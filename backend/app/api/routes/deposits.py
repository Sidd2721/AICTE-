from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.domain.clock import today
from app.domain.rules import load_rule, required_deposit_paise

router = APIRouter(prefix="/deposits", tags=["deposits"])


class CalculatorBreakdown(BaseModel):
    programme: str
    amount_paise: int


class CalculatorResponse(BaseModel):
    required_deposit_paise: int
    multiplier: int
    exempt: bool
    breakdown: list[CalculatorBreakdown]
    rule_edition: str
    rule_effective_from: str


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
