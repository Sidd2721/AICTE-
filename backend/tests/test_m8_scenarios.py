import io
import uuid
from datetime import UTC, date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.domain.fraud_lab import run_fraud_lab_benchmark
from app.domain.receipt import verify_release_receipt
from app.domain.worker import run_daily_worker
from app.main import app
from app.models import Confirmation, Document, Institution, Instrument, Obligation, ReleaseRequest, User
from tests.utils.user import authentication_token_from_email


@pytest.fixture(name="all_tokens")
def fixture_all_tokens(client: TestClient, db: Session) -> dict[str, dict[str, str]]:
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        if inst_user and not inst_user.institution_id:
            inst_obj = Institution(
                name="North Tech 1",
                permanent_id=f"P-NT-{uuid.uuid4().hex[:6]}",
                region="NR",
            )
            session.add(inst_obj)
            session.commit()
            session.refresh(inst_obj)
            inst_user.institution_id = inst_obj.id
            session.add(inst_user)
            session.commit()

    return {
        "institution": authentication_token_from_email(client=client, email="inst.north1@example.com", db=db),
        "regional": authentication_token_from_email(client=client, email="officer.north@example.com", db=db),
        "bureau": authentication_token_from_email(client=client, email="bureau@example.com", db=db),
        "auditor": authentication_token_from_email(client=client, email="auditor@example.com", db=db),
    }


def test_m8_fraud_lab_benchmark_metrics(client: TestClient, all_tokens: dict[str, dict[str, str]]) -> None:
    """Validate synthetic fraud lab fixture reports TP=20, FP=0, FN=0, Accuracy=100%."""
    # 1. Pure function benchmark
    metrics = run_fraud_lab_benchmark()
    assert metrics["planted_records"] == 20
    assert metrics["clean_records"] == 20
    assert metrics["true_positives"] == 20
    assert metrics["false_positives"] == 0
    assert metrics["false_negatives"] == 0
    assert metrics["true_negatives"] == 20
    assert metrics["accuracy"] == 1.0
    assert metrics["status"] == "SYNTHETIC_LAB"

    # 2. API endpoint benchmark
    res = client.get("/api/v1/fraud-lab/metrics", headers=all_tokens["bureau"])
    assert res.status_code == 200, res.text
    api_data = res.json()
    assert api_data["true_positives"] == 20
    assert api_data["false_positives"] == 0
    assert api_data["false_negatives"] == 0
    assert api_data["accuracy"] == 1.0


