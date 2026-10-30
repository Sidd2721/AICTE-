import re
import sys
from collections.abc import Generator

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, create_engine, delete

from app.core.config import settings

# 1. Determine isolated test database URL
if settings.TEST_DATABASE_URL:
    test_db_url_str = str(settings.TEST_DATABASE_URL)
else:
    raw_url = str(settings.DATABASE_URL)
    m = re.search(r"/([^/?]+)(\?|$)", raw_url)
    current_name = m.group(1) if m else "app"
    test_db_name = (
        current_name if current_name.endswith("_test") else f"{current_name}_test"
    )
    test_db_url_str = re.sub(r"/([^/?]+)(\?|$)", f"/{test_db_name}\\2", raw_url)

# Prefer IPv4 loopback on Windows to avoid ::1 resolution delay
test_db_url_str = test_db_url_str.replace("@localhost:", "@127.0.0.1:")

# 2. Guard: Refuse to run test suite against remote database hosts
_db_hosts = [h.get("host") for h in settings.DATABASE_URL.hosts() if h.get("host")]
_allowed_local = {"localhost", "127.0.0.1", "::1", "db", "postgres"}
for _h in _db_hosts:
    if _h not in _allowed_local:
        sys.stderr.write(
            f"\nFATAL: Refusing to run tests against remote database host '{_h}'!\n"
            f"Point DATABASE_URL to a local database.\n"
        )
        sys.exit(3)

# 3. Guard: Destructive fixtures refuse to run unless the DB name ends '_test'
_m_test = re.search(r"/([^/?]+)(?:\?|$)", test_db_url_str)
_test_db_name = _m_test.group(1) if _m_test else ""
if not _test_db_name.endswith("_test"):
    sys.stderr.write(
        f"\nFATAL: Test suite requires database name ending in '_test', got '{_test_db_name}'!\n"
    )
    sys.exit(3)

# 4. Ensure test database exists on the database server
_maint_url = re.sub(r"/([^/?]+)(\?|$)", r"/postgres\2", test_db_url_str).replace(
    "postgresql+psycopg://", "postgresql://"
)
try:
    with psycopg.connect(_maint_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (_test_db_name,)
            )
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{_test_db_name}"')
except Exception:
    pass

# 5. Point application engine to the isolated test database
import app.core.db as app_db

app_db.engine = create_engine(test_db_url_str, pool_pre_ping=True)
engine = app_db.engine

from app.core.db import init_db
from app.main import app
from app.models import User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session]:
    from app.core.rls_context import install_rls_context, set_rls_context

    install_rls_context()
    with Session(engine) as session:
        set_rls_context(session, role="bureau")
        # Pre-cleanup of known test users that may survive between test runs
        try:
            session.execute(
                text(
                    "DELETE FROM \"user\" WHERE email IN ('a@x', 'b@x', 'r@x') OR email NOT IN (SELECT \"user\".email FROM \"user\" JOIN lateral(select 1) ON true WHERE is_superuser = true) OR email = 'pollo@listo.com'"
                )
            )
            session.execute(
                text("DELETE FROM rate_limit_bucket; SELECT pg_advisory_unlock_all();")
            )
            session.commit()
        except Exception:
            session.rollback()
        init_db(session)
        yield session
        # Teardown: clean up test database rows without touching or re-seeding live DB
        try:
            session.execute(
                text(
                    "DELETE FROM flag_waiver; DELETE FROM notice; DELETE FROM obligation; DELETE FROM case_note; DELETE FROM confirmation; DELETE FROM document; DELETE FROM release_request; DELETE FROM instrument; DELETE FROM rate_limit_bucket; SELECT pg_advisory_unlock_all();"
                )
            )
        except Exception:
            session.rollback()
        statement = delete(User)
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    with Session(engine) as session:
        try:
            session.execute(
                text("DELETE FROM rate_limit_bucket; SELECT pg_advisory_unlock_all();")
            )
            session.commit()
        except Exception:
            session.rollback()
    yield
    with Session(engine) as session:
        try:
            session.execute(
                text("DELETE FROM rate_limit_bucket; SELECT pg_advisory_unlock_all();")
            )
            session.commit()
        except Exception:
            session.rollback()


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    from sqlmodel import select

    from app.core.rls_context import set_rls_context
    from app.core.security import get_password_hash, verify_password

    with Session(engine) as session:
        set_rls_context(session, role="bureau")
        user = session.exec(
            select(User).where(User.email == settings.FIRST_SUPERUSER)
        ).first()
        if not user:
            init_db(session)
        else:
            v, _ = verify_password(
                settings.FIRST_SUPERUSER_PASSWORD, user.hashed_password
            )
            if (
                not v
                or user.role != "bureau"
                or not user.is_superuser
                or not user.is_active
            ):
                user.hashed_password = get_password_hash(
                    settings.FIRST_SUPERUSER_PASSWORD
                )
                user.role = "bureau"
                user.is_superuser = True
                user.is_active = True
                session.add(user)
                session.commit()
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
