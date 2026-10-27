import io
import csv
import uuid
from datetime import UTC, date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.domain.csv_safe import csv_safe
from app.domain.next_action import dashboard_bucket, next_action
from app.main import app
from app.models import Confirmation, Institution, Instrument, User
from tests.utils.user import authentication_token_from_email


@pytest.fixture(name="tokens")
def fixture_tokens(client: TestClient, db: Session) -> dict[str, dict[str, str]]:
    return {
        "bureau": authentication_token_from_email(client=client, email="bureau@example.com", db=db),
        "regional_nr": authentication_token_from_email(client=client, email="officer.north@example.com", db=db),
        "institution": authentication_token_from_email(client=client, email="inst.north1@example.com", db=db),
    }


def test_csv_safe_formula_neutralization() -> None:
    # Formula injection attempts
    assert csv_safe("=1+1") == "'=1+1"
    assert csv_safe("+2+2") == "'+2+2"
    assert csv_safe("-3-3") == "'-3-3"
    assert csv_safe("@SUM(A1:A2)") == "'@SUM(A1:A2)"
    assert csv_safe("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"
    # Safe text
    assert csv_safe("Normal Ref") == "Normal Ref"
    assert csv_safe(150000000) == "150000000"


def test_dashboard_bucket_counters_logic() -> None:
    # Pending
    assert dashboard_bucket("pending", days_to_maturity=100, expiring_days=60) == "pending"
    # Active & not expiring
    assert dashboard_bucket("active", days_to_maturity=100, expiring_days=60) == "active"
    # Active & expiring (<= 60 days)
    assert dashboard_bucket("active", days_to_maturity=30, expiring_days=60) == "expiring"
    # Matured
    assert dashboard_bucket("matured", days_to_maturity=-5, expiring_days=60) == "matured"
    # Renewed
    assert dashboard_bucket("renewed", days_to_maturity=0, expiring_days=60) == "renewed"
    # Released
    assert dashboard_bucket("released", days_to_maturity=-10, expiring_days=60) == "released"


def test_dashboard_api_counters_and_search(client: TestClient, tokens: dict[str, dict[str, str]]) -> None:
    with Session(engine) as session:
        # Create an institution in NR
        inst_id = uuid.uuid4()
        inst = Institution(
            id=inst_id,
            permanent_id=f"DASH-INST-{uuid.uuid4().hex[:6]}",
            name="Dashboard Tech College",
            region="NR",
        )
        session.add(inst)

        # Create active expiring instrument
        instrument = Instrument(
            institution_id=inst_id,
            region="NR",
            kind="FDR",
            ref_no=f"DASH-EXP-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=250000000,
            issue_date=date.today() - timedelta(days=3600),
            maturity_date=date.today() + timedelta(days=20),  # expiring in 20 days
            lifecycle="active",
            lien_marked=True,
        )
        session.add(instrument)
        session.commit()
        ref_no = instrument.ref_no

    # 1. Fetch counters as Bureau
    res = client.get("/api/v1/dashboard/counters", headers=tokens["bureau"])
    assert res.status_code == 200, res.text
    counters = res.json()
    for key in ("active", "expiring", "matured", "renewed", "released", "pending"):
        assert key in counters
    assert counters["expiring"] >= 1

    # 2. Search by ref_no
    search_res = client.get(f"/api/v1/dashboard/search?q={ref_no}", headers=tokens["bureau"])
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["count"] >= 1
    assert search_data["results"][0]["ref_no"] == ref_no

    # 3. Fetch impact metrics
    impact_res = client.get("/api/v1/dashboard/impact", headers=tokens["bureau"])
    assert impact_res.status_code == 200, impact_res.text
    impact_data = impact_res.json()
    assert impact_data["status"] == "computed"
    metrics = impact_data["metrics"]
    assert len(metrics) >= 5
    metric_ids = {m["id"] for m in metrics}
    assert "corpus_protected_inr" in metric_ids
    assert "active_lien_paise" in metric_ids
    assert "verified_bank_confirmations" in metric_ids
    assert "participating_banks" in metric_ids
    assert "immutable_audit_events" in metric_ids
    assert len(search_data["results"]) >= 1
    assert search_data["results"][0]["ref_no"] == ref_no

    # 3. Needs action queue returns items with primary_action
    na_res = client.get("/api/v1/dashboard/needs-action", headers=tokens["regional_nr"])
    assert na_res.status_code == 200
    na_items = na_res.json()
    assert isinstance(na_items, list)


def test_csv_reports_generation_and_formula_guard(client: TestClient, tokens: dict[str, dict[str, str]]) -> None:
    # Insert an instrument with a malicious formula ref_no to prove CSV injection is neutralised
    malicious_ref = "=cmd|'/C calc'!A0"
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        assert inst_user
        if not inst_user.institution_id:
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
            session.refresh(inst_user)

        institution_id = inst_user.institution_id
        assert institution_id is not None
        
        bad_inst = Instrument(
            institution_id=institution_id,
            region="NR",
            kind="FDR",
            ref_no=malicious_ref,
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=10000000,
            issue_date=date.today() - timedelta(days=3600),
            maturity_date=date.today() + timedelta(days=15),
            lifecycle="active",
        )
        session.add(bad_inst)
        session.commit()

    # 1. Download upcoming_maturities report
    rep_res = client.get("/api/v1/reports/upcoming-maturities", headers=tokens["bureau"])
    assert rep_res.status_code == 200, rep_res.text
    assert "text/csv" in rep_res.headers.get("content-type", "")

    csv_reader = csv.reader(io.StringIO(rep_res.text))
    rows = list(csv_reader)
    assert len(rows) > 1  # Header + rows
    
    # Verify the formula was neutralised by prefixing with '
    found_bad = False
    for row in rows:
        for cell in row:
            if cell.endswith(malicious_ref):
                assert cell.startswith("'"), f"Cell {cell} was not sanitised with leading quote!"
                found_bad = True
    assert found_bad, "Did not find inserted malicious record in CSV export"