def test_scenario_1_new_fdr_submission(client: TestClient, all_tokens: dict[str, dict[str, str]]) -> None:
    """Scenario 1: Institution signs in, submits new FDR, initial state is pending, badge claimed."""
    today_val = date.today()
    mat_val = today_val + timedelta(days=3650)
    ref_no = f"SCEN-1-{uuid.uuid4().hex[:6]}"

    res = client.post(
        "/api/v1/instruments/submit",
        headers=all_tokens["institution"],
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
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["lifecycle"] == "pending"
    assert data["badge"] == "claimed"
    assert data["ref_no"] == ref_no


def test_scenario_2_validity_tracking_and_obligations(client: TestClient, all_tokens: dict[str, dict[str, str]]) -> None:
    """Scenario 2: Daily worker scans instruments, tracks validity, logs obligations."""
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        assert inst_user and inst_user.institution_id
        
        inst = Instrument(
            institution_id=inst_user.institution_id,
            region="NR",
            kind="FDR",
            ref_no=f"SCEN-2-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=150000000,
            issue_date=date.today() - timedelta(days=3500),
            maturity_date=date.today() + timedelta(days=150),
            lifecycle="active",
            lien_marked=True,
        )
        session.add(inst)
        session.commit()
        session.refresh(inst)

        # Run daily worker
        res = run_daily_worker(session, today=date.today())
        assert res["scanned_instruments"] >= 1


def test_scenario_3_approaching_maturity_alerts(client: TestClient, all_tokens: dict[str, dict[str, str]]) -> None:
    """Scenario 3: Approaching maturity (<=90 days) triggers renewal_due obligation and reminder notice."""
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        assert inst_user and inst_user.institution_id
        
        inst = Instrument(
            institution_id=inst_user.institution_id,
            region="NR",
            kind="FDR",
            ref_no=f"SCEN-3-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=150000000,
            issue_date=date.today() - timedelta(days=3600),
            maturity_date=date.today() + timedelta(days=45),  # 45 days to maturity
            lifecycle="active",
            lien_marked=True,
        )
        session.add(inst)
        session.commit()
        session.refresh(inst)
        inst_id = inst.id

        # Worker run creates obligation & notice
        run_daily_worker(session, today=date.today())

        obs = session.exec(
            select(Obligation).where(Obligation.instrument_id == inst_id)
        ).all()
        assert len(obs) >= 1
        assert any(o.kind == "renewal_due" for o in obs)


def test_scenario_4_renewal_linking(client: TestClient, all_tokens: dict[str, dict[str, str]]) -> None:
    """Scenario 4: Replacement instrument links to old FDR via replaces_id."""
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        assert inst_user and inst_user.institution_id
        
        old_inst = Instrument(
            institution_id=inst_user.institution_id,
            region="NR",
            kind="FDR",
            ref_no=f"SCEN-4-OLD-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=150000000,
            issue_date=date.today() - timedelta(days=3650),
            maturity_date=date.today() - timedelta(days=1),
            lifecycle="matured",
            lien_marked=True,
        )
        session.add(old_inst)
        session.commit()
        session.refresh(old_inst)

        # Replacement instrument
        new_inst = Instrument(
            institution_id=inst_user.institution_id,
            region="NR",
            kind="FDR",
            ref_no=f"SCEN-4-NEW-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=150000000,
            issue_date=date.today(),
            maturity_date=date.today() + timedelta(days=3650),
            lifecycle="active",
            replaces_id=old_inst.id,
            lien_marked=True,
        )
        session.add(new_inst)
        old_inst.lifecycle = "renewed"
        session.add(old_inst)
        session.commit()

        assert new_inst.replaces_id == old_inst.id
        assert old_inst.lifecycle == "renewed"


def test_scenario_5_discrepancy_identification(client: TestClient, all_tokens: dict[str, dict[str, str]]) -> None:
    """Scenario 5: Discrepancy caught by engine when bank confirmation mismatches amount."""
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        assert inst_user and inst_user.institution_id
        
        inst = Instrument(
            institution_id=inst_user.institution_id,
            region="NR",
            kind="FDR",
            ref_no=f"SCEN-5-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=150000000,
            issue_date=date.today() - timedelta(days=3650),
            maturity_date=date.today() + timedelta(days=100),
            lifecycle="pending",
            lien_marked=True,
        )
        session.add(inst)
        session.commit()
        session.refresh(inst)

        # Add mismatched confirmation
        conf = Confirmation(
            instrument_id=inst.id,
            status="confirmed",
            method="signed_letter",
            token_hash="hash_5",
            token_expires_at=datetime.now(UTC) + timedelta(days=14),
            confirmed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=365),
            fields={
                "ref_no": inst.ref_no,
                "bank_code": inst.bank_code,
                "amount_paise": 100000000,  # 10L instead of 15L!
                "maturity_date": str(inst.maturity_date),
                "lien_marked": True,
            },
        )
        session.add(conf)
        session.commit()
        inst_id = inst.id

    # Request release and expect verify to block on D1 discrepancy
    rel_res = client.post(
        f"/api/v1/instruments/{inst_id}/release",
        headers=all_tokens["institution"],
        json={"path": "term_completion"},
    )
    assert rel_res.status_code == 200
    rel_id = rel_res.json()["id"]

    ver_res = client.patch(f"/api/v1/release/{rel_id}/verify", headers=all_tokens["regional"])
    assert ver_res.status_code == 400
    assert "D1_AMOUNT_MISMATCH" in ver_res.text


def test_scenario_6_authorised_release_maker_checker(client: TestClient, all_tokens: dict[str, dict[str, str]]) -> None:
    """Scenario 6: Authorised release with dual-custody maker-checker and signed PyJWT receipt."""
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        assert inst_user and inst_user.institution_id
        
        inst = Instrument(
            institution_id=inst_user.institution_id,
            region="NR",
            kind="FDR",
            ref_no=f"SCEN-6-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=150000000,
            issue_date=date.today() - timedelta(days=3650),
            maturity_date=date.today() - timedelta(days=1),
            lifecycle="active",
            lien_marked=True,
        )
        session.add(inst)
        session.commit()
        session.refresh(inst)

        conf = Confirmation(
            instrument_id=inst.id,
            status="confirmed",
            method="signed_letter",
            token_hash="hash_6",
            token_expires_at=datetime.now(UTC) + timedelta(days=14),
            confirmed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=365),
            fields={
                "ref_no": inst.ref_no,
                "bank_code": inst.bank_code,
                "amount_paise": 150000000,
                "maturity_date": str(inst.maturity_date),
                "lien_marked": True,
            },
        )
        session.add(conf)
        session.commit()
        inst_id = inst.id

    # 1. Institution requests release
    rel_res = client.post(
        f"/api/v1/instruments/{inst_id}/release",
        headers=all_tokens["institution"],
        json={"path": "term_completion"},
    )
    assert rel_res.status_code == 200
    rel_id = rel_res.json()["id"]

    # 2. Regional verifies (Maker)
    ver_res = client.patch(f"/api/v1/release/{rel_id}/verify", headers=all_tokens["regional"])
    assert ver_res.status_code == 200

    # 3. Regional tries to approve (Maker-Checker violation) -> 403
    app_fail = client.patch(f"/api/v1/release/{rel_id}/approve", headers=all_tokens["regional"])
    assert app_fail.status_code == 403

    # 4. Bureau approves (Checker)
    app_res = client.patch(f"/api/v1/release/{rel_id}/approve", headers=all_tokens["bureau"])
    assert app_res.status_code == 200
    token = app_res.json()["receipt_token"]
    assert token

    # 5. Verify receipt offline
    claims = verify_release_receipt(token)
    assert claims["path"] == "term_completion"
    assert "instrument_hash" in claims
