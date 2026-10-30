import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain.receipt import (
    get_key_id,
    get_receipt_keys,
    sign_release_receipt,
    validate_receipt_key_security,
    verify_release_receipt,
)
from app.api.routes.receipts import reset_rate_limit_buckets
from app.main import app


@pytest.fixture(autouse=True)
def clean_rate_limits():
    reset_rate_limit_buckets()
    yield
    reset_rate_limit_buckets()


def test_key_stability_and_reload(monkeypatch: pytest.MonkeyPatch):
    """Test that key loader reloaded from the same source returns identical keys and kid."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_str = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    monkeypatch.setattr(settings, "RECEIPT_PRIVATE_KEY_PEM", pem_str)
    priv1, pub1, kid1 = get_receipt_keys(reload=True)

    # Issue a token
    token = sign_release_receipt(
        instrument_id="inst-test-01",
        instrument_ref_no="FDR-STABLE-01",
        path="term_completion",
    )
    assert token

    # Reload from the same source
    priv2, pub2, kid2 = get_receipt_keys(reload=True)
    assert priv1 == priv2
    assert pub1 == pub2
    assert kid1 == kid2

    # Verify that the token issued prior to reload is still valid
    claims = verify_release_receipt(token)
    assert claims["path"] == "term_completion"
    assert claims["kid"] == kid1


def test_production_startup_fails_without_explicit_key(monkeypatch: pytest.MonkeyPatch):
    """Production mode must refuse startup if RECEIPT_PRIVATE_KEY_PEM is missing."""
    monkeypatch.setattr(settings, "RECEIPT_PRIVATE_KEY_PEM", None)
    with pytest.raises(RuntimeError, match="RECEIPT_PRIVATE_KEY_PEM"):
        validate_receipt_key_security(env="production")

    # With explicit key, validation passes
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_str = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    monkeypatch.setattr(settings, "RECEIPT_PRIVATE_KEY_PEM", pem_str)
    validate_receipt_key_security(env="production")


def test_public_key_endpoint_and_schema_exclusion(client: TestClient):
    """GET /api/v1/receipts/public-key is public, returns kid & public key, outside OpenAPI."""
    res = client.get("/api/v1/receipts/public-key")
    assert res.status_code == 200
    data = res.json()
    assert "kid" in data
    assert data["algorithm"] == "RS256"
    assert "BEGIN PUBLIC KEY" in data["public_key"]

    # Text format
    res_txt = client.get("/api/v1/receipts/public-key", headers={"Accept": "text/plain"})
    assert res_txt.status_code == 200
    assert "BEGIN PUBLIC KEY" in res_txt.text

    # Route must NOT appear in OpenAPI schema
    schema_res = client.get("/api/v1/openapi.json")
    if schema_res.status_code == 200:
        paths = schema_res.json().get("paths", {})
        assert "/api/v1/receipts/public-key" not in paths
        assert "/api/v1/receipts/verify" not in paths


def test_verify_receipt_api_flow(client: TestClient):
    """POST /api/v1/receipts/verify validates tokens and rejects tampered tokens."""
    token = sign_release_receipt(
        instrument_id="inst-vr-01",
        instrument_ref_no="FDR-VR-001",
        path="term_completion",
    )

    # 1. Valid token
    res = client.post("/api/v1/receipts/verify", json={"token": token})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["reason"] is None
    assert data["claims"]["path"] == "term_completion"
    assert data["kid"] is not None
    assert data["issued_at"] is not None

    # 2. One flipped character in signature gives bad signature
    parts = token.split(".")
    tampered_sig = parts[2][:10] + ("A" if parts[2][10] != "A" else "B") + parts[2][11:]
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    res_tampered = client.post("/api/v1/receipts/verify", json={"token": tampered_token})
    assert res_tampered.status_code == 200
    data_tampered = res_tampered.json()
    assert data_tampered["valid"] is False
    assert "bad signature" in data_tampered["reason"].lower()

    # 3. Corrupted malformed token gives malformed
    corrupted_token = token + "xyz"
    res_corrupted = client.post("/api/v1/receipts/verify", json={"token": corrupted_token})
    assert res_corrupted.status_code == 200
    assert res_corrupted.json()["valid"] is False


def test_verify_receipt_rejects_none_and_hs256(client: TestClient):
    """Algorithm confusion attacks (none, HS256) must be strictly rejected."""
    _, pub_pem, kid = get_receipt_keys()

    payload = {
        "receipt_id": str(uuid.uuid4()),
        "iat": int(datetime.now(UTC).timestamp()),
        "instrument_hash": "dummyhash",
        "path": "term_completion",
        "kid": kid,
    }
    # 1. Alg = 'none' attack
    none_token = jwt.encode(payload, key="", algorithm="none")
    res_none = client.post("/api/v1/receipts/verify", json={"token": none_token})
    assert res_none.status_code == 200
    assert res_none.json()["valid"] is False
    assert "rejected algorithm" in res_none.json()["reason"] or "pinned to RS256" in res_none.json()["reason"]

    # 2. Alg = 'HS256' attack with symmetric key
    hs256_token = jwt.encode(payload, key="attack-symmetric-secret", algorithm="HS256", headers={"kid": kid})
    res_hs = client.post("/api/v1/receipts/verify", json={"token": hs256_token})
    assert res_hs.status_code == 200
    assert res_hs.json()["valid"] is False
    assert "rejected algorithm" in res_hs.json()["reason"] or "pinned to RS256" in res_hs.json()["reason"]


def test_verify_receipt_wrong_kid_rejected(client: TestClient):
    """Token signed with mismatched or unknown kid in header must be rejected."""
    priv_pem, _, _ = get_receipt_keys()
    payload = {
        "receipt_id": str(uuid.uuid4()),
        "iat": int(datetime.now(UTC).timestamp()),
        "instrument_hash": "dummyhash",
        "path": "term_completion",
    }
    wrong_token = jwt.encode(payload, priv_pem, algorithm="RS256", headers={"kid": "unknown_kid_1234"})
    res = client.post("/api/v1/receipts/verify", json={"token": wrong_token})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert "unknown key" in data["reason"].lower()


def test_verify_receipt_oversized_body_413(client: TestClient):
    """POST /api/v1/receipts/verify with > 4KB body returns 413 Payload Too Large."""
    oversized = "A" * 4500
    res = client.post(
        "/api/v1/receipts/verify",
        content=f'{{"token": "{oversized}"}}',
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 413


def test_verify_receipt_rate_limiting(client: TestClient):
    """Verify endpoint rate limits excess requests (at least 60/min)."""
    token = sign_release_receipt(
        instrument_id="inst-rl",
        instrument_ref_no="FDR-RL-01",
        path="term_completion",
    )
    # Perform 120 rapid requests (the allowed threshold)
    for _ in range(120):
        r = client.post("/api/v1/receipts/verify", json={"token": token})
        assert r.status_code == 200

    # 121st request triggers 429
    r_exceeded = client.post("/api/v1/receipts/verify", json={"token": token})
    assert r_exceeded.status_code == 429
