from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.db import engine
from app.domain.clock import now
from app.domain.worker import run_daily_obligations_job
from app.main import app
from app.models import Instrument, Notice, Obligation

client = TestClient(app)


def test_daily_worker_advisory_lock_and_obligation_generation(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    # 1. Submit an instrument expiring in 30 days
    today_val = date.today()
    expiring_soon = today_val + timedelta(days=30)
    sub = client.post(
        "/api/v1/instruments/submit",
        headers=superuser_token_headers,
        json={
            "ref_no": "FDR-OBLIG-001",
            "bank_code": "SBI",
            "ifsc": "SBIN0001234",
            "amount_paise": 20000000,
            "issue_date": (today_val - timedelta(days=3620)).isoformat(),
            "maturity_date": expiring_soon.isoformat(),
            "kind": "FDR",
        },
    )
    assert sub.status_code == 200
    inst_id = sub.json()["id"]

    # 2. Trigger worker
    res = client.post(
        "/sim/worker/run-daily",
        headers=superuser_token_headers,
    )
    assert res.status_code == 200
    worker_data = res.json()
    assert worker_data["lock_acquired"] is True
    assert "obligations_processed" in worker_data

    # 3. Verify obligation was generated
    with Session(engine) as session:
        ob = session.exec(
            select(Obligation).where(
                Obligation.instrument_id == inst_id,
                Obligation.kind == "renewal_due",
            )
        ).first()
        assert ob is not None
        assert ob.status == "open"
