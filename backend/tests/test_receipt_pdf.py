"""Tests for Release Receipt PDF generation and download route.

Verifies:
1. PDF builder:
   - Starts with '%PDF-'
   - Total size < 300 KB
   - Decoded stream text contains required disclaimers, title, and verified field labels.
2. Route GET /api/v1/release/{id}/receipt.pdf:
   - 401 Unauthenticated
   - 404 Nonexistent release request
   - 409 Conflict when release request is not in 'released' status (e.g. 'submitted' or 'verified')
   - 404 Cross-tenant institution access
   - 200 Valid PDF response for authorized user when released
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import init_db
from app.core.rls_context import install_rls_context, set_rls_context
from app.domain.receipt import sign_release_receipt
from app.domain.receipt_pdf import build_release_receipt_pdf
from app.models import Institution, Instrument, ReleaseRequest, User
from app.seed_rich_synthetic_data import seed_rich_data
from tests.utils.user import authentication_token_from_email


def _decode_pdf_text(pdf_bytes: bytes) -> str:
    """Decode raw uncompressed PDF stream text handling PDF escaping."""
    raw = pdf_bytes.decode("latin1", errors="ignore")
    return raw.replace(r"\(", "(").replace(r"\)", ")")


def test_build_release_receipt_pdf_structure() -> None:
    """PDF builder produces valid PDF under 300 KB with required markers and disclaimer."""
    token = sign_release_receipt(
        instrument_id="inst-test-01",
        instrument_ref_no="FDR-TEST-001",
        path="term_completion",
    )

    pdf_bytes = build_release_receipt_pdf(
        token=token,
        instrument_ref_no="FDR-TEST-001",
        institution_name="Government Engineering College",
        bank_code="SBI",
        amount_paise=500000000,
    )

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) < 300 * 1024  # under 300 KB
    assert len(pdf_bytes) > 2000

    pdf_text = _decode_pdf_text(pdf_bytes)
    assert "Demo release receipt" in pdf_text
    assert "AICTE FDR Portal (prototype, PS 26265)" in pdf_text
    assert "DEMO" in pdf_text
    assert "Demo release receipt. Synthetic data. Not a bank instrument; no funds are released." in pdf_text
    assert "VERIFIED FIELDS" in pdf_text
    assert "INFORMATIONAL" in pdf_text
    assert "term_completion" in pdf_text
    assert "Rs. 50,00,000.00" in pdf_text


def test_receipt_pdf_route_unauthenticated(client: TestClient) -> None:
    """Unauthenticated request must return 401."""
    random_id = uuid.uuid4()
    res = client.get(f"{settings.API_V1_STR}/release/{random_id}/receipt.pdf")
    assert res.status_code == 401


def test_receipt_pdf_route_lifecycle_and_tenant_guards(
    client: TestClient, db: Session
) -> None:
    """Route enforces 404 for not found, 409 for unreleased, 404 for cross-tenant, and 200 for released."""
    init_db(db)
    seed_rich_data()

    install_rls_context()
    set_rls_context(db, role="bureau")

    north_headers = authentication_token_from_email(
        client=client, email="inst.north1@example.com", db=db
    )
    west_headers = authentication_token_from_email(
        client=client, email="inst.west@example.com", db=db
    )
    bureau_headers = authentication_token_from_email(
        client=client, email="bureau.approver@example.com", db=db
    )

    # 1. Nonexistent release request -> 404
    missing_id = uuid.uuid4()
    res_404 = client.get(
        f"{settings.API_V1_STR}/release/{missing_id}/receipt.pdf",
        headers=bureau_headers,
    )
    assert res_404.status_code == 404

    # 2. Existing request in 'submitted' status -> 409 Conflict
    sub_inst = db.exec(
        select(Instrument).where(Instrument.ref_no == "FDR-ICIC-2016-MATURED1")
    ).first()
    assert sub_inst is not None

    # Align users with their tenant institution ids and bureau role in db
    u_north = db.exec(
        select(User).where(User.email == "inst.north1@example.com")
    ).first()
    assert u_north is not None
    u_north.institution_id = sub_inst.institution_id
    db.add(u_north)

    u_west = db.exec(
        select(User).where(User.email == "inst.west@example.com")
    ).first()
    assert u_west is not None
    west_inst = db.exec(
        select(Institution).where(Institution.region == "WR")
    ).first()
    assert west_inst is not None
    u_west.institution_id = west_inst.id
    db.add(u_west)

    u_bureau = db.exec(
        select(User).where(User.email == "bureau.approver@example.com")
    ).first()
    assert u_bureau is not None
    u_bureau.role = "bureau"
    db.add(u_bureau)
    db.commit()

    sub_req = db.exec(
        select(ReleaseRequest).where(ReleaseRequest.instrument_id == sub_inst.id)
    ).first()
    assert sub_req is not None
    assert sub_req.status == "submitted"

    res_409 = client.get(
        f"{settings.API_V1_STR}/release/{sub_req.id}/receipt.pdf",
        headers=north_headers,
    )
    assert res_409.status_code == 409
    assert "not in released status" in res_409.json()["detail"].lower()

    # 3. Create a released request for north institution
    released_token = sign_release_receipt(
        instrument_id=str(sub_inst.id),
        instrument_ref_no=sub_inst.ref_no,
        path="term_completion",
        release_id=str(sub_req.id),
    )
    sub_req.status = "released"
    sub_req.receipt_token = released_token
    sub_req.updated_at = datetime.now(UTC)
    db.add(sub_req)
    db.commit()
    db.refresh(sub_req)

    # 4. Cross-tenant access: West institution user requests North institution's receipt -> 404
    res_cross = client.get(
        f"{settings.API_V1_STR}/release/{sub_req.id}/receipt.pdf",
        headers=west_headers,
    )
    assert res_cross.status_code == 404

    # 5. Legitimate owner (North institution) accesses receipt -> 200 OK application/pdf
    res_200_inst = client.get(
        f"{settings.API_V1_STR}/release/{sub_req.id}/receipt.pdf",
        headers=north_headers,
    )
    assert res_200_inst.status_code == 200
    assert res_200_inst.headers["content-type"] == "application/pdf"
    assert res_200_inst.content.startswith(b"%PDF-")
    assert len(res_200_inst.content) < 300 * 1024

    # 6. Bureau approver accesses receipt -> 200 OK application/pdf
    res_200_bureau = client.get(
        f"{settings.API_V1_STR}/release/{sub_req.id}/receipt.pdf",
        headers=bureau_headers,
    )
    assert res_200_bureau.status_code == 200
    assert res_200_bureau.headers["content-type"] == "application/pdf"
    assert res_200_bureau.content.startswith(b"%PDF-")
