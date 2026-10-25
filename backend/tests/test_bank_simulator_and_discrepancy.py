from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.db import engine
from app.domain.bank_gate import check_bank_reply
from app.domain.discrepancy import evaluate_discrepancies
from app.main import app
from app.models import Confirmation, Instrument

client = TestClient(app)


def test_discrepancy_engine_rules() -> None:
    # Match - no discrepancies
    inst = {
        "ref_no": "FDR-100",
        "bank_code": "SBI",
        "amount_paise": 10000000,
        "maturity_date": date(2034, 1, 1),
        "lien_marked": True,
    }
    conf = {
        "ref_no": "FDR-100",
        "bank_code": "SBI",
        "amount_paise": 10000000,
        "maturity_date": date(2034, 1, 1),
        "lien_marked": True,
    }
    flags = evaluate_discrepancies(inst, conf)
    assert len(flags) == 0

    # D1: Amount discrepancy
    conf_bad_amount = {**conf, "amount_paise": 9000000}
    flags = evaluate_discrepancies(inst, conf_bad_amount)
    assert "D1_AMOUNT_MISMATCH" in [f["code"] for f in flags]

    # D2: Maturity discrepancy
    conf_bad_mat = {**conf, "maturity_date": date(2030, 1, 1)}
    flags = evaluate_discrepancies(inst, conf_bad_mat)
    assert "D2_MATURITY_MISMATCH" in [f["code"] for f in flags]

    # D5: Lien not marked
    inst_no_lien = {**inst, "lien_marked": False}
    flags = evaluate_discrepancies(inst_no_lien, conf)
    assert "D5_LIEN_NOT_MARKED" in [f["code"] for f in flags]


def test_bank_simulator_confirmation_flow(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    # 1. Submit instrument
    today_val = date.today()
    maturity_val = today_val + timedelta(days=3650)
    sub = client.post(
        "/api/v1/instruments/submit",
        headers=superuser_token_headers,
        json={
            "ref_no": "FDR-SIM-001",
            "bank_code": "SBI",
            "ifsc": "SBIN0001234",
            "amount_paise": 15000000,
            "issue_date": today_val.isoformat(),
            "maturity_date": maturity_val.isoformat(),
            "lien_marked": True,
        },
    )
    assert sub.status_code == 200
    inst_id = sub.json()["id"]

    # 2. Request confirmation from bank simulator
    req = client.post(
        f"/api/v1/bank/request-confirmation/{inst_id}",
        headers=superuser_token_headers,
    )
    assert req.status_code == 200
    conf_data = req.json()
    assert conf_data["status"] == "requested"

    # 3. Simulate bank reply with match
    sim = client.post(
        f"/sim/bank/confirm/{inst_id}",
        headers=superuser_token_headers,
        json={"outcome": "match"},
    )
    assert sim.status_code == 200
    result = sim.json()
    assert result["status"] == "confirmed"
    assert result["discrepancies"] == []

    # Verify instrument badge is now "confirmed"
    inst_res = client.get(
        f"/api/v1/instruments/{inst_id}",
        headers=superuser_token_headers,
    )
    assert inst_res.status_code == 200
    assert inst_res.json()["badge"] == "confirmed"
