"""Role x Action Matrix Test (Criterion C3, Phase 1.2).

Pins exact status codes and error messages for every persona across the 3 release actions:
1. request_release (POST /api/v1/instruments/{id}/release)
2. verify_release  (POST /api/v1/release/{id}/verify)
3. approve_release (POST /api/v1/release/{id}/approve)

Persona contract (G7 / BRIEF):
- institution (inst.north1@example.com): request -> 200, verify -> 403, approve -> 403
- regional officer (officer.north@example.com): request -> 403, verify -> 200, approve -> 403
- regional checker (checker.north@example.com): role is regional -> request -> 403, verify -> 200, approve -> 403
- bureau head (bureau@example.com): request -> 403, verify -> 403, approve -> 200 (when verified by regional)
- bureau head as maker: approve -> 403 ("Maker cannot be checker")
- auditor (auditor@example.com): request -> 403, verify -> 403, approve -> 403
"""

import uuid
from datetime import UTC, date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine, init_db
from app.core.security import create_access_token
from app.main import app
from app.models import Confirmation, Institution, Instrument, ReleaseRequest, User


@pytest.fixture(name="matrix_setup")
def fixture_matrix_setup() -> dict[str, str]:
    with Session(engine) as session:
        init_db(session)
        users = {
            u.email: u
            for u in session.exec(select(User)).all()
        }
        tokens = {
            email: f"Bearer {create_access_token(user.id, timedelta(minutes=60))}"
            for email, user in users.items()
        }

        # Create test institution and instrument
        inst_user = users["inst.north1@example.com"]
        inst_obj = session.get(Institution, inst_user.institution_id)
        if not inst_obj:
            inst_obj = Institution(
                name="North Tech Matrix Test",
                permanent_id="P-MATRIX-1",
                region="NR",
            )
            session.add(inst_obj)
            session.commit()
            session.refresh(inst_obj)
            inst_user.institution_id = inst_obj.id
            session.add(inst_user)
            session.commit()

        instrument = Instrument(
            institution_id=inst_obj.id,
            region="NR",
            kind="FDR",
            ref_no="FDR-MATRIX-001",
            bank_code="SBIN",
            ifsc="SBIN0000001",
            amount_paise=150000000,
            issue_date=date(2024, 1, 1),
            maturity_date=date(2024, 1, 2), # matured
            lifecycle="active",
            lien_marked=True,
        )
        session.add(instrument)
        session.commit()
        session.refresh(instrument)

        conf = Confirmation(
            instrument_id=instrument.id,
            method="signed_letter",
            token_hash="hash_matrix_test",
            token_expires_at=datetime.now(UTC) + timedelta(days=14),
            status="confirmed",
            fields={
                "ref_no": instrument.ref_no,
                "bank_code": instrument.bank_code,
                "amount_paise": instrument.amount_paise,
                "maturity_date": str(instrument.maturity_date),
                "lien_marked": True,
            },
            confirmed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=90),
            revoked=False,
        )
        session.add(conf)
        session.commit()

        return {
            "tokens": tokens,
            "instrument_id": str(instrument.id),
        }


# Parametrized Persona x Action Matrix
MATRIX_CASES = [
    # (email, expected_request_code, expected_verify_code, expected_approve_code)
    ("inst.north1@example.com", 200, 403, 403),
    ("officer.north@example.com", 403, 200, 403),
    ("checker.north@example.com", 403, 200, 403),
    ("bureau@example.com", 403, 403, 200),
    ("auditor@example.com", 403, 403, 403),
]


@pytest.mark.parametrize("email,req_code,ver_code,app_code", MATRIX_CASES)
def test_persona_release_action_matrix(
    client: TestClient,
    matrix_setup: dict[str, str],
    email: str,
    req_code: int,
    ver_code: int,
    app_code: int,
) -> None:
    tokens = matrix_setup["tokens"]
    instrument_id = matrix_setup["instrument_id"]
    headers = {"Authorization": tokens[email]}

    # 1. Test Request Action
    req_res = client.post(
        f"{settings.API_V1_STR}/instruments/{instrument_id}/release",
        headers=headers,
        json={"path": "term_completion", "attestation_no_complaints": True},
    )
    assert req_res.status_code == req_code, f"{email} request_release expected {req_code}, got {req_res.status_code}: {req_res.text}"

    # Setup a clean submitted release request for verify action test
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        assert inst_user
        inst_user_id = inst_user.id
        rel_req = ReleaseRequest(
            instrument_id=uuid.UUID(instrument_id),
            path="term_completion",
            checklist=[],
            status="submitted",
            requested_by=inst_user_id,
        )
        session.add(rel_req)
        session.commit()
        session.refresh(rel_req)
        verify_req_id = str(rel_req.id)

    # 2. Test Verify Action
    ver_res = client.post(
        f"{settings.API_V1_STR}/release/{verify_req_id}/verify",
        headers=headers,
    )
    assert ver_res.status_code == ver_code, f"{email} verify_release expected {ver_code}, got {ver_res.status_code}: {ver_res.text}"

    # Setup a verified release request for approve action test (verified by officer.north)
    with Session(engine) as session:
        officer = session.exec(select(User).where(User.email == "officer.north@example.com")).first()
        assert officer
        rel_req_approve = ReleaseRequest(
            instrument_id=uuid.UUID(instrument_id),
            path="term_completion",
            checklist=[],
            status="verified",
            requested_by=inst_user_id,
            verified_by=officer.id,
        )
        session.add(rel_req_approve)
        session.commit()
        session.refresh(rel_req_approve)
        approve_req_id = str(rel_req_approve.id)

    # 3. Test Approve Action
    app_res = client.post(
        f"{settings.API_V1_STR}/release/{approve_req_id}/approve",
        headers=headers,
    )
    assert app_res.status_code == app_code, f"{email} approve_release expected {app_code}, got {app_res.status_code}: {app_res.text}"


def test_maker_cannot_be_checker_bureau_self_approval_blocked(
    client: TestClient,
    matrix_setup: dict[str, str],
) -> None:
    """Invariant I8: If Bureau user somehow verified, they are blocked from approving (403 Maker cannot be checker)."""
    tokens = matrix_setup["tokens"]
    instrument_id = matrix_setup["instrument_id"]
    bureau_headers = {"Authorization": tokens["bureau@example.com"]}

    with Session(engine) as session:
        bureau = session.exec(select(User).where(User.email == "bureau@example.com")).first()
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        assert bureau and inst_user
        rel_req = ReleaseRequest(
            instrument_id=uuid.UUID(instrument_id),
            path="term_completion",
            checklist=[],
            status="verified",
            requested_by=inst_user.id,
            verified_by=bureau.id, # Bureau is maker
        )
        session.add(rel_req)
        session.commit()
        session.refresh(rel_req)
        rel_id = str(rel_req.id)

    res = client.post(f"{settings.API_V1_STR}/release/{rel_id}/approve", headers=bureau_headers)
    assert res.status_code == 403
    assert "Maker cannot be checker" in res.json()["detail"]
