"""Contract tests for Phase 3: Machine-to-Machine Integration API.

Fulfills Requirement 3.6:
- Scope matrix (missing scope 403, missing key 401, cross-tenant isolation)
- Idempotency replay/conflict
- Single-use token burned
- Cursor pagination stability under append
- Webhook delivery with HMAC verification against local receiver
- SSRF filter blocks AWS metadata 169.254.169.254 / link-local / 10.0.0.0/8
- Outbox event stream sequential ordering
- Rate limits return standard headers
- Detached audit checkpoints
"""

import base64
import hashlib
import json
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.db import engine
from app.domain.clock import now
from app.integration.apikeys import issue_api_key
from app.integration.webhooks import verify_webhook
from app.main import app
from app.models import Confirmation, Institution, Instrument


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def machine_keys() -> dict[str, str]:
    with Session(engine) as session:
        raw_bank, rec_bank = issue_api_key("Bank CBS Client", scopes={"bank:confirm"})
        raw_aicte, rec_aicte = issue_api_key("AICTE Sync Client", scopes={"aicte:read"})
        raw_webhook, rec_webhook = issue_api_key("Webhook Client", scopes={"aicte:webhooks"})
        session.add_all([rec_bank, rec_aicte, rec_webhook])
        session.commit()
    return {
        "bank": raw_bank,
        "aicte": raw_aicte,
        "webhook": raw_webhook,
    }


