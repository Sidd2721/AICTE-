import subprocess
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, text

from app.core.config import Settings, settings


def test_signup_returns_404_or_405(client: TestClient) -> None:
    """I11 & M0: There is no public sign-up route."""
    response = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json={"email": "newuser@example.com", "password": "password123"},
    )
    assert response.status_code in (404, 405)


def test_token_expires_in_60_minutes() -> None:
    """I11 & M0: Access tokens last 60 minutes."""
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60


def test_env_is_not_tracked() -> None:
    """I9 & M0: .env must not be tracked in git."""
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".env"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, ".env is tracked by git!"


def test_secret_key_validation_outside_development() -> None:
    """M0: SECRET_KEY must be 32+ bytes outside development."""
    with pytest.raises(ValueError, match="SECRET_KEY must be at least 32 bytes"):
        Settings(
            FASTAPI_ENV=None,
            SECRET_KEY="short",
            PROJECT_NAME="Test",
            FIRST_SUPERUSER="admin@example.com",
            FIRST_SUPERUSER_PASSWORD="strongpassword123",
            DATABASE_URL="postgresql://postgres:changethis@localhost:5432/app",
        )


def test_vault_key_validation_outside_development() -> None:
    """G8 & M0: VAULT_KEY must be set to a valid key outside development."""
    with pytest.raises(ValueError, match="VAULT_KEY must be set"):
        Settings(
            FASTAPI_ENV=None,
            SECRET_KEY="a" * 32,
            VAULT_KEY="",
            PROJECT_NAME="Test",
            FIRST_SUPERUSER="admin@example.com",
            FIRST_SUPERUSER_PASSWORD="strongpassword123",
            DATABASE_URL="postgresql://postgres:changethis@localhost:5432/app",
        )


def test_app_role_is_not_superuser(db: Session) -> None:
    """I4 & M0: app role must exist and have rolsuper=false and rolbypassrls=false."""
    row = db.exec(
        text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'app'")
    ).first()
    assert row is not None, "Role 'app' does not exist in database"
    assert row[0] is False, "Role 'app' must NOT be superuser"
    assert row[1] is False, "Role 'app' must NOT bypass RLS"
