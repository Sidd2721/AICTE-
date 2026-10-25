from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import User, UserCreate

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
            full_name="System Administrator",
        )
        user = crud.create_user(session=session, user_create=user_in)

    # In production mode, never seed demo/test accounts
    if settings.FASTAPI_ENV == "production":
        return

    # Seed users across 2 regions for dual-custody (maker!=checker) and isolation demos
    demo_users = [
        (
            "officer.north@example.com",
            "North Regional Officer (Maker)",
            False,
            "regional",
            "NR",
        ),
        (
            "checker.north@example.com",
            "North Regional Checker",
            False,
            "regional",
            "NR",
        ),
        (
            "officer.west@example.com",
            "West Regional Officer (Maker)",
            False,
            "regional",
            "WR",
        ),
        ("checker.west@example.com", "West Regional Checker", False, "regional", "WR"),
        (
            "inst.north1@example.com",
            "North Tech Institution 1",
            False,
            "institution",
            "NR",
        ),
        (
            "inst.north2@example.com",
            "North Tech Institution 2",
            False,
            "institution",
            "NR",
        ),
        ("inst.west@example.com", "West Polytechnic", False, "institution", "WR"),
        ("bureau@example.com", "Bureau Head (Approver)", False, "bureau", None),
        ("auditor@example.com", "Regulatory Auditor", False, "auditor", None),
    ]

    demo_password = settings.FIRST_SUPERUSER_PASSWORD
    for email, full_name, is_super, role, region in demo_users:
        existing = session.exec(select(User).where(User.email == email)).first()
        if not existing:
            u_in = UserCreate(
                email=email,
                password=demo_password,
                is_superuser=is_super,
                full_name=full_name,
                role=role,
                region=region,
            )
            existing = crud.create_user(session=session, user_create=u_in)
        else:
            existing.role = role
            existing.region = region
            session.add(existing)
            session.commit()

        if role == "institution" and not existing.institution_id:
            from app.models import Institution

            inst_obj = Institution(
                name=full_name,
                permanent_id=f"P-{email.split('@')[0].upper()}",
                region=region or "NR",
            )
            session.add(inst_obj)
            session.commit()
            session.refresh(inst_obj)
            existing.institution_id = inst_obj.id
            session.add(existing)
            session.commit()
