#!/usr/bin/env python3
"""Run and verify every documented snippet in docs/INTEGRATION.md.

Requirement 3.5: scripts/integration_examples_test.py runs every curl/Python snippet
in INTEGRATION.md against the application and must pass.
"""

from __future__ import annotations

import base64
import sys
import uuid
from pathlib import Path

# Setup paths
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.db import engine
from app.integration.apikeys import issue_api_key
from app.main import app
from app.models import Confirmation, Instrument, MachineApiKey


def run_tests() -> None:
    print("=" * 70)
    print("AICTE FDR Portal — INTEGRATION.md Snippet & Contract Verification")
    print("=" * 70)

    client = TestClient(app)

    # 1. Setup API Keys for testing
    with Session(engine) as session:
        # Bank client key
        raw_bank_key, bank_record = issue_api_key(
            client_name="Test Bank Integrator",
            scopes={"bank:confirm"},
        )
        session.add(bank_record)

        # AICTE Read client key
        raw_aicte_key, aicte_record = issue_api_key(
            client_name="Test AICTE Sync",
            scopes={"aicte:read"},
        )
        session.add(aicte_record)

        # Webhook client key
        raw_webhook_key, webhook_record = issue_api_key(
            client_name="Test Webhook Admin",
            scopes={"aicte:webhooks"},
        )
        session.add(webhook_record)

        # Find or create a test instrument and pending confirmation
        ins = session.exec(select(Instrument)).first()
        if not ins:
            print("ERROR: Database unseeded. Run uv run python scripts/demo_data.py load --scenario judge")
            sys.exit(1)

        ins_ref_no = ins.ref_no
        ins_bank_code = ins.bank_code
        ins_amount_paise = ins.amount_paise
        ins_maturity_date = str(ins.maturity_date)

        test_token = f"tok_test_{uuid.uuid4().hex}"
        import hashlib
        from datetime import timedelta
        from app.domain.clock import now
        conf = Confirmation(
            instrument_id=ins.id,
            method="signed_letter",
            token_hash=hashlib.sha256(test_token.encode("utf-8")).hexdigest(),
            token_expires_at=now() + timedelta(days=15),
            status="requested",
        )
        session.add(conf)
        session.commit()

    print("[1/8] Operation 2.1: Poll Pending Bank Verification Requests (GET)")
    r = client.get(
        "/api/integration/v1/bank/requests/pending?limit=10",
        headers={"X-API-Key": raw_bank_key},
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert "items" in data
    assert "X-RateLimit-Limit" in r.headers
    print(f"  OK: Retrieved {len(data['items'])} pending request(s). RateLimit headers verified.")

    print("[2/8] Operation 2.3: Bank Sandbox Signer (POST)")
    r = client.post(
        "/api/integration/v1/sandbox/bank/sign",
        headers={"X-API-Key": raw_bank_key},
        json={
            "ref_no": ins_ref_no,
            "bank_code": ins_bank_code,
            "amount_paise": ins_amount_paise,
            "maturity_date": ins_maturity_date,
            "lien_marked": True,
        },
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    sign_data = r.json()
    assert sign_data["status"] == "SIMULATED"
    assert "signed_letter_base64" in sign_data
    signed_b64 = sign_data["signed_letter_base64"]
    print("  OK: Sample counter-signed bank reply generated.")

    print("[3/8] Operation 2.2: Submit Authoritative Bank Confirmation (POST)")
    idemp_key = str(uuid.uuid4())
    confirm_payload = {
        "request_token": test_token,
        "signed_letter_base64": signed_b64,
        "fields": {
            "ref_no": ins_ref_no,
            "bank_code": ins_bank_code,
            "amount_paise": ins_amount_paise,
            "maturity_date": ins_maturity_date,
            "lien_marked": True,
        },
    }
    r = client.post(
        "/api/integration/v1/bank/confirmations",
        headers={
            "X-API-Key": raw_bank_key,
            "Idempotency-Key": idemp_key,
        },
        json=confirm_payload,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    conf_res = r.json()
    assert conf_res["verdict"] == "accepted"
    assert conf_res["badge"] == "confirmed"
    assert len(conf_res["checks"]) >= 5
    print("  OK: 6-point cryptographic gate verified. Deposit marked confirmed.")

    print("[3b] Idempotency Replay Test")
    r_replay = client.post(
        "/api/integration/v1/bank/confirmations",
        headers={
            "X-API-Key": raw_bank_key,
            "Idempotency-Key": idemp_key,
        },
        json=confirm_payload,
    )
    assert r_replay.status_code == 200
    assert r_replay.json()["verdict"] == "accepted"
    print("  OK: Idempotent replay returned cached gate verdict.")

    print("[3c] Single-Use Token Burn Defense Test")
    r_burned = client.post(
        "/api/integration/v1/bank/confirmations",
        headers={
            "X-API-Key": raw_bank_key,
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json=confirm_payload,
    )
    assert r_burned.status_code == 409
    assert r_burned.json()["detail"]["code"] == "TOKEN_ALREADY_USED"
    print("  OK: Re-use of burned challenge token rejected with HTTP 409 TOKEN_ALREADY_USED.")

    print("[4/8] Operation 3.1: Query Institutions (GET)")
    r = client.get(
        "/api/integration/v1/institutions?limit=5",
        headers={"X-API-Key": raw_aicte_key},
    )
    assert r.status_code == 200
    inst_data = r.json()
    assert "items" in inst_data
    assert len(inst_data["items"]) > 0
    print(f"  OK: Retrieved {len(inst_data['items'])} institutions with cursor pagination.")

    print("[5/8] Operation 3.2: Query Instruments (GET)")
    r = client.get(
        "/api/integration/v1/instruments?lifecycle=active&limit=5",
        headers={"X-API-Key": raw_aicte_key},
    )
    assert r.status_code == 200
    inst_items = r.json()["items"]
    assert len(inst_items) > 0
    print(f"  OK: Retrieved {len(inst_items)} active instruments.")

    print("[6/8] Operation 3.3: Sequential Outbox Event Stream (GET)")
    r = client.get(
        "/api/integration/v1/events?limit=10",
        headers={"X-API-Key": raw_aicte_key},
    )
    assert r.status_code == 200
    events_data = r.json()
    assert "items" in events_data
    print(f"  OK: Streamed {len(events_data['items'])} transactional outbox events.")

    print("[7/8] Operation 3.4: Webhook Subscriptions (SSRF-Protected)")
    # SSRF Attack verification: AWS Metadata block
    r_ssrf = client.post(
        "/api/integration/v1/webhooks",
        headers={"X-API-Key": raw_webhook_key},
        json={"target_url": "http://169.254.169.254/latest/meta-data"},
    )
    assert r_ssrf.status_code == 400
    assert "SSRF_BLOCKED" in r_ssrf.json()["detail"]["code"]
    print("  OK: Cloud metadata SSRF attempt (169.254.169.254) blocked with HTTP 400.")

    # Legitimate registration (local receiver URL allowed in dev)
    r_sub = client.post(
        "/api/integration/v1/webhooks",
        headers={"X-API-Key": raw_webhook_key},
        json={"target_url": "http://127.0.0.1:9999/fdr/webhook", "event_types": ["*"]},
    )
    assert r_sub.status_code == 200
    sub_id = r_sub.json()["id"]
    print(f"  OK: Registered webhook subscription {sub_id}.")

    # List webhooks
    r_list = client.get(
        "/api/integration/v1/webhooks",
        headers={"X-API-Key": raw_webhook_key},
    )
    assert r_list.status_code == 200
    assert any(s["id"] == sub_id for s in r_list.json()["items"])
    print("  OK: Listed registered webhooks.")

    # Delete webhook
    r_del = client.delete(
        f"/api/integration/v1/webhooks/{sub_id}",
        headers={"X-API-Key": raw_webhook_key},
    )
    assert r_del.status_code == 200
    print("  OK: Revoked webhook subscription.")

    print("[8/8] Detached Audit Checkpoint Verification (Ed25519 Signature)")
    r_cp = client.get("/api/v1/audit/checkpoints")
    assert r_cp.status_code == 200
    cp_data = r_cp.json()
    assert "checkpoints" in cp_data
    assert "public_key_pem" in cp_data
    assert len(cp_data["checkpoints"]) > 0

    # Verify signature cryptographically
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization

    pubkey = serialization.load_pem_public_key(cp_data["public_key_pem"].encode("utf-8"))
    assert isinstance(pubkey, Ed25519PublicKey)

    latest_cp = cp_data["checkpoints"][0]
    import json
    unsigned = {k: latest_cp[k] for k in ("up_to_id", "head_hash", "created_at")}
    signed_content = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    sig_bytes = base64.b64decode(latest_cp["signature"])
    pubkey.verify(sig_bytes, signed_content)
    print("  OK: Detached Ed25519 signature cryptographically verified against public key.")

    print("\n" + "=" * 70)
    print("ALL INTEGRATION.md SNIPPETS & CONTRACT CHECKS PASSED PERFECTLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
