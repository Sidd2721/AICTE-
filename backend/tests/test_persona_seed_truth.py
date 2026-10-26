"""Test Persona Seed Truth (CHARTER Section 2, R4).

Verifies that clean DB + seed only yields exactly the contracted personas,
roles, regions, and tenant institutions from the single seed source (app.core.db.init_db).
Scripts like demo_steps.py must never patch or create personas.
"""

import pytest
from sqlmodel import Session, select

from app.core.db import engine, init_db
from app.models import Institution, User


CONTRACT_PERSONAS = [
    ("officer.north@example.com", "regional", "NR", False),
    ("checker.north@example.com", "regional", "NR", False),
    ("officer.west@example.com", "regional", "WR", False),
    ("checker.west@example.com", "regional", "WR", False),
    ("inst.north1@example.com", "institution", "NR", True),
    ("inst.north2@example.com", "institution", "NR", True),
    ("inst.west@example.com", "institution", "WR", True),
    ("bureau@example.com", "bureau", None, False),
    ("auditor@example.com", "auditor", None, False),
]


def test_persona_seed_truth_contract() -> None:
    with Session(engine) as session:
        # Re-run init_db idempotent check
        init_db(session)

        for email, expected_role, expected_region, expect_institution in CONTRACT_PERSONAS:
            user = session.exec(select(User).where(User.email == email)).first()
            assert user is not None, f"Seeded persona {email} must exist in database"
            assert user.role == expected_role, f"{email} role must be {expected_role}, got {user.role}"
            assert user.region == expected_region, f"{email} region must be {expected_region}, got {user.region}"

            if expect_institution:
                assert user.institution_id is not None, f"{email} must be mapped to an institution"
                inst = session.get(Institution, user.institution_id)
                assert inst is not None, f"Institution for {email} must exist"
                assert inst.region == expected_region, f"Institution region {inst.region} must match user region {expected_region}"
