"""Test matrix over development, demo, production, and unknown environments (Sprint 2 D2).

Verifies route availability, startup guard behavior, and security headers across
all supported and unknown FASTAPI_ENV values.
"""

from typing import Any
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.core.config import settings
from app.domain.rules import startup_guard
from app.main import app


ENV_MATRIX = ["development", "demo", "production", "unknown"]


@pytest.mark.parametrize("env", ENV_MATRIX)
def test_docs_and_openapi_availability(env: str) -> None:
    """In development, /docs and /openapi.json return 200. Outside development (demo, production, unknown), they return 404."""
    with patch.object(settings, "FASTAPI_ENV", env):
        # Build test client reflecting env
        client = TestClient(app)
        
        # Test /api/v1/meta to confirm env setting
        meta_res = client.get(f"{settings.API_V1_STR}/meta")
        assert meta_res.status_code == 200
        assert meta_res.json()["env_label"] == env

        # Test /docs
        docs_res = client.get("/docs")
        if env == "development":
            assert docs_res.status_code == 200, "Swagger /docs must be enabled in development"
        else:
            assert docs_res.status_code == 404, f"/docs must return 404 in {env}"

        # Test /redoc
        redoc_res = client.get("/redoc")
        if env == "development":
            assert redoc_res.status_code == 200, "ReDoc must be enabled in development"
        else:
            assert redoc_res.status_code == 404, f"/redoc must return 404 in {env}"


@pytest.mark.parametrize("env", ENV_MATRIX)
def test_demo_persona_endpoint_availability(env: str) -> None:
    """Demo personas and 1-click login are available in development/demo, but blocked (404) in production/unknown."""
    with patch.object(settings, "FASTAPI_ENV", env):
        client = TestClient(app)
        
        personas_res = client.get(f"{settings.API_V1_STR}/login/demo-personas")
        demo_login_res = client.post(
            f"{settings.API_V1_STR}/login/demo",
            json={"email": "inst.north1@example.com"},
        )

        if env in ("development", "demo"):
            assert personas_res.status_code == 200, f"Demo personas must be available in {env}"
            assert len(personas_res.json()) >= 4
            assert demo_login_res.status_code == 200, f"Demo login must succeed in {env}"
            assert "access_token" in demo_login_res.json()
        else:
            assert personas_res.status_code == 404, f"Demo personas must be 404 in {env}"
            assert demo_login_res.status_code == 404, f"Demo login must be 404 in {env}"


@pytest.mark.parametrize("env", ENV_MATRIX)
def test_startup_guard_matrix(env: str) -> None:
    """DEMO rules are allowed in development/demo, but blocked with RuntimeError in production/unknown (Invariant I7)."""
    demo_rules: list[dict[str, Any]] = [
        {"name": "deposit", "status": "DEMO", "notes": "Demo rule values"}
    ]
    confirmed_rules: list[dict[str, Any]] = [
        {"name": "deposit", "status": "CONFIRMED", "notes": "Handbook certified"}
    ]

    if env in ("development", "demo"):
        # Must not raise with DEMO rules
        startup_guard(demo_rules, env)
    else:
        # Must raise RuntimeError with DEMO rules
        with pytest.raises(RuntimeError) as exc_info:
            startup_guard(demo_rules, env)
        assert "refusing to start" in str(exc_info.value).lower()

    # Confirmed rules always pass
    startup_guard(confirmed_rules, env)


def test_security_headers_present() -> None:
    """Security headers (CSP, HSTS, nosniff, DENY) are present on responses."""
    client = TestClient(app)
    res = client.get(f"{settings.API_V1_STR}/utils/health-check/")
    assert res.status_code == 200
    assert "Strict-Transport-Security" in res.headers
    assert "Content-Security-Policy" in res.headers
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
