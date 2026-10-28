from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

from app.core.db import engine
from app.core.rls_context import set_rls_context
from app.main import app

client = TestClient(app)


def test_existing_health_endpoints_unchanged():
    """Verify existing health endpoints remain backward-compatible and lightweight."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res_v1 = client.get("/api/v1/utils/health-check/")
    assert res_v1.status_code == 200
    assert res_v1.json() is True


def test_readiness_endpoint_healthy():
    """Verify /ready returns 200 with minimal body when database and vault are ready."""
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ready"}


def test_readiness_endpoint_excluded_from_public_schema():
    """Verify /ready is excluded from the public OpenAPI specification."""
    # When FASTAPI_ENV is development, openapi.json is accessible
    res = client.get("/api/v1/openapi.json")
    if res.status_code == 200:
        schema = res.json()
        assert "/ready" not in schema.get("paths", {})
        assert "/api/ready" not in schema.get("paths", {})


def test_readiness_endpoint_503_on_vault_unwritable(monkeypatch: pytest.MonkeyPatch):
    """Verify /ready returns 503 with minimal body if vault directory is not writable."""
    monkeypatch.setattr("app.domain.vault.check_vault_writable", lambda: False)
    res = client.get("/ready")
    assert res.status_code == 503
    assert res.json() == {"status": "unready"}


def test_readiness_endpoint_503_on_db_disconnect():
    """Verify /ready returns 503 if database query fails."""
    with patch("sqlmodel.Session.execute", side_effect=Exception("Database connection timeout")):
        res = client.get("/ready")
        assert res.status_code == 503
        assert res.json() == {"status": "unready"}


def test_pool_recovery_after_drop_and_rls_integrity():
    """Verify API recovers after pool connection drop and maintains RLS isolation."""
    # 1. Dispose pool connections simulating a network drop / Render proxy idle cutoff
    engine.dispose()

    # 2. Re-connect and verify pool recovers cleanly
    with Session(engine) as session:
        ping = session.execute(text("SELECT 1")).scalar()
        assert ping == 1

        # 3. Verify RLS context applies properly on new connection
        set_rls_context(
            session=session,
            role="regional",
            region="NR",
            institution="",
        )

        role_applied = session.execute(text("SELECT current_setting('app.role', true)")).scalar()
        region_applied = session.execute(text("SELECT current_setting('app.region', true)")).scalar()
        assert role_applied == "regional"
        assert region_applied == "NR"


def test_readiness_returns_503_while_seeding(monkeypatch: pytest.MonkeyPatch):
    """Verify /ready returns 503 while background demo seeding is in progress."""
    from app.core.config import settings
    from app.main import set_seed_completed

    monkeypatch.setattr(settings, "FASTAPI_ENV", "demo")
    monkeypatch.setattr(settings, "AUTO_SEED", True)
    set_seed_completed(False)

    try:
        res = client.get("/ready")
        assert res.status_code == 503
        assert res.json()["status"] == "unready"
        assert res.json()["reason"] == "seeding_in_progress"

        set_seed_completed(True)
        res_after = client.get("/ready")
        assert res_after.status_code == 200
        assert res_after.json() == {"status": "ready"}
    finally:
        set_seed_completed(True)