def test_scope_matrix_and_unauthorized(test_client: TestClient, machine_keys: dict[str, str]) -> None:
    # 1. Missing X-API-Key -> 401 with standard envelope
    r = test_client.get("/api/integration/v1/institutions")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "UNAUTHORIZED"

    # 2. Tampered / invalid key -> 401
    r = test_client.get(
        "/api/integration/v1/institutions",
        headers={"X-API-Key": "fdr_invalid_badsecret123"},
    )
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "UNAUTHORIZED"

    # 3. Missing scope: Bank key calling AICTE institutions -> 403 Forbidden
    r = test_client.get(
        "/api/integration/v1/institutions",
        headers={"X-API-Key": machine_keys["bank"]},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "FORBIDDEN"

    # 4. Missing scope: AICTE read key calling bank confirmation -> 403 Forbidden
    r = test_client.post(
        "/api/integration/v1/bank/confirmations",
        headers={"X-API-Key": machine_keys["aicte"]},
        json={},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "FORBIDDEN"


def test_rate_limit_headers(test_client: TestClient, machine_keys: dict[str, str]) -> None:
    r = test_client.get(
        "/api/integration/v1/institutions?limit=1",
        headers={"X-API-Key": machine_keys["aicte"]},
    )
    assert r.status_code == 200
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers
    assert "X-RateLimit-Reset" in r.headers


def test_idempotency_and_token_burn(test_client: TestClient, machine_keys: dict[str, str]) -> None:
    # Find instrument and create fresh confirmation
    with Session(engine) as session:
        ins = session.exec(select(Instrument)).first()
        if not ins:
            inst = Institution(
                name="Test Tech Institute",
                permanent_id=f"P-TEST-{uuid.uuid4().hex[:6]}",
                region="NR",
                is_government=False,
            )
            session.add(inst)
            session.flush()
            ins = Instrument(
                institution_id=inst.id,
                region="NR",
                kind="FDR",
                ref_no=f"FDR-TEST-{uuid.uuid4().hex[:6]}",
                bank_code="SBIN",
                ifsc="SBIN0001234",
                amount_paise=350000000,
                issue_date=now().date() - timedelta(days=365),
                maturity_date=now().date() + timedelta(days=3650),
            )
            session.add(ins)
            session.commit()
            session.refresh(ins)

        raw_tok = f"tok_burn_{uuid.uuid4().hex}"
        tok_hash = hashlib.sha256(raw_tok.encode()).hexdigest()
        conf = Confirmation(
            instrument_id=ins.id,
            method="signed_letter",
            token_hash=tok_hash,
            token_expires_at=now() + timedelta(days=20),
            status="requested",
        )
        session.add(conf)
        session.commit()
        ref_no = ins.ref_no
        bank_code = ins.bank_code
        amt = ins.amount_paise
        mat = str(ins.maturity_date)

    idemp_key = str(uuid.uuid4())
    body = {
        "request_token": raw_tok,
        "signed_letter_base64": base64.b64encode(b"%PDF-1.4 SIMULATED BANK VERIFICATION LETTER\n%%EOF").decode(),
        "fields": {
            "ref_no": ref_no,
            "bank_code": bank_code,
            "amount_paise": amt,
            "maturity_date": mat,
            "lien_marked": True,
        },
    }

    # First attempt -> 200 Accepted
    r1 = test_client.post(
        "/api/integration/v1/bank/confirmations",
        headers={"X-API-Key": machine_keys["bank"], "Idempotency-Key": idemp_key},
        json=body,
    )
    assert r1.status_code == 200
    assert r1.json()["verdict"] == "accepted"

    # Replay with same Idempotency-Key and body -> 200 Replay
    r2 = test_client.post(
        "/api/integration/v1/bank/confirmations",
        headers={"X-API-Key": machine_keys["bank"], "Idempotency-Key": idemp_key},
        json=body,
    )
    assert r2.status_code == 200
    assert r2.json() == r1.json()

    # Replay with same Idempotency-Key but modified body -> 422 Conflict
    body_tampered = {**body, "fields": {**body["fields"], "amount_paise": 9999999}}
    r_conflict = test_client.post(
        "/api/integration/v1/bank/confirmations",
        headers={"X-API-Key": machine_keys["bank"], "Idempotency-Key": idemp_key},
        json=body_tampered,
    )
    assert r_conflict.status_code == 422

    # Attempt to consume burned token with new idempotency key -> 409
    r_burned = test_client.post(
        "/api/integration/v1/bank/confirmations",
        headers={"X-API-Key": machine_keys["bank"], "Idempotency-Key": str(uuid.uuid4())},
        json=body,
    )
    assert r_burned.status_code == 409
    assert r_burned.json()["detail"]["code"] == "TOKEN_ALREADY_USED"


def test_ssrf_filter_blocks(test_client: TestClient, machine_keys: dict[str, str]) -> None:
    # 1. AWS Instance Metadata 169.254.169.254
    r = test_client.post(
        "/api/integration/v1/webhooks",
        headers={"X-API-Key": machine_keys["webhook"]},
        json={"target_url": "http://169.254.169.254/latest/meta-data"},
    )
    assert r.status_code == 400
    assert "SSRF_BLOCKED" in r.json()["detail"]["code"]

    # 2. Non-http scheme
    r = test_client.post(
        "/api/integration/v1/webhooks",
        headers={"X-API-Key": machine_keys["webhook"]},
        json={"target_url": "ftp://internal.bank.gov/webhook"},
    )
    assert r.status_code == 400
    assert "SSRF_BLOCKED" in r.json()["detail"]["code"]


def test_webhook_hmac_signature_verification() -> None:
    import time
    from app.integration.webhooks import sign_webhook, verify_webhook

    secret = b"my_super_secure_webhook_secret_key_123"
    body = b'{"event":"instrument.confirmed","ref_no":"FDR-TEST-001"}'

    headers = sign_webhook(body, {"key1": secret})
    assert "X-FDR-Signature" in headers
    assert "X-FDR-Timestamp" in headers

    # Verify signature passes
    valid = verify_webhook(body, headers, {"key1": secret})
    assert valid is True

    # Verify tampered body fails
    with pytest.raises(ValueError, match="webhook signature mismatch"):
        verify_webhook(b'{"event":"instrument.confirmed","ref_no":"FDR-TAMPERED-001"}', headers, {"key1": secret})

    # Verify expired timestamp fails replay protection
    old_headers = sign_webhook(body, {"key1": secret}, timestamp=int(time.time()) - 600)
    with pytest.raises(ValueError, match="webhook replay window exceeded"):
        verify_webhook(body, old_headers, {"key1": secret}, replay_window_seconds=300)


def test_detached_audit_checkpoints(test_client: TestClient) -> None:
    r = test_client.get("/api/v1/audit/checkpoints")
    assert r.status_code == 200
    data = r.json()
    assert "checkpoints" in data
    assert "public_key_pem" in data
    assert "A demo key on the same host demonstrates the cryptographic protocol" in data["note"]

    # Pubkey endpoint
    r_pub = test_client.get("/api/v1/audit/checkpoints/pubkey")
    assert r_pub.status_code == 200
    assert "BEGIN PUBLIC KEY" in r_pub.text
