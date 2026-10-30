from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User


def test_create_user(client: TestClient, db: Session) -> None:
    existing = db.exec(select(User).where(User.email == "pollo@listo.com")).all()
    for u in existing:
        db.delete(u)
    db.commit()

    try:
        r = client.post(
            f"{settings.API_V1_STR}/private/users/",
            json={
                "email": "pollo@listo.com",
                "password": "password123",
                "full_name": "Pollo Listo",
            },
        )

        assert r.status_code == 200

        data = r.json()

        user = db.exec(select(User).where(User.id == data["id"])).first()

        assert user
        assert user.email == "pollo@listo.com"
        assert user.full_name == "Pollo Listo"
    finally:
        existing = db.exec(select(User).where(User.email == "pollo@listo.com")).all()
        for u in existing:
            db.delete(u)
        db.commit()
