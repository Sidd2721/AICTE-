from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import User, UserCreate, UserUpdate
from tests.utils.utils import random_email, random_lower_string


def user_authentication_headers(
    *, client: TestClient, email: str, password: str
) -> dict[str, str]:
    data = {"username": email, "password": password}

    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=data)
    response = r.json()
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {response}"
    auth_token = response["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}
    return headers


def create_random_user(db: Session) -> User:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)
    return user


def authentication_token_from_email(
    *, client: TestClient, email: str, db: Session
) -> dict[str, str]:
    """
    Return a valid token for the user with given email.

    If the user doesn't exist it is created first.
    """
    password = random_lower_string()
    role_map = {
        "bureau@example.com": ("bureau", None),
        "auditor@example.com": ("auditor", None),
        "officer.north@example.com": ("regional", "NR"),
        "checker.north@example.com": ("regional", "NR"),
        "officer.west@example.com": ("regional", "WR"),
        "checker.west@example.com": ("regional", "WR"),
        "inst.north1@example.com": ("institution", "NR"),
        "inst.north2@example.com": ("institution", "NR"),
        "inst.west@example.com": ("institution", "WR"),
    }
    user = crud.get_user_by_email(session=db, email=email)
    expected_role, expected_region = role_map.get(email, ("institution", None))
    if not user:
        user_in_create = UserCreate(
            email=email,
            password=password,
            role=expected_role,
            region=expected_region,
            is_active=True,
        )
        user = crud.create_user(session=db, user_create=user_in_create)
    else:
        user_in_update = UserUpdate(
            password=password,
            is_active=True,
            role=expected_role,
            region=expected_region,
        )
        if not user.id:
            raise Exception("User id not set")
        user = crud.update_user(session=db, db_user=user, user_in=user_in_update)

    return user_authentication_headers(client=client, email=email, password=password)
