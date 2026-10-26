import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.core.audit import audit
from app.domain.clock import now
from app.domain.next_action import next_action
from app.domain.trust import Confirmation as TrustConfirmation
from app.domain.trust import badge
from app.models import (
    Confirmation,
    Document,
    Institution,
    Instrument,
    InstrumentPublic,
    InstrumentsPublic,
    InstrumentSubmit,
    Obligation,
    ReleaseRequest,
)

router = APIRouter(prefix="/instruments", tags=["instruments"])


def _hydrate_instrument_meta(
    inst: Instrument,
    session: SessionDep,
    user_role: str,
) -> InstrumentPublic:
    # Fetch confirmations
    confs = session.exec(
        select(Confirmation).where(Confirmation.instrument_id == inst.id)
    ).all()
    trust_confs = [
        TrustConfirmation(
            fields=c.fields or {},
            method=c.method,
            confirmed_at=c.confirmed_at or now(),
            expires_at=c.expires_at or now(),
            revoked=c.revoked,
        )
        for c in confs
    ]

    current_badge = badge(
        {
            "ref_no": inst.ref_no,
            "bank_code": inst.bank_code,
            "amount_paise": inst.amount_paise,
            "maturity_date": str(inst.maturity_date),
        },
        trust_confs,
        now(),
    )

    # Document completion check
    docs = session.exec(select(Document).where(Document.instrument_id == inst.id)).all()
    docs_complete = any(d.kind == "fdr_scan" for d in docs)

    # Open obligations / release requests
    open_obligations = session.exec(
        select(Obligation).where(
            Obligation.instrument_id == inst.id,
            Obligation.status == "open",
        )
    ).all()

    release_req = session.exec(
        select(ReleaseRequest).where(ReleaseRequest.instrument_id == inst.id)
    ).first()
    release_status = release_req.status if release_req else None

    # Latest confirmation status
    conf_status: str | None = None
    if confs:
        latest_conf = max(confs, key=lambda c: c.requested_at)
        conf_status = latest_conf.status

    current_date = now().date()
    days_to_maturity = (inst.maturity_date - current_date).days

    action = next_action(
        role=user_role,
        lifecycle=inst.lifecycle,
        badge=current_badge,
        docs_complete=docs_complete,
        open_flags=len(open_obligations),
        confirmation_status=conf_status,
        days_to_maturity=days_to_maturity,
        expiring_days=60,
        has_replacement=inst.replaces_id is not None,
        release_status=release_status,
    )

    return InstrumentPublic(
        id=inst.id,
        institution_id=inst.institution_id,
        region=inst.region,
        kind=inst.kind,
        ref_no=inst.ref_no,
        bank_code=inst.bank_code,
        ifsc=inst.ifsc,
        amount_paise=inst.amount_paise,
        issue_date=inst.issue_date,
        maturity_date=inst.maturity_date,
        holders=inst.holders,
        lien_marked=inst.lien_marked,
        is_duplicate_receipt=inst.is_duplicate_receipt,
        lifecycle=inst.lifecycle,
        replaces_id=inst.replaces_id,
        created_by=inst.created_by,
        created_at=inst.created_at,
        updated_at=inst.updated_at,
        badge=current_badge,
        next_action_code=action.code,
        next_action_label=action.label,
    )


@router.post("/submit", response_model=InstrumentPublic)
def submit_instrument(
    data: InstrumentSubmit,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    if data.amount_paise <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount in paise must be positive integer",
        )
    if data.maturity_date <= data.issue_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maturity date must be after issue date",
        )

    # Determine institution and region
    inst_id = data.institution_id or current_user.institution_id
    if not inst_id:
        default_inst = session.exec(select(Institution)).first()
        if not default_inst:
            default_inst = Institution(
                permanent_id=f"1-{uuid.uuid4().hex[:8].upper()}",
                name="Default Institution",
                region="North",
                is_government=False,
                leased_private=False,
            )

            session.add(default_inst)
            session.commit()
            session.refresh(default_inst)
        inst_id = default_inst.id

    institution_obj = session.get(Institution, inst_id)
    region = data.region or (institution_obj.region if institution_obj else "North")

    instrument = Instrument(
        institution_id=inst_id,
        region=region,
        kind=data.kind,
        ref_no=data.ref_no,
        bank_code=data.bank_code,
        ifsc=data.ifsc,
        amount_paise=data.amount_paise,
        issue_date=data.issue_date,
        maturity_date=data.maturity_date,
        holders=data.holders,
        lien_marked=data.lien_marked,
        is_duplicate_receipt=data.is_duplicate_receipt,
        lifecycle="pending",
        replaces_id=data.replaces_id,
        created_by=current_user.id,
    )
    session.add(instrument)
    session.commit()
    session.refresh(instrument)

    # Attach documents if provided
    for doc_id in data.document_ids:
        doc = session.get(Document, doc_id)
        if doc:
            doc.instrument_id = instrument.id
            session.add(doc)
    if data.document_ids:
        session.commit()

    audit(
        session=session,
        actor_id=current_user.id,
        action="instrument_submitted",
        entity="instrument",
        entity_id=str(instrument.id),
        payload={
            "instrument_id": str(instrument.id),
            "ref_no": instrument.ref_no,
            "bank_code": instrument.bank_code,
            "amount_paise": instrument.amount_paise,
        },
    )

    role = current_user.role or (
        "institution" if current_user.institution_id else "regional"
    )
    return _hydrate_instrument_meta(instrument, session, role)


