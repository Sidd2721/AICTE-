from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_sim_clock_endpoint() -> None:
    res = client.get("/sim/clock")
    assert res.status_code == 200
    data = res.json()
    assert "now" in data
    assert "offset_seconds" in data

    # Update clock offset
    res = client.put("/sim/clock", json={"offset_seconds": 86400})
    assert res.status_code == 200
    assert res.json()["offset_seconds"] == 86400

    # Reset clock offset
    res = client.put("/sim/clock", json={"offset_seconds": 0})
    assert res.status_code == 200
    assert res.json()["offset_seconds"] == 0

def test_deposit_calculator_endpoint() -> None:
    # Private, owned land
    res = client.get(
        "/api/v1/deposits/calculator",
        params={
            "programmes": "Engineering and Technology,Management",
            "land_ownership": "owned",
            "institution_type": "private",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["required_deposit_paise"] == 500_000_000
    assert data["multiplier"] == 1
    assert data["exempt"] is False
    assert len(data["breakdown"]) == 2

    # Private, leased land (2x multiplier)
    res = client.get(
        "/api/v1/deposits/calculator",
        params={
            "programmes": "Engineering and Technology,Management",
            "land_ownership": "leased",
            "institution_type": "private",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["required_deposit_paise"] == 1_000_000_000
    assert data["multiplier"] == 2
    assert data["exempt"] is False

    # Government (exempt)
    res = client.get(
        "/api/v1/deposits/calculator",
        params={
            "programmes": "Engineering and Technology,Management",
            "land_ownership": "leased",
            "institution_type": "government",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["required_deposit_paise"] == 0
    assert data["multiplier"] == 0
    assert data["exempt"] is True
