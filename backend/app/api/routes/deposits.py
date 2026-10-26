import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.domain.clock import today
from app.domain.rules import (
    calculate_institution_coverage,
    load_rule,
    required_deposit_paise,
)
from app.models import Institution, Instrument

router = APIRouter(prefix="/deposits", tags=["deposits"])


class CalculatorBreakdown(BaseModel):
    programme: str
    amount_paise: int


class ProgrammeInfo(BaseModel):
    name: str
    amount_paise: int


class ProgrammesResponse(BaseModel):
    programmes: list[ProgrammeInfo]
    deposit_term_years: int
    leased_private_multiplier: int
    government_exempt: bool
    edition: str
    effective_from: str


class CalculatorResponse(BaseModel):
    required_deposit_paise: int
    multiplier: int
    exempt: bool
    breakdown: list[CalculatorBreakdown]
    rule_edition: str
    rule_effective_from: str


@router.get("/programmes", response_model=ProgrammesResponse)
def get_programmes(
    as_of: date | None = Query(None, description="Date for dated rulebook lookup"),
) -> Any:
    calc_date = as_of or today()
    try:
        rule = load_rule(None, "deposit", calc_date)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    amounts: dict[str, int] = rule.get("programme_amounts_paise", {})
    progs = [ProgrammeInfo(name=k, amount_paise=v) for k, v in amounts.items()]

    return ProgrammesResponse(
        programmes=progs,
        deposit_term_years=rule.get("deposit_term_years", 10),
        leased_private_multiplier=rule.get("leased_private_multiplier", 2),
        government_exempt=rule.get("government_exempt", True),
        edition=rule.get("edition", "APH 2024-25 to 2026-27"),
        effective_from=rule.get("effective_from", "2024-04-01"),
    )


@router.get("/calculator", response_model=CalculatorResponse)
def calculate_deposit(
    programmes: str = Query(..., description="Comma-separated list of programme names"),
    land_ownership: str = Query("owned", description="'owned' or 'leased'"),
    institution_type: str = Query("private", description="'private' or 'government'"),
    as_of: date | None = Query(None, description="Date for dated rulebook lookup"),
) -> Any:
    calc_date = as_of or today()
    try:
        rule = load_rule(None, "deposit", calc_date)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    prog_list = [p.strip() for p in programmes.split(",") if p.strip()]
    if not prog_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one programme must be provided",
        )

    available_rates: dict[str, int] = rule.get("programme_amounts_paise", {})
    breakdown: list[CalculatorBreakdown] = []
    amounts: list[int] = []

    for p in prog_list:
        if p not in available_rates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown programme '{p}'. Available programmes: {list(available_rates.keys())}",
            )
        rate = available_rates[p]
        amounts.append(rate)
        breakdown.append(CalculatorBreakdown(programme=p, amount_paise=rate))

    is_gov = institution_type.lower() == "government"
    is_leased = land_ownership.lower() == "leased"

    total = required_deposit_paise(
        amounts,
        leased_private=is_leased,
        rule=rule,
        is_government=is_gov,
    )

    if is_gov:
        mult = 0
    elif is_leased:
        mult = rule.get("leased_private_multiplier", 2)
    else:
        mult = 1

    return CalculatorResponse(
        required_deposit_paise=total,
        multiplier=mult,
        exempt=is_gov,
        breakdown=breakdown,
        rule_edition=rule.get("edition", "unknown"),
        rule_effective_from=rule.get("effective_from", "unknown"),
    )


@router.get("/coverage")
def get_institution_coverage(
    session: SessionDep,
    current_user: CurrentUser,
    institution_id: uuid.UUID | None = Query(None),
) -> dict[str, Any]:
    """Calculate institution security deposit coverage: required vs confirmed vs claimed vs shortfall."""
    target_id = institution_id or current_user.institution_id
    if not target_id:
        # Default or unattached user
        return {
            "required_paise": 350000000,
            "confirmed_active_paise": 0,
            "claimed_only_paise": 0,
            "shortfall_paise": 350000000,
            "is_compliant": False,
            "multiplier": 1,
            "is_government": False,
            "institution_name": "General Obligation (Unspecified)",
        }

    instn = session.get(Institution, target_id)
    instruments = session.exec(
        select(Instrument).where(Instrument.institution_id == target_id)
    ).all()

    inst_dicts = [
        {
            "id": str(i.id),
            "amount_paise": i.amount_paise,
            "lifecycle": i.lifecycle,
            "badge": getattr(i, "badge", "claimed"),
        }
        for i in instruments
    ]

    cov: dict[str, Any] = dict(
        calculate_institution_coverage(
            programme_amounts_paise=[350000000],
            leased_private=instn.leased_private if instn else False,
            rule=load_rule(None, "deposit", today()),
            is_government=instn.is_government if instn else False,
            instruments=inst_dicts,
        )
    )
    cov["institution_name"] = instn.name if instn else "Institution"
    cov["permanent_id"] = instn.permanent_id if instn else ""
    cov["is_compliant"] = cov["shortfall_paise"] == 0
    cov["multiplier"] = 2 if (instn and instn.leased_private) else 1
    cov["is_government"] = instn.is_government if instn else False
    return cov