@router.get("", response_model=InstrumentsPublic)
def list_instruments(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    query = select(Instrument)
    if not current_user.is_superuser and current_user.role not in ("bureau", "auditor"):
        if current_user.institution_id:
            query = query.where(
                Instrument.institution_id == current_user.institution_id
            )
        elif current_user.region:
            query = query.where(Instrument.region == current_user.region)

    instruments = session.exec(query.offset(skip).limit(limit)).all()
    role = current_user.role or (
        "institution" if current_user.institution_id else "regional"
    )
    hydrated = [_hydrate_instrument_meta(i, session, role) for i in instruments]

    return InstrumentsPublic(data=hydrated, count=len(hydrated))


@router.get("/{instrument_id}", response_model=InstrumentPublic)
def get_instrument(
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

    role = current_user.role or (
        "institution" if current_user.institution_id else "regional"
    )
    return _hydrate_instrument_meta(instrument, session, role)


@router.get("/{instrument_id}/case")
def get_instrument_case(
    instrument_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Aggregate case view: instrument + bank confirmations + discrepancies + documents +
    flags + release request + per-instrument audit trail — saves 5+ separate requests."""

    from sqlmodel import col

    from app.domain.discrepancy import evaluate_discrepancies
    from app.models import (
        AuditEvent,
        CaseNote,
        Confirmation,
        Document,
        FlagWaiver,
        Institution,
        ReleaseRequest,
    )

    instrument = session.get(Instrument, instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found"
        )

    role = current_user.role or (
        "institution" if current_user.institution_id else "regional"
    )
    hydrated = _hydrate_instrument_meta(instrument, session, role)

    # Confirmations
    confs = session.exec(
        select(Confirmation).where(Confirmation.instrument_id == instrument_id)
    ).all()
    latest_conf = None
    if confs:
        latest_conf = max(confs, key=lambda c: c.requested_at)

    # Discrepancies
    discrepancies: list[dict[str, object]] = []
    if latest_conf and latest_conf.status == "confirmed" and latest_conf.fields:
        inst_dict = {
            "ref_no": instrument.ref_no,
            "bank_code": instrument.bank_code,
            "amount_paise": instrument.amount_paise,
            "maturity_date": str(instrument.maturity_date),
            "lien_marked": instrument.lien_marked,
        }
        discrepancies = evaluate_discrepancies(inst_dict, latest_conf.fields)

    # Documents
    docs = session.exec(
        select(Document).where(Document.instrument_id == instrument_id)
    ).all()

    # Flags / waivers
    waivers = session.exec(
        select(FlagWaiver).where(FlagWaiver.instrument_id == instrument_id)
    ).all()

    # Case notes
    notes = session.exec(
        select(CaseNote).where(CaseNote.instrument_id == instrument_id)
    ).all()

    # Release request
    release_req = session.exec(
        select(ReleaseRequest)
        .where(ReleaseRequest.instrument_id == instrument_id)
        .order_by(col(ReleaseRequest.created_at).desc())
    ).first()

    # Per-instrument audit timeline (instrument + document + confirmation + release events)
    audit_events = session.exec(
        select(AuditEvent)
        .where(AuditEvent.entity_id == str(instrument_id))
        .order_by(col(AuditEvent.id).desc())
        .limit(50)
    ).all()

    # Institution info
    institution = session.get(Institution, instrument.institution_id)

    return {
        "instrument": hydrated.model_dump(),
        "institution": {
            "id": str(institution.id) if institution else None,
            "name": institution.name if institution else None,
            "permanent_id": institution.permanent_id if institution else None,
            "region": institution.region if institution else None,
            "is_government": institution.is_government if institution else None,
            "leased_private": institution.leased_private if institution else None,
        },
        "confirmations": [
            {
                "id": str(c.id),
                "status": c.status,
                "method": c.method,
                "requested_at": c.requested_at.isoformat(),
                "confirmed_at": c.confirmed_at.isoformat() if c.confirmed_at else None,
                "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                "fields": c.fields,
                "revoked": c.revoked,
            }
            for c in confs
        ],
        "discrepancies": discrepancies,
        "documents": [
            {
                "id": str(d.id),
                "kind": d.kind,
                "filename": d.filename,
                "sha256": d.sha256,
                "size_bytes": d.size_bytes,
                "uploaded_by": str(d.uploaded_by) if d.uploaded_by else None,
                "uploaded_at": d.uploaded_at.isoformat(),
            }
            for d in docs
        ],
        "waivers": [
            {
                "id": str(w.id),
                "code": w.code,
                "reason": w.reason,
                "waived_by": str(w.waived_by),
                "created_at": w.created_at.isoformat(),
            }
            for w in waivers
        ],
        "notes": [
            {
                "id": str(n.id),
                "body": n.body,
                "author_id": str(n.author_id),
                "created_at": n.created_at.isoformat(),
            }
            for n in notes
        ],
        "release_request": {
            "id": str(release_req.id),
            "status": release_req.status,
            "path": release_req.path,
            "checklist": release_req.checklist,
            "requested_by": str(release_req.requested_by),
            "verified_by": str(release_req.verified_by)
            if release_req.verified_by
            else None,
            "approved_by": str(release_req.approved_by)
            if release_req.approved_by
            else None,
            "receipt_token": release_req.receipt_token,
            "created_at": release_req.created_at.isoformat(),
            "updated_at": release_req.updated_at.isoformat(),
        }
        if release_req
        else None,
        "audit_timeline": [
            {
                "id": e.id,
                "ts": e.ts.isoformat(),
                "action": e.action,
                "entity": e.entity,
                "actor_id": str(e.actor_id) if e.actor_id else None,
            }
            for e in audit_events
        ],
    }
