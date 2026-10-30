"""Tests for Demo Sample Receipt endpoints and fully released seed case.

Verifies:
1. Release Case 3 Seed:
   - Full domain release path: submitted -> verified -> released.
   - Invariant I8: Maker is never checker (verified_by != approved_by).
   - Invariant I3: Audit chain passes verification.
2. Demo Sample Receipt Endpoints:
   - GET /api/v1/demo/sample-receipt?format=token returns 200 and valid signed token.
   - GET /api/v1/demo/sample-receipt.pdf returns 200 with valid PDF < 300 KB.
   - Verification of sample token via /api/v1/receipts/verify yields valid: True.
3. Production Protection:
   - Endpoints return 404 when FASTAPI_ENV == 'production'.
   - Endpoints are excluded from the OpenAPI schema.
"""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from sqlalchemy import text
from app.core.config import settings
from app.core.db import init_db
from app.core.rls_context import install_rls_context, set_rls_context
from app.domain.receipt import verify_release_receipt
from app.models import Instrument, ReleaseRequest
from app.seed_rich_synthetic_data import seed_rich_data


def test_seeded_released_case_and_audit_integrity(db: Session) -> None:
    """Release Case 3 completes the full domain release path with audit ledger intact."""
    init_db(db)
    seed_rich_data()

    install_rls_context()
    set_rls_context(db, role="bureau")

    inst = db.exec(
        select(Instrument).where(Instrument.ref_no == "FDR-HDFC-2014-RELEASED")
    ).first()
    assert inst is not None
    assert inst.lifecycle == "released"

    req = db.exec(
        select(ReleaseRequest).where(ReleaseRequest.instrument_id == inst.id)
    ).first()
    assert req is not None
    assert req.status == "released"
    assert req.receipt_token is not None

    # Invariant I8: Maker is never checker
    assert req.verified_by is not None
    assert req.approved_by is not None
    assert req.verified_by != req.approved_by
    assert req.requested_by != req.verified_by

    # Cryptographic validity of the seeded token
    claims = verify_release_receipt(req.receipt_token)
    assert claims["path"] == "term_completion"
    assert claims["receipt_id"] is not None

    # Invariant I3: Tamper-evident hash chain must be valid (audit_verify() returns null if intact)
    tampered_id = db.execute(text("SELECT audit_verify()")).scalar()
    assert tampered_id is None, f"Audit chain verification detected tampering at event {tampered_id}"


def test_demo_sample_receipt_endpoints(client: TestClient, db: Session) -> None:
    """Public sample receipt endpoints return valid token and valid PDF in demo mode."""
    init_db(db)
    seed_rich_data()

    # 1. GET /api/v1/demo/sample-receipt?format=token
    res_tok = client.get(f"{settings.API_V1_STR}/demo/sample-receipt?format=token")
    assert res_tok.status_code == 200
    data = res_tok.json()
    assert data["status"] == "released"
    assert data["instrument_ref_no"] == "FDR-HDFC-2014-RELEASED"
    token = data["token"]
    assert token is not None

    # Verify the sample token via the public verify endpoint
    res_verify = client.post(
        f"{settings.API_V1_STR}/receipts/verify",
        json={"token": token},
    )
    assert res_verify.status_code == 200
    v_data = res_verify.json()
    assert v_data["valid"] is True
    assert v_data["claims"]["path"] == "term_completion"

    # 2. GET /api/v1/demo/sample-receipt.pdf
    res_pdf = client.get(f"{settings.API_V1_STR}/demo/sample-receipt.pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF-")
    assert len(res_pdf.content) < 300 * 1024


def test_demo_sample_receipt_production_block_and_schema(client: TestClient) -> None:
    """Sample receipt endpoints must return 404 in production and remain excluded from OpenAPI."""
    # 1. OpenAPI schema exclusion
    res_openapi = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert res_openapi.status_code == 200
    schema = res_openapi.json()
    paths = schema.get("paths", {})
    assert f"{settings.API_V1_STR}/demo/sample-receipt" not in paths
    assert f"{settings.API_V1_STR}/demo/sample-receipt.pdf" not in paths

    # 2. Block in production
    orig_env = settings.FASTAPI_ENV
    try:
        settings.FASTAPI_ENV = "production"
        res_prod_json = client.get(f"{settings.API_V1_STR}/demo/sample-receipt")
        assert res_prod_json.status_code == 404

        res_prod_pdf = client.get(f"{settings.API_V1_STR}/demo/sample-receipt.pdf")
        assert res_prod_pdf.status_code == 404
    finally:
        settings.FASTAPI_ENV = orig_env
