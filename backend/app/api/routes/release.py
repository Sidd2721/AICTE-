import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.core.audit import audit_append
from app.domain.discrepancy import evaluate_discrepancies
from app.domain.receipt import sign_release_receipt
from app.domain.receipt_pdf import build_release_receipt_pdf
from app.domain.rules import load_rule
from app.domain.trust import Confirmation as TrustConfirmation
from app.domain.trust import badge
from app.models import (
    Confirmation,
    FlagWaiver,
    Institution,
    Instrument,
    ReleaseRequest,
    ReleaseRequestCreate,
    ReleaseRequestPublic,
)

router = APIRouter(tags=["release"])


def _load_release_rules() -> dict[str, Any]:
    return load_rule(None, "release_paths", date.today())


@router.post(
    "/instruments/{instrument_id}/release", response_model=ReleaseRequestPublic
)
def request_release(
    instrument_id: uuid.UUID,
    data: ReleaseRequestCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    if current_user.role != "institution" and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only Institution users can request release of instruments",
        )

    instrument = session.get(Instrument, instrument_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    rules = _load_release_rules()
    paths = rules.get("paths", {})
    if data.path not in paths:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid release path '{data.path}'. Allowed paths: {list(paths.keys())}",
        )

    checklist_def = paths[data.path].get("checklist", [])
    checklist: list[dict[str, Any]] = []

    today = date.today()
    is_matured = instrument.maturity_date <= today

    for item in checklist_def:
        item_copy = dict(item)
        # Closure waiver when deposit already matured
        if item_copy.get("waived_if") == "deposit_matured" and is_matured:
            item_copy["waived"] = True
            item_copy["waiver_reason"] = "Deposit has already matured"
        else:
            item_copy["waived"] = False

        if (
            item_copy.get("id") == "no_pending_complaints"
            and data.attestation_no_complaints
        ):
            item_copy["attested"] = True
        checklist.append(item_copy)

    # Check for existing pending/submitted/verified request
    existing = session.exec(
        select(ReleaseRequest)
        .where(ReleaseRequest.instrument_id == instrument_id)
        .where(col(ReleaseRequest.status).in_(["draft", "submitted", "verified"]))
    ).first()
    if existing:
        return existing

    release_req = ReleaseRequest(
        instrument_id=instrument_id,
        path=data.path,
        checklist=checklist,
        status="submitted",
        requested_by=current_user.id,
    )
    session.add(release_req)
    session.commit()
    session.refresh(release_req)

    audit_append(
        session,
        actor_id=current_user.id,
        action="release.requested",
        entity="release_request",
        entity_id=str(release_req.id),
        payload={"path": data.path, "instrument_id": str(instrument_id)},
    )

    return release_req


@router.get(
    "/instruments/{instrument_id}/release", response_model=ReleaseRequestPublic | None
)
def get_instrument_release(
    instrument_id: uuid.UUID,
    session: SessionDep,
    _current_user: CurrentUser,
) -> Any:
    return session.exec(
        select(ReleaseRequest)
        .where(ReleaseRequest.instrument_id == instrument_id)
        .order_by(col(ReleaseRequest.created_at).desc())
    ).first()


