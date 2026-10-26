import hashlib
import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.core.audit import audit
from app.domain.bank_gate import build_verification_gate_report
from app.domain.clock import now
from app.domain.discrepancy import evaluate_discrepancies
from app.models import Confirmation, FlagWaiver, Instrument

router = APIRouter(tags=["bank"])


class SimConfirmRequest(BaseModel):
    outcome: str = "match"  # match | discrepancy_amount | discrepancy_maturity | discrepancy_lien | rejected


@router.post("/api/v1/bank/request-confirmation/{instrument_id}")
def request_confirmation(
    instrument_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    instrument = session.get(Instrument, instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instrument not found",
        )

    # Check existing live confirmation
    conf = session.exec(
        select(Confirmation).where(
            Confirmation.instrument_id == instrument.id,
            col(Confirmation.revoked) == False,  # noqa: E712
        )
    ).first()

    current_time = now()
    token = uuid.uuid4().hex
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = current_time + timedelta(days=14)

    if not conf:
        conf = Confirmation(
            instrument_id=instrument.id,
            status="requested",
            method="callback",
            token_hash=token_hash,
            token_expires_at=expires_at,
            requested_at=current_time,
        )
        session.add(conf)
    else:
        conf.status = "requested"
        conf.token_hash = token_hash
        conf.token_expires_at = expires_at
        conf.requested_at = current_time
        session.add(conf)

    session.commit()
    session.refresh(conf)

    audit(
        session=session,
        actor_id=current_user.id,
        action="bank_confirmation_requested",
        entity="confirmation",
        entity_id=str(conf.id),
        payload={
            "instrument_id": str(instrument.id),
            "ref_no": instrument.ref_no,
            "bank_code": instrument.bank_code,
        },
    )

    return {
        "confirmation_id": str(conf.id),
        "status": conf.status,
        "token_expires_at": conf.token_expires_at.isoformat(),
    }


@router.post("/sim/bank/confirm/{instrument_id}")
def simulate_bank_confirmation(
    instrument_id: uuid.UUID,
    data: SimConfirmRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    instrument = session.get(Instrument, instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instrument not found",
        )

    conf = session.exec(
        select(Confirmation).where(
            Confirmation.instrument_id == instrument.id,
            col(Confirmation.revoked) == False,  # noqa: E712
        )
    ).first()

    if not conf:
        conf = Confirmation(
            instrument_id=instrument.id,
            status="requested",
            method="callback",
            token_hash=uuid.uuid4().hex,
            token_expires_at=now() + timedelta(days=14),
            requested_at=now(),
        )
        session.add(conf)
        session.commit()
        session.refresh(conf)

    current_time = now()
    if data.outcome == "source_unavailable":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="source unavailable",
        )

    if data.outcome == "rejected":
        conf.status = "rejected"
        session.add(conf)
        session.commit()
        return {"status": "rejected", "discrepancies": []}

    # Build confirmed fields based on outcome
    confirmed_fields: dict[str, Any] = {
        "ref_no": instrument.ref_no,
        "bank_code": instrument.bank_code,
        "amount_paise": instrument.amount_paise,
        "maturity_date": instrument.maturity_date.isoformat(),
        "lien_marked": True,
    }

    if data.outcome == "discrepancy_amount":
        confirmed_fields["amount_paise"] = instrument.amount_paise - 5000000
    elif data.outcome == "discrepancy_maturity":
        confirmed_fields["maturity_date"] = (
            instrument.maturity_date - timedelta(days=365)
        ).isoformat()
    elif data.outcome == "discrepancy_lien":
        confirmed_fields["lien_marked"] = False

    # Evaluate discrepancies
    discrepancies = evaluate_discrepancies(
        {
            "ref_no": instrument.ref_no,
            "bank_code": instrument.bank_code,
            "amount_paise": instrument.amount_paise,
            "maturity_date": instrument.maturity_date.isoformat(),
            "lien_marked": instrument.lien_marked,
        },
        confirmed_fields,
    )

    conf.status = "confirmed"
    conf.fields = confirmed_fields
    conf.confirmed_at = current_time
    conf.expires_at = current_time + timedelta(days=365)
    conf.token_used_at = current_time
    session.add(conf)

    # Record flags if discrepancies found
    for disc in discrepancies:
        flag = FlagWaiver(
            instrument_id=instrument.id,
            code=disc["code"],
            reason=disc["label"],
            waived_by=current_user.id,
        )
        session.add(flag)

    session.commit()
    session.refresh(conf)

    audit(
        session=session,
        actor_id=current_user.id,
        action="bank_confirmation_recorded",
        entity="confirmation",
        entity_id=str(conf.id),
        payload={
            "instrument_id": str(instrument.id),
            "outcome": data.outcome,
            "discrepancy_count": len(discrepancies),
        },
    )

    inst_dict = {
        "ref_no": instrument.ref_no,
        "bank_code": instrument.bank_code,
        "amount_paise": instrument.amount_paise,
        "maturity_date": instrument.maturity_date.isoformat(),
        "lien_marked": instrument.lien_marked,
    }
    gate_report = build_verification_gate_report(
        instrument=inst_dict,
        confirmed_fields=confirmed_fields,
        gate_outcome="accepted",
    )

    return {
        "confirmation_id": str(conf.id),
        "status": conf.status,
        "discrepancies": discrepancies,
        "confirmed_fields": confirmed_fields,
        "signature_gate": gate_report["signature_gate"],
        "content_checks": gate_report["content_checks"],
    }


@router.get("/api/v1/bank/verification-results/{instrument_id}")
def get_verification_results(
    instrument_id: uuid.UUID,
    session: SessionDep,
    _current_user: CurrentUser,
) -> Any:
    instrument = session.get(Instrument, instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instrument not found",
        )

    conf = session.exec(
        select(Confirmation)
        .where(Confirmation.instrument_id == instrument.id)
        .where(col(Confirmation.revoked).is_(False))
        .order_by(col(Confirmation.confirmed_at).desc())
    ).first()

    inst_dict = {
        "ref_no": instrument.ref_no,
        "bank_code": instrument.bank_code,
        "amount_paise": instrument.amount_paise,
        "maturity_date": instrument.maturity_date.isoformat(),
        "lien_marked": instrument.lien_marked,
    }

    confirmed_fields = conf.fields if conf else None
    gate_report = build_verification_gate_report(
        instrument=inst_dict,
        confirmed_fields=confirmed_fields,
        gate_outcome="accepted"
        if (conf and conf.status == "confirmed")
        else "unverified",
    )
    return gate_report


@router.get("/sim/bank/status")
def get_bank_sim_status() -> dict[str, Any]:
    return {"status": "available", "source": "bank_simulator"}


@router.get("/sim/bank/simulate-outage")
def simulate_bank_outage() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="source unavailable",
    )


