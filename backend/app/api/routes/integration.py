"""Proposed, machine-authenticated integration contract.

All external systems remain adapters/simulators until AICTE and each bank agree to
hosting, identity, retention, and transport details.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import select

from app.api.deps import SessionDep
from app.api.deps_integration import require_scope
from app.core.audit import audit
from app.domain.clock import now
from app.domain.rules import load_rule
from app.domain.trust import Confirmation as TrustConfirmation
from app.domain.trust import badge
from app.integration.idempotency import (
    IdempotencyConflict,
    body_hash,
    claim_request,
    complete_request,
    replay_response,
)
from app.integration.outbox import enqueue
from app.models import Confirmation, Institution, Instrument, MachineApiKey

router = APIRouter(prefix="/integration", tags=["integration"])


class ProgrammeInput(BaseModel):
    category: str = Field(min_length=1, max_length=120)
    level: str = Field(min_length=1, max_length=20)


class InstitutionUpsert(BaseModel):
    permanent_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    region: str = Field(min_length=1, max_length=100)
    is_government: bool = False
    leased_private: bool = False
    programmes: list[ProgrammeInput] = Field(default_factory=list)


class BulkUpsertResponse(BaseModel):
    dry_run: bool
    accepted: int
    created: int = 0
    updated: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)


def _validate_row(row: InstitutionUpsert, allowed: set[str]) -> list[str]:
    errors: list[str] = []
    for programme in row.programmes:
        if programme.category not in allowed:
            errors.append(f"unknown programme category: {programme.category}")
    if row.leased_private and row.is_government:
        errors.append("government institutions cannot be marked leased_private")
    return errors


@router.post("/institutions:bulk-upsert", response_model=BulkUpsertResponse)
def bulk_upsert_institutions(
    rows: list[InstitutionUpsert],
    session: SessionDep,
    _client: MachineApiKey = Depends(require_scope("institutions:write")),
    dry_run: bool = Query(False),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> BulkUpsertResponse:
    rule = load_rule(None, "deposit", date.today())
    allowed = set(rule.get("programme_amounts_paise", {}))
    errors = [
        {"row": index, "permanent_id": row.permanent_id, "errors": row_errors}
        for index, row in enumerate(rows)
        if (row_errors := _validate_row(row, allowed))
    ]
    valid_rows = [row for row in rows if not _validate_row(row, allowed)]
    if errors and not dry_run:
        return BulkUpsertResponse(dry_run=False, accepted=0, errors=errors)

    request_record = None
    if idempotency_key:
        try:
            request_record, is_new = claim_request(
                session,
                scope="integration:institutions:bulk-upsert",
                key=idempotency_key,
                request_hash=body_hash(
                    {
                        "rows": [row.model_dump(mode="json") for row in rows],
                        "dry_run": dry_run,
                    }
                ),
            )
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not is_new:
            replayed = replay_response(request_record)
            if replayed is None:
                raise HTTPException(
                    status_code=409, detail="request is already in progress"
                )
            return BulkUpsertResponse.model_validate(replayed)

    result = BulkUpsertResponse(
        dry_run=dry_run,
        accepted=len(valid_rows),
        errors=errors,
    )
    if not dry_run:
        for row in valid_rows:
            existing = session.exec(
                select(Institution).where(Institution.permanent_id == row.permanent_id)
            ).first()
            if existing:
                existing.name = row.name
                existing.region = row.region
                existing.is_government = row.is_government
                existing.leased_private = row.leased_private
                existing.programmes = [p.model_dump() for p in row.programmes]
                result.updated += 1
                institution = existing
            else:
                institution = Institution(
                    permanent_id=row.permanent_id,
                    name=row.name,
                    region=row.region,
                    is_government=row.is_government,
                    leased_private=row.leased_private,
                    programmes=[p.model_dump() for p in row.programmes],
                )
                session.add(institution)
                result.created += 1
            session.flush()
            enqueue(
                session,
                event_type="institution.upserted",
                aggregate_type="institution",
                aggregate_id=str(institution.id),
                payload={"permanent_id": institution.permanent_id, "state": "upserted"},
            )
        session.commit()
        for row in valid_rows:
            audit(
                session,
                actor_id=None,
                action="institution.bulk_upserted",
                entity="institution",
                entity_id=row.permanent_id,
                payload={"state": "upserted", "source": "machine_api"},
            )

    if request_record:
        complete_request(
            session,
            request_record,
            status_code=200,
            response=result.model_dump(mode="json"),
        )
    return result


@router.get("/institutions/{permanent_id}/coverage-status")
def coverage_status(
    permanent_id: str,
    session: SessionDep,
    _client: MachineApiKey = Depends(require_scope("coverage:read")),
) -> dict[str, Any]:
    institution = session.exec(
        select(Institution).where(Institution.permanent_id == permanent_id)
    ).first()
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found")

    rule = load_rule(None, "deposit", date.today())
    rates: dict[str, int] = rule.get("programme_amounts_paise", {})
    programme_amounts = [
        rates[p.get("category", "")]
        for p in institution.programmes
        if p.get("category", "") in rates
    ]
    required = 0 if institution.is_government else sum(programme_amounts)
    if institution.leased_private and required:
        required *= int(rule.get("leased_private_multiplier", 2))

    confirmed = 0
    claimed = 0
    instruments = session.exec(
        select(Instrument).where(Instrument.institution_id == institution.id)
    ).all()
    for instrument in instruments:
        if instrument.lifecycle == "released":
            continue
        confirmations = session.exec(
            select(Confirmation).where(Confirmation.instrument_id == instrument.id)
        ).all()
        trust = [
            TrustConfirmation(
                fields=confirmation.fields or {},
                method=confirmation.method,
                confirmed_at=confirmation.confirmed_at or now(),
                expires_at=confirmation.expires_at or now(),
                revoked=confirmation.revoked,
            )
            for confirmation in confirmations
        ]
        current_badge = badge(
            {
                "ref_no": instrument.ref_no,
                "bank_code": instrument.bank_code,
                "amount_paise": instrument.amount_paise,
                "maturity_date": str(instrument.maturity_date),
            },
            trust,
            now(),
        )
        if current_badge == "confirmed":
            confirmed += instrument.amount_paise
        else:
            claimed += instrument.amount_paise

    if required == 0:
        state = "exempt"
    elif confirmed >= required:
        state = "covered"
    elif confirmed == 0 and claimed:
        state = "unconfirmed"
    else:
        state = "short"
    return {
        "permanent_id": institution.permanent_id,
        "required_paise": required,
        "confirmed_paise": confirmed,
        "claimed_paise": claimed,
        "status": state,
        "as_of": date.today().isoformat(),
        "rule_edition": rule.get("edition", "unknown"),
        "rule_status": rule.get("status", "DEMO"),
    }
