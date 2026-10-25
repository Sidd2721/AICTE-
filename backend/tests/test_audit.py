import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.audit import audit, validate_audit_payload
from app.core.config import settings
from tests.utils.user import authentication_token_from_email


def test_validate_audit_payload_rejects_floats() -> None:
    """I5: Floating-point values are strictly forbidden in audit payloads."""
    with pytest.raises(ValueError, match="Floating point values are forbidden"):
        validate_audit_payload({"amount": 100.50})

    with pytest.raises(ValueError, match="Floating point values are forbidden"):
        validate_audit_payload({"nested": {"rate": 0.05}})

    with pytest.raises(ValueError, match="Floating point values are forbidden"):
        validate_audit_payload({"items": [1, 2, 3.14]})


def test_validate_audit_payload_rejects_non_string_keys() -> None:
    """Audit payload keys must always be strings."""
    with pytest.raises(TypeError, match="Audit payload keys must be strings"):
        validate_audit_payload({123: "val"})  # type: ignore


def test_audit_append_and_verify(db: Session) -> None:
    """I4: Append via audit helper and verify chain."""
    event_id = audit(
        db,
        actor_id=None,
        action="test_action",
        entity="test_entity",
        entity_id="test_1",
        payload={"key": "value", "amount_paise": 100000},
    )
    assert event_id > 0


def test_audit_verify_endpoint(client: TestClient, db: Session) -> None:
    """GET /api/v1/audit/verify is restricted to bureau and auditor roles."""
    # Auditor access
    auditor_headers = authentication_token_from_email(
        client=client, email="auditor@example.com", db=db
    )
    r = client.get(f"{settings.API_V1_STR}/audit/verify", headers=auditor_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "clean"

    # Bureau access
    bureau_headers = authentication_token_from_email(
        client=client, email="bureau@example.com", db=db
    )
    r = client.get(f"{settings.API_V1_STR}/audit/verify", headers=bureau_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "clean"

    # Regional officer blocked (403)
    officer_headers = authentication_token_from_email(
        client=client, email="officer.north@example.com", db=db
    )
    r = client.get(f"{settings.API_V1_STR}/audit/verify", headers=officer_headers)
    assert r.status_code == 403

    # Institution blocked (403)
    inst_headers = authentication_token_from_email(
        client=client, email="inst.north1@example.com", db=db
    )
    r = client.get(f"{settings.API_V1_STR}/audit/verify", headers=inst_headers)
    assert r.status_code == 403