@router.patch("/release/{release_id}/verify", response_model=ReleaseRequestPublic)
@router.post(
    "/release/{release_id}/verify",
    response_model=ReleaseRequestPublic,
    operation_id="release-verify_release_post",
)
def verify_release(
    release_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    release_req = session.get(ReleaseRequest, release_id)
    if not release_req:
        raise HTTPException(status_code=404, detail="Release request not found")

    if current_user.role != "regional" and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only Regional Officers can verify release requests",
        )

    instrument = session.get(Instrument, release_req.instrument_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    # Check discrepancy flags first
    waivers = session.exec(
        select(FlagWaiver).where(FlagWaiver.instrument_id == instrument.id)
    ).all()
    waiver_codes = {w.code for w in waivers}

    inst_dict = {
        "ref_no": instrument.ref_no,
        "bank_code": instrument.bank_code,
        "amount_paise": instrument.amount_paise,
        "maturity_date": instrument.maturity_date,
        "lien_marked": instrument.lien_marked,
    }
    latest_conf = session.exec(
        select(Confirmation)
        .where(Confirmation.instrument_id == instrument.id)
        .where(Confirmation.status == "confirmed")
        .where(col(Confirmation.revoked).is_(False))
        .order_by(col(Confirmation.confirmed_at).desc())
    ).first()

    if latest_conf and latest_conf.fields:
        discrepancies = evaluate_discrepancies(inst_dict, latest_conf.fields)
        for d in discrepancies:
            if (
                d.get("severity") in ("critical", "block")
                and d.get("code") not in waiver_codes
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot verify release: blocked by discrepancy {d.get('code')}: {d.get('label')}",
                )

    # Invariant checks: check open discrepancy block flags and badge
    confs = session.exec(
        select(Confirmation)
        .where(Confirmation.instrument_id == instrument.id)
        .where(col(Confirmation.revoked).is_(False))
    ).all()
    trust_confs = [
        TrustConfirmation(
            fields=c.fields or {},
            method=c.method,
            confirmed_at=c.confirmed_at or datetime.now(UTC),
            expires_at=c.expires_at or datetime.now(UTC),
            revoked=c.revoked,
        )
        for c in confs
    ]
    inst_badge = badge(
        {
            "ref_no": instrument.ref_no,
            "bank_code": instrument.bank_code,
            "amount_paise": instrument.amount_paise,
            "maturity_date": str(instrument.maturity_date),
        },
        trust_confs,
        datetime.now(UTC),
    )
    if inst_badge in ("stale", "changed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot verify release: bank confirmation status is {inst_badge}",
        )

    release_req.verified_by = current_user.id
    release_req.status = "verified"
    release_req.updated_at = datetime.now(UTC)

    session.add(release_req)
    session.commit()
    session.refresh(release_req)

    audit_append(
        session,
        actor_id=current_user.id,
        action="release.verified",
        entity="release_request",
        entity_id=str(release_req.id),
        payload={"verified_by": str(current_user.id)},
    )

    return release_req


@router.patch("/release/{release_id}/approve", response_model=ReleaseRequestPublic)
@router.post(
    "/release/{release_id}/approve",
    response_model=ReleaseRequestPublic,
    operation_id="release-approve_release_post",
)
def approve_release(
    release_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    release_req = session.get(ReleaseRequest, release_id)
    if not release_req:
        raise HTTPException(status_code=404, detail="Release request not found")

    if current_user.role != "bureau" and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only Bureau Head/Approver can approve release requests",
        )

    # Invariant I8: Maker is NEVER checker
    if release_req.verified_by == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Maker cannot be checker: the officer who verified cannot approve release",
        )

    instrument = session.get(Instrument, release_req.instrument_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    # Generate PyJWT signed receipt
    receipt_token = sign_release_receipt(
        instrument_id=str(instrument.id),
        instrument_ref_no=instrument.ref_no,
        path=release_req.path,
        release_id=str(release_req.id),
    )

    release_req.approved_by = current_user.id
    release_req.status = "released"
    release_req.receipt_token = receipt_token
    release_req.updated_at = datetime.now(UTC)

    instrument.lifecycle = "released"
    instrument.updated_at = datetime.now(UTC)

    session.add(release_req)
    session.add(instrument)
    session.commit()
    session.refresh(release_req)

    audit_append(
        session,
        actor_id=current_user.id,
        action="release.approved",
        entity="release_request",
        entity_id=str(release_req.id),
        payload={"approved_by": str(current_user.id)},
    )
    audit_append(
        session,
        actor_id=current_user.id,
        action="instrument.released",
        entity="instrument",
        entity_id=str(instrument.id),
        payload={"release_id": str(release_req.id)},
    )

    return release_req


@router.patch("/release/{release_id}/reject", response_model=ReleaseRequestPublic)
def reject_release(
    release_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    reason: str = Query(..., min_length=5),
) -> Any:
    release_req = session.get(ReleaseRequest, release_id)
    if not release_req:
        raise HTTPException(status_code=404, detail="Release request not found")

    if (
        current_user.role not in ("regional", "bureau")
        and not current_user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Unauthorized to reject release")

    release_req.status = "rejected"
    release_req.updated_at = datetime.now(UTC)

    session.add(release_req)
    session.commit()
    session.refresh(release_req)

    audit_append(
        session,
        actor_id=current_user.id,
        action="release.rejected",
        entity="release_request",
        entity_id=str(release_req.id),
        payload={"reason": reason, "rejected_by": str(current_user.id)},
    )

    return release_req


@router.get("/release/{id}/receipt.pdf")
def get_release_receipt_pdf(
    id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Response:
    """Download signed PDF release receipt for a released instrument."""
    release_req = session.get(ReleaseRequest, id)
    if not release_req:
        raise HTTPException(status_code=404, detail="Release request not found")

    instrument = session.get(Instrument, release_req.instrument_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    # Tenant check:
    # 1. Institution users can only view their own institution's receipts
    if (
        current_user.role == "institution"
        and current_user.institution_id
        and instrument.institution_id != current_user.institution_id
    ):
        raise HTTPException(status_code=404, detail="Release request not found")

    # 2. Regional officers can only view instruments within their assigned region
    if (
        current_user.role == "regional"
        and current_user.region
        and instrument.region != current_user.region
    ):
        raise HTTPException(status_code=404, detail="Release request not found")

    # Status check: must be fully released with receipt token
    if release_req.status != "released" or not release_req.receipt_token:
        raise HTTPException(
            status_code=409,
            detail="Release request is not in released status; receipt is only available after release approval",
        )

    institution = session.get(Institution, instrument.institution_id)
    inst_name = institution.name if institution else "AICTE Regulated Institution"

    pdf_bytes = build_release_receipt_pdf(
        token=release_req.receipt_token,
        instrument_ref_no=instrument.ref_no,
        institution_name=inst_name,
        bank_code=instrument.bank_code,
        amount_paise=instrument.amount_paise,
    )

    filename = f"release_receipt_{instrument.ref_no}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/release/verify-receipt")
def verify_receipt_endpoint(token: str = Query(...)) -> Any:
    """Public endpoint to verify a release receipt token."""
    from app.domain.receipt import verify_release_receipt

    try:
        claims = verify_release_receipt(token)
        return {"status": "valid", **claims}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid or tampered receipt: {e}")
