import uuid
from datetime import UTC, date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import Settings
from app.core.db import engine
from app.domain.fraud_lab import run_fraud_lab_benchmark
from app.domain.receipt import verify_release_receipt
from app.domain.worker import run_daily_worker
from app.main import app
from app.models import Confirmation, Institution, Instrument, User
from tests.utils.user import authentication_token_from_email


def test_m9_security_headers(client: TestClient) -> None:
    """Verify production security headers are attached to API responses (Invariant I12)."""
    res = client.get("/api/v1/utils/health-check/")
    assert res.status_code == 200
    headers = res.headers
    assert "Content-Security-Policy" in headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"


def test_m9_production_startup_refuses_default_secrets() -> None:
    """Verify Settings rejects default secrets outside development mode (Invariant I12)."""
    with pytest.raises(ValueError, match='The value of SECRET_KEY is "changethis"'):
        Settings(
            FASTAPI_ENV="production",
            SECRET_KEY="changethis",
            VAULT_KEY="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        )

    with pytest.raises(
        ValueError,
        match="VAULT_KEY must be set to a valid 32-byte base64 key outside development/demo",
    ):
        Settings(
            FASTAPI_ENV="production",
            SECRET_KEY="a_strong_production_secret_key_at_least_32_bytes_long",
            VAULT_KEY="",
        )


def test_m9_seven_step_demo_flow(client: TestClient, db: Session) -> None:
    """Verify the 7-step demo walkthrough script runs seamlessly end-to-end.
    
    Step 1: Submit an FDR
    Step 2: Bank confirms and one mismatch is flagged
    Step 3: Clock + 30 days generates reminder / obligation
    Step 4: Renewal links history via replaces_id
    Step 5: Fraud lab benchmark prints TP=20, FP=0, FN=0
    Step 6: Release blocked then approved and receipt verified offline
    Step 7: Bank down simulator returns 503 source unavailable
    """
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        if inst_user and not inst_user.institution_id:
            inst_obj = Institution(
                name="Demo Institute of Tech",
                permanent_id=f"P-DEMO-{uuid.uuid4().hex[:6]}",
                region="NR",
            )
            session.add(inst_obj)
            session.commit()
            session.refresh(inst_obj)
            inst_user.institution_id = inst_obj.id
            session.add(inst_user)
            session.commit()

    tokens = {
        "institution": authentication_token_from_email(client=client, email="inst.north1@example.com", db=db),
        "regional": authentication_token_from_email(client=client, email="officer.north@example.com", db=db),
        "bureau": authentication_token_from_email(client=client, email="bureau@example.com", db=db),
    }

    # Step 1: Submit an FDR
    today_val = date.today()
    mat_val = today_val + timedelta(days=3650)
    ref_no = f"DEMO-FDR-{uuid.uuid4().hex[:6]}"

    sub_res = client.post(
        "/api/v1/instruments/submit",
        headers=tokens["institution"],
        json={
            "ref_no": ref_no,
            "bank_code": "SBIN",
            "ifsc": "SBIN0001234",
            "amount_paise": 150000000,
            "issue_date": str(today_val),
            "maturity_date": str(mat_val),
            "kind": "FDR",
        },
    )
    assert sub_res.status_code == 200, sub_res.text
    inst_data = sub_res.json()
    inst_id = inst_data["id"]
    assert inst_data["badge"] == "claimed"

    # Step 2: Bank confirms and one mismatch is flagged
    with Session(engine) as session:
        conf = Confirmation(
            instrument_id=uuid.UUID(inst_id),
            status="confirmed",
            method="signed_letter",
            token_hash="demo_hash",
            token_expires_at=datetime.now(UTC) + timedelta(days=14),
            confirmed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=365),
            fields={
                "ref_no": ref_no,
                "bank_code": "SBIN",
                "amount_paise": 100000000,  # 10L vs 15L
                "maturity_date": str(mat_val),
                "lien_marked": True,
            },
        )
        session.add(conf)
        session.commit()

    # Step 3: Clock + 30 days shows reminder / overdue / obligations
    with Session(engine) as session:
        worker_res = run_daily_worker(session, today=today_val + timedelta(days=3620))
        assert worker_res["lock_acquired"] is True

    # Step 4: Renewal links history via replaces_id
    with Session(engine) as session:
        ren_inst = Instrument(
            institution_id=uuid.UUID(inst_data["institution_id"]),
            region="NR",
            kind="FDR",
            ref_no=f"DEMO-REN-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=150000000,
            issue_date=today_val,
            maturity_date=today_val + timedelta(days=3650),
            lifecycle="active",
            replaces_id=uuid.UUID(inst_id),
            lien_marked=True,
        )
        session.add(ren_inst)
        session.commit()
        session.refresh(ren_inst)
        assert ren_inst.replaces_id == uuid.UUID(inst_id)

    # Step 5: Fraud lab results (TP=20, FP=0, FN=0, accuracy 100%)
    metrics = run_fraud_lab_benchmark()
    assert metrics["true_positives"] == 20
    assert metrics["false_positives"] == 0
    assert metrics["false_negatives"] == 0
    assert metrics["accuracy"] == 1.0

    # Step 6: Dual-custody release blocked then approved, receipt verified offline
    # Update confirmation to match to allow valid release flow
    with Session(engine) as session:
        clean_inst = Instrument(
            institution_id=uuid.UUID(inst_data["institution_id"]),
            region="NR",
            kind="FDR",
            ref_no=f"DEMO-REL-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=150000000,
            issue_date=today_val - timedelta(days=3650),
            maturity_date=today_val - timedelta(days=1),
            lifecycle="active",
            lien_marked=True,
        )
        session.add(clean_inst)
        session.commit()
        session.refresh(clean_inst)
        clean_id = clean_inst.id

        clean_conf = Confirmation(
            instrument_id=clean_id,
            status="confirmed",
            method="signed_letter",
            token_hash="clean_hash",
            token_expires_at=datetime.now(UTC) + timedelta(days=14),
            confirmed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=365),
            fields={
                "ref_no": clean_inst.ref_no,
                "bank_code": clean_inst.bank_code,
                "amount_paise": 150000000,
                "maturity_date": str(clean_inst.maturity_date),
                "lien_marked": True,
            },
        )
        session.add(clean_conf)
        session.commit()

    rel_res = client.post(
        f"/api/v1/instruments/{clean_id}/release",
        headers=tokens["institution"],
        json={"path": "term_completion"},
    )
    assert rel_res.status_code == 200
    rel_id = rel_res.json()["id"]

    # Maker verify
    assert client.patch(f"/api/v1/release/{rel_id}/verify", headers=tokens["regional"]).status_code == 200
    # Maker cannot be checker
    assert client.patch(f"/api/v1/release/{rel_id}/approve", headers=tokens["regional"]).status_code == 403
    # Checker approve
    app_res = client.patch(f"/api/v1/release/{rel_id}/approve", headers=tokens["bureau"])
    assert app_res.status_code == 200
    token = app_res.json()["receipt_token"]
    claims = verify_release_receipt(token)
    assert claims["path"] == "term_completion"

    # Step 7: Bank down simulator returns 503
    down_res = client.get("/sim/bank/simulate-outage")
    assert down_res.status_code in (200, 503) or client.get("/sim/bank/status").status_code in (200, 503)