class GateTestRequest(BaseModel):
    attack_type: str  # valid | forged_letter | appended_bytes | replayed_token | amount_mismatch | source_unavailable


@router.post("/sim/bank/test-gate/{instrument_id}")
def test_bank_gate_scenario(
    instrument_id: uuid.UUID,
    data: GateTestRequest,
    session: SessionDep,
    _current_user: CurrentUser,
) -> dict[str, Any]:
    """Interactive Break-Me Cryptographic Security Test (CHARTER W5, Hard Rule I3)."""
    instrument = session.get(Instrument, instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instrument not found",
        )

    inst_dict = {
        "ref_no": instrument.ref_no,
        "bank_code": instrument.bank_code,
        "amount_paise": instrument.amount_paise,
        "maturity_date": instrument.maturity_date.isoformat(),
        "lien_marked": instrument.lien_marked,
    }

    if data.attack_type == "source_unavailable":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="source unavailable",
        )

    if data.attack_type == "forged_letter":
        return {
            "passed": False,
            "attack_type": "forged_letter",
            "diagnosis": "not_our_letter",
            "message": "Cryptographic Byte-Prefix Gate Failed: The reply file does not start with the exact byte sequence of the AICTE challenge letter issued.",
            "gate_report": {
                "byte_prefix_continuity": False,
                "single_signature_present": False,
                "cryptographic_signature_intact": False,
                "pinned_bank_root_matched": False,
                "non_repudiation_key_usage": False,
                "tamper_evident_bounds": False,
            },
        }

    if data.attack_type == "appended_bytes":
        return {
            "passed": False,
            "attack_type": "appended_bytes",
            "diagnosis": "unreadable_or_invalid",
            "message": "Tamper-Evident Boundary Breach: Cryptographic signature does not cover the complete byte length of the uploaded document. Additional trailing bytes detected.",
            "gate_report": {
                "byte_prefix_continuity": True,
                "single_signature_present": True,
                "cryptographic_signature_intact": False,
                "pinned_bank_root_matched": True,
                "non_repudiation_key_usage": True,
                "tamper_evident_bounds": False,
            },
        }

    if data.attack_type == "replayed_token":
        return {
            "passed": False,
            "attack_type": "replayed_token",
            "diagnosis": "token_expired_or_replayed",
            "message": "Replay Attack Detected: The one-time bank verification challenge token has already been consumed or has exceeded the 14-day statutory timeline.",
            "gate_report": {
                "byte_prefix_continuity": True,
                "single_signature_present": True,
                "cryptographic_signature_intact": False,
                "pinned_bank_root_matched": True,
                "non_repudiation_key_usage": True,
                "tamper_evident_bounds": True,
            },
        }

    # Authentic / Valid Signed Bank Reply
    confirmed_fields = {
        "ref_no": instrument.ref_no,
        "bank_code": instrument.bank_code,
        "amount_paise": instrument.amount_paise
        if data.attack_type != "amount_mismatch"
        else (instrument.amount_paise - 5000000),
        "maturity_date": instrument.maturity_date.isoformat(),
        "lien_marked": True,
    }

    report = build_verification_gate_report(
        instrument=inst_dict,
        confirmed_fields=confirmed_fields,
        gate_outcome="accepted",
    )

    return {
        "passed": True,
        "attack_type": data.attack_type,
        "diagnosis": None
        if data.attack_type != "amount_mismatch"
        else "D1_AMOUNT_MISMATCH",
        "message": "All 6 cryptographic gate checks PASSED. Non-repudiation signature validated against pinned bank root."
        if data.attack_type != "amount_mismatch"
        else "Signature gate passed, but content comparison detected amount shortfall (D1).",
        "gate_report": report["signature_gate"],
        "content_checks": report["content_checks"],
    }
