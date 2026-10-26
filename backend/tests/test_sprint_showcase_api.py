from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Instrument


def test_reports_preview_endpoints(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    headers = superuser_token_headers
    r1 = client.get(f"{settings.API_V1_STR}/reports/pending-verifications/preview", headers=headers)
    assert r1.status_code == 200
    assert "rows" in r1.json()

    r2 = client.get(f"{settings.API_V1_STR}/reports/upcoming-maturities/preview", headers=headers)
    assert r2.status_code == 200
    assert "rows" in r2.json()

    r3 = client.get(f"{settings.API_V1_STR}/reports/missing-documents/preview", headers=headers)
    assert r3.status_code == 200
    assert "rows" in r3.json()

    r4 = client.get(f"{settings.API_V1_STR}/reports/cases-needing-intervention/preview", headers=headers)
    assert r4.status_code == 200
    assert "rows" in r4.json()


def test_audit_events_endpoint(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    headers = superuser_token_headers
    r = client.get(f"{settings.API_V1_STR}/audit/events", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data


def test_instrument_case_view_endpoint(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    headers = superuser_token_headers
    inst = db.exec(select(Instrument)).first()
    if not inst:
        return
    r = client.get(f"{settings.API_V1_STR}/instruments/{inst.id}/case", headers=headers)
    assert r.status_code == 200
    case_data = r.json()
    assert "instrument" in case_data
    assert "confirmations" in case_data
    assert "discrepancies" in case_data
    assert "documents" in case_data
    assert "audit_timeline" in case_data
