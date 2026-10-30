import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.core.audit import audit_append
from app.domain.clock import today as clock_today
from app.domain.csv_safe import csv_safe
from app.domain.reports_pdf import generate_reports_pdf
from app.domain.trust import Confirmation as TrustConfirmation
from app.domain.trust import badge
from app.models import Confirmation, Document, Institution, Instrument, Obligation

router = APIRouter(prefix="/reports", tags=["reports"])

VALID_REPORT_TYPES = {
    "pending-verifications",
    "upcoming-maturities",
    "missing-documents",
    "cases-needing-intervention",
    "all",
    "full",
}


@router.get("/pdf")
def export_reports_pdf(
    session: SessionDep,
    current_user: CurrentUser,
    report_type: str | None = None,
) -> Response:
    """Server-side PDF statement report export with DEMO watermark and prototype disclaimers."""
    if report_type:
        normalized = report_type.strip().lower().replace("_", "-")
        if normalized not in VALID_REPORT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid report_type '{report_type}'. Must be one of: pending-verifications, upcoming-maturities, missing-documents, cases-needing-intervention",
            )
    pdf_bytes, filename, total_rows = generate_reports_pdf(
        session=session,
        current_user=current_user,
        report_type=report_type,
    )

    audit_append(
        session,
        actor_id=current_user.id,
        action="report.exported",
        entity="report",
        entity_id=f"pdf-{report_type or 'all'}",
        payload={
            "format": "pdf",
            "report_type": report_type or "all",
            "row_count": total_rows,
        },
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _hydrate_badge(inst: Instrument, session: SessionDep) -> str:
    confs = session.exec(
        select(Confirmation)
        .where(Confirmation.instrument_id == inst.id)
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
    return badge(
        {
            "ref_no": inst.ref_no,
            "bank_code": inst.bank_code,
            "amount_paise": inst.amount_paise,
            "maturity_date": str(inst.maturity_date),
        },
        trust_confs,
        datetime.now(UTC),
    )


def _make_csv_response(
    filename: str, headers: list[str], rows: list[list[Any]]
) -> Response:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([csv_safe(h) for h in headers])
    for row in rows:
        writer.writerow([csv_safe(cell) for cell in row])

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
    )


@router.get("/pending-verifications")
def report_pending_verifications(
    session: SessionDep,
    current_user: CurrentUser,
) -> Response:
    """CSV report of FDRs currently in pending verification."""
    query = select(Instrument).where(Instrument.lifecycle == "pending")
    if current_user.role == "institution" and current_user.institution_id:
        query = query.where(Instrument.institution_id == current_user.institution_id)
    elif current_user.role == "regional" and current_user.region:
        query = query.where(Instrument.region == current_user.region)

    instruments = session.exec(query).all()
    headers = [
        "Instrument ID",
        "Institution ID",
        "Region",
        "Kind",
        "Ref No",
        "Bank Code",
        "Amount (Paise)",
        "Issue Date",
        "Maturity Date",
        "Badge",
    ]
    rows: list[list[Any]] = []
    for inst in instruments:
        b = _hydrate_badge(inst, session)
        rows.append(
            [
                str(inst.id),
                str(inst.institution_id),
                inst.region,
                inst.kind,
                inst.ref_no,
                inst.bank_code,
                inst.amount_paise,
                str(inst.issue_date),
                str(inst.maturity_date),
                b,
            ]
        )

    audit_append(
        session,
        actor_id=current_user.id,
        action="report.exported",
        entity="report",
        entity_id="pending-verifications",
        payload={"row_count": len(rows)},
    )
    return _make_csv_response("pending_verifications", headers, rows)


@router.get("/upcoming-maturities")
def report_upcoming_maturities(
    session: SessionDep,
    current_user: CurrentUser,
) -> Response:
    """CSV report of FDRs maturing within 90 days."""
    today_val = clock_today()
    cutoff = today_val + timedelta(days=90)
    query = (
        select(Instrument)
        .where(Instrument.lifecycle == "active")
        .where(Instrument.maturity_date <= cutoff)
    )
    if current_user.role == "institution" and current_user.institution_id:
        query = query.where(Instrument.institution_id == current_user.institution_id)
    elif current_user.role == "regional" and current_user.region:
        query = query.where(Instrument.region == current_user.region)

    instruments = session.exec(query).all()
    headers = [
        "Instrument ID",
        "Institution ID",
        "Region",
        "Ref No",
        "Bank Code",
        "Amount (Paise)",
        "Maturity Date",
        "Days to Maturity",
    ]
    rows: list[list[Any]] = []
    for inst in instruments:
        days_to_mat = (inst.maturity_date - today_val).days
        rows.append(
            [
                str(inst.id),
                str(inst.institution_id),
                inst.region,
                inst.ref_no,
                inst.bank_code,
                inst.amount_paise,
                str(inst.maturity_date),
                days_to_mat,
            ]
        )

    audit_append(
        session,
        actor_id=current_user.id,
        action="report.exported",
        entity="report",
        entity_id="upcoming-maturities",
        payload={"row_count": len(rows)},
    )
    return _make_csv_response("upcoming_maturities", headers, rows)


@router.get("/missing-documents")
def report_missing_documents(
    session: SessionDep,
    current_user: CurrentUser,
) -> Response:
    """CSV report of instruments missing mandatory deposit proof or fdr scan."""
    query = select(Instrument).where(
        col(Instrument.lifecycle).in_(["pending", "active"])
    )
    if current_user.role == "institution" and current_user.institution_id:
        query = query.where(Instrument.institution_id == current_user.institution_id)
    elif current_user.role == "regional" and current_user.region:
        query = query.where(Instrument.region == current_user.region)

    instruments = session.exec(query).all()
    headers = [
        "Instrument ID",
        "Institution Name",
        "Region",
        "Ref No",
        "Missing Documents",
    ]
    rows: list[list[Any]] = []
    for inst in instruments:
        docs = session.exec(
            select(Document).where(Document.instrument_id == inst.id)
        ).all()
        doc_kinds = {d.kind for d in docs}
        missing: list[str] = []
        if "fdr_scan" not in doc_kinds:
            missing.append("fdr_scan")
        if "payment_proof" not in doc_kinds:
            missing.append("payment_proof")

        if missing:
            inst_obj = session.get(Institution, inst.institution_id)
            rows.append(
                [
                    str(inst.id),
                    inst_obj.name if inst_obj else "",
                    inst.region,
                    inst.ref_no,
                    "; ".join(missing),
                ]
            )

    audit_append(
        session,
        actor_id=current_user.id,
        action="report.exported",
        entity="report",
        entity_id="missing-documents",
        payload={"row_count": len(rows)},
    )
    return _make_csv_response("missing_documents", headers, rows)


@router.get("/cases-needing-intervention")
def report_cases_needing_intervention(
    session: SessionDep,
    current_user: CurrentUser,
) -> Response:
    """CSV report of cases with open overdue obligations or maturity past due."""
    today_val = clock_today()
    query = select(Instrument).where(
        col(Instrument.lifecycle).in_(["pending", "active", "matured"])
    )
    if current_user.role == "institution" and current_user.institution_id:
        query = query.where(Instrument.institution_id == current_user.institution_id)
    elif current_user.role == "regional" and current_user.region:
        query = query.where(Instrument.region == current_user.region)

    instruments = session.exec(query).all()
    headers = [
        "Instrument ID",
        "Ref No",
        "Region",
        "Lifecycle",
        "Intervention Reason",
    ]
    rows: list[list[Any]] = []
    for inst in instruments:
        reasons: list[str] = []
        if inst.lifecycle == "matured":
            reasons.append("Instrument has reached maturity without renewal or release")

        obs = session.exec(
            select(Obligation)
            .where(Obligation.instrument_id == inst.id)
            .where(Obligation.status == "open")
            .where(Obligation.due_date < today_val)
        ).all()
        for o in obs:
            reasons.append(f"Overdue obligation: {o.kind} (due {o.due_date})")

        if reasons:
            rows.append(
                [
                    str(inst.id),
                    inst.ref_no,
                    inst.region,
                    inst.lifecycle,
                    "; ".join(reasons),
                ]
            )

    audit_append(
        session,
        actor_id=current_user.id,
        action="report.exported",
        entity="report",
        entity_id="cases-needing-intervention",
        payload={"row_count": len(rows)},
    )
    return _make_csv_response("cases_needing_intervention", headers, rows)


# ── JSON preview endpoints (no CSV download, no audit event) ──────────────────


@router.get("/pending-verifications/preview")
def preview_pending_verifications(
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = 50,
) -> dict[str, Any]:
    """JSON preview (up to limit rows) for the pending-verifications report."""
    query = select(Instrument).where(Instrument.lifecycle == "pending")
    if current_user.role == "institution" and current_user.institution_id:
        query = query.where(Instrument.institution_id == current_user.institution_id)
    elif current_user.role == "regional" and current_user.region:
        query = query.where(Instrument.region == current_user.region)
    instruments = session.exec(query.limit(limit)).all()
    rows = []
    for i in instruments:
        inst_obj = session.get(Institution, i.institution_id)
        rows.append(
            {
                "id": str(i.id),
                "institution_id": str(i.institution_id),
                "institution_name": inst_obj.name if inst_obj else "",
                "region": i.region,
                "kind": i.kind,
                "ref_no": i.ref_no,
                "bank_code": i.bank_code,
                "amount_paise": i.amount_paise,
                "issue_date": str(i.issue_date),
                "maturity_date": str(i.maturity_date),
                "lifecycle": i.lifecycle,
                "badge": _hydrate_badge(i, session),
            }
        )
    return {"rows": rows, "count": len(rows)}


@router.get("/upcoming-maturities/preview")
def preview_upcoming_maturities(
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = 50,
) -> dict[str, Any]:
    """JSON preview for the upcoming-maturities report."""
    today_val = clock_today()
    cutoff = today_val + timedelta(days=90)
    query = (
        select(Instrument)
        .where(Instrument.lifecycle == "active")
        .where(Instrument.maturity_date <= cutoff)
    )
    if current_user.role == "institution" and current_user.institution_id:
        query = query.where(Instrument.institution_id == current_user.institution_id)
    elif current_user.role == "regional" and current_user.region:
        query = query.where(Instrument.region == current_user.region)
    instruments = session.exec(query.limit(limit)).all()
    rows = []
    for i in instruments:
        inst_obj = session.get(Institution, i.institution_id)
        rows.append(
            {
                "id": str(i.id),
                "institution_id": str(i.institution_id),
                "institution_name": inst_obj.name if inst_obj else "",
                "region": i.region,
                "ref_no": i.ref_no,
                "bank_code": i.bank_code,
                "amount_paise": i.amount_paise,
                "maturity_date": str(i.maturity_date),
                "lifecycle": i.lifecycle,
                "days_to_maturity": (i.maturity_date - today_val).days,
            }
        )
    return {"rows": rows, "count": len(rows)}


@router.get("/missing-documents/preview")
def preview_missing_documents(
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = 50,
) -> dict[str, Any]:
    """JSON preview for the missing-documents report."""
    query = select(Instrument).where(
        col(Instrument.lifecycle).in_(["pending", "active"])
    )
    if current_user.role == "institution" and current_user.institution_id:
        query = query.where(Instrument.institution_id == current_user.institution_id)
    elif current_user.role == "regional" and current_user.region:
        query = query.where(Instrument.region == current_user.region)
    instruments = session.exec(query.limit(limit)).all()
    rows = []
    for i in instruments:
        docs = session.exec(
            select(Document).where(Document.instrument_id == i.id)
        ).all()
        doc_kinds = {d.kind for d in docs}
        missing = [k for k in ("fdr_scan", "payment_proof") if k not in doc_kinds]
        if missing:
            inst_obj = session.get(Institution, i.institution_id)
            rows.append(
                {
                    "id": str(i.id),
                    "institution_id": str(i.institution_id),
                    "institution_name": inst_obj.name if inst_obj else "",
                    "region": i.region,
                    "ref_no": i.ref_no,
                    "bank_code": i.bank_code,
                    "amount_paise": i.amount_paise,
                    "maturity_date": str(i.maturity_date),
                    "lifecycle": i.lifecycle,
                    "missing": missing,
                }
            )
    return {"rows": rows, "count": len(rows)}


@router.get("/cases-needing-intervention/preview")
def preview_cases_needing_intervention(
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = 50,
) -> dict[str, Any]:
    """JSON preview for the cases-needing-intervention report."""
    today_val = clock_today()
    query = select(Instrument).where(
        col(Instrument.lifecycle).in_(["pending", "active", "matured"])
    )
    if current_user.role == "institution" and current_user.institution_id:
        query = query.where(Instrument.institution_id == current_user.institution_id)
    elif current_user.role == "regional" and current_user.region:
        query = query.where(Instrument.region == current_user.region)
    instruments = session.exec(query.limit(limit)).all()
    rows = []
    for i in instruments:
        reasons: list[str] = []
        if i.lifecycle == "matured":
            reasons.append("Reached maturity without renewal or release")
        obs = session.exec(
            select(Obligation)
            .where(Obligation.instrument_id == i.id)
            .where(Obligation.status == "open")
            .where(Obligation.due_date < today_val)
        ).all()
        for o in obs:
            reasons.append(f"Overdue {o.kind} (due {o.due_date})")
        if reasons:
            inst_obj = session.get(Institution, i.institution_id)
            rows.append(
                {
                    "id": str(i.id),
                    "institution_id": str(i.institution_id),
                    "institution_name": inst_obj.name if inst_obj else "",
                    "ref_no": i.ref_no,
                    "region": i.region,
                    "bank_code": i.bank_code,
                    "amount_paise": i.amount_paise,
                    "maturity_date": str(i.maturity_date),
                    "lifecycle": i.lifecycle,
                    "reasons": reasons,
                }
            )
    return {"rows": rows, "count": len(rows)}
