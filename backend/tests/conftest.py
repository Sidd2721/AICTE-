from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session]:
    with Session(engine) as session:
        from sqlalchemy import text
        # Pre-cleanup of known test users that may survive between test runs
        try:
            session.execute(text("DELETE FROM \"user\" WHERE email NOT IN (SELECT \"user\".email FROM \"user\" JOIN lateral(select 1) ON true WHERE is_superuser = true) OR email = 'pollo@listo.com'"))
            session.commit()
        except Exception:
            session.rollback()
        init_db(session)
        yield session
        try:
            session.execute(text("DELETE FROM flag_waiver; DELETE FROM notice; DELETE FROM obligation; DELETE FROM case_note; DELETE FROM confirmation; DELETE FROM document; DELETE FROM release_request; DELETE FROM instrument;"))
        except Exception:
            session.rollback()
        statement = delete(User)
        session.execute(statement)
        session.commit()



@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
