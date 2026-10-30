"""Comprehensive tests for server-side PDF Statement Report export (GET /api/v1/reports/pdf).

Verifies:
1. Valid PDF generation with correct headers and Content-Type.
2. Required disclaimers and branding:
   - "AICTE FDR Portal (prototype, PS 26265)"
   - "Synthetic data, SIMULATED bank and email, DEMO rule values. Not an official document."
   - "DEMO" watermark
3. Money display uses "Rs." prefix (standard ReportLab Helvetica fonts lack ₹ symbol).
4. Regional Officer RLS isolation:
   - NR officer export contains NR references and zero WR references.
   - WR officer export contains WR references and zero NR references.
5. Specific tab filtering (pending-verifications, upcoming-maturities, etc.) and full report.
6. Audit ledger entry logged with action "report.exported" and format "pdf".
"""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import init_db
from app.models import AuditEvent
from app.seed_reports_topup import seed_reports_topup
from app.seed_rich_synthetic_data import seed_rich_data
from tests.utils.user import authentication_token_from_email


def _decode_pdf_text(pdf_bytes: bytes) -> str:
    """Decode raw uncompressed PDF stream text handling PDF string literal escaping."""
    raw = pdf_bytes.decode("latin1", errors="ignore")
    return raw.replace(r"\(", "(").replace(r"\)", ")")


def test_reports_pdf_header_disclaimers_watermark_and_rs(
    client: TestClient, db: Session
) -> None:
    """PDF export must contain mandatory prototype header, disclaimer, watermark, and Rs currency."""
    init_db(db)
    seed_rich_data()
    seed_reports_topup(db)

    nr_headers = authentication_token_from_email(
        client=client, email="officer.north@example.com", db=db
    )

    r = client.get(f"{settings.API_V1_STR}/reports/pdf", headers=nr_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in r.headers["content-disposition"]
    assert len(r.content) > 1000

    pdf_text = _decode_pdf_text(r.content)

    # 1. Official prototype header
    assert "AICTE FDR Portal (prototype, PS 26265)" in pdf_text

    # 2. Visible disclaimer
    assert (
        "Synthetic data, SIMULATED bank and email, DEMO rule values. Not an official document."
        in pdf_text
    )

    # 3. DEMO watermark
    assert "DEMO" in pdf_text

    # 4. Currency: "Rs." must be used; unicode Rupee symbol (₹) must NOT be present
    assert "Rs." in pdf_text
    assert "₹" not in pdf_text

    # 5. Footer elements: page number and demo clock date
    assert "Generated:" in pdf_text
    assert "Demo Date:" in pdf_text
    assert "Page " in pdf_text


def test_reports_pdf_nr_and_wr_rls_isolation(
    client: TestClient, db: Session
) -> None:
    """NR officer PDF must contain NR records and zero WR records; WR must contain WR and zero NR."""
    init_db(db)
    seed_rich_data()
    seed_reports_topup(db)

    nr_headers = authentication_token_from_email(
        client=client, email="officer.north@example.com", db=db
    )
    wr_headers = authentication_token_from_email(
        client=client, email="officer.west@example.com", db=db
    )

    # NR Export
    r_nr = client.get(f"{settings.API_V1_STR}/reports/pdf", headers=nr_headers)
    assert r_nr.status_code == 200
    nr_text = _decode_pdf_text(r_nr.content)

    assert "SYN-REP-NR" in nr_text
    assert "SYN-REP-WR" not in nr_text
    assert "Region: NR" in nr_text

    # WR Export
    r_wr = client.get(f"{settings.API_V1_STR}/reports/pdf", headers=wr_headers)
    assert r_wr.status_code == 200
    wr_text = _decode_pdf_text(r_wr.content)

    assert "SYN-REP-WR" in wr_text
    assert "SYN-REP-NR" not in wr_text
    assert "Region: WR" in wr_text


def test_reports_pdf_individual_tab_filters(
    client: TestClient, db: Session
) -> None:
    """PDF export supports optional report_type query param for each Statement Reports tab."""
    init_db(db)
    seed_rich_data()
    seed_reports_topup(db)

    nr_headers = authentication_token_from_email(
        client=client, email="officer.north@example.com", db=db
    )

    tabs = [
        ("pending-verifications", "Statement Report: Pending Verifications"),
        ("upcoming-maturities", "Statement Report: Upcoming Maturities"),
        ("missing-documents", "Statement Report: Missing Documents"),
        ("cases-needing-intervention", "Statement Report: Cases Needing Intervention"),
    ]

    for tab_id, expected_title in tabs:
        r = client.get(
            f"{settings.API_V1_STR}/reports/pdf?report_type={tab_id}",
            headers=nr_headers,
        )
        assert r.status_code == 200
        text = _decode_pdf_text(r.content)
        assert expected_title in text
        assert f"statement_report_{tab_id}_" in r.headers["content-disposition"]


def test_reports_pdf_audit_trail_logging(
    client: TestClient, db: Session
) -> None:
    """PDF export logs an audit event with action report.exported and format pdf."""
    init_db(db)
    seed_rich_data()
    seed_reports_topup(db)

    nr_headers = authentication_token_from_email(
        client=client, email="officer.north@example.com", db=db
    )

    r = client.get(
        f"{settings.API_V1_STR}/reports/pdf?report_type=upcoming-maturities",
        headers=nr_headers,
    )
    assert r.status_code == 200

    last_audit = db.exec(
        select(AuditEvent)
        .where(AuditEvent.action == "report.exported")
        .order_by(AuditEvent.id.desc())
    ).first()

    assert last_audit is not None
    assert last_audit.entity == "report"
    assert last_audit.entity_id == "pdf-upcoming-maturities"
    assert last_audit.payload.get("format") == "pdf"
    assert last_audit.payload.get("report_type") == "upcoming-maturities"
