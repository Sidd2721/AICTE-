import hashlib
import uuid
from datetime import UTC, date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.domain.receipt import sign_release_receipt, verify_release_receipt
from app.main import app
from app.models import Confirmation, Instrument, ReleaseRequest, User
from tests.utils.user import authentication_token_from_email


@pytest.fixture(name="users_and_tokens")
def fixture_users_and_tokens() -> dict[str, dict[str, str]]:
    from app.core.security import create_access_token
    with Session(engine) as session:
        # Get or verify the test users
        officer = session.exec(select(User).where(User.email == "officer.north@example.com")).first()
        bureau = session.exec(select(User).where(User.email == "bureau@example.com")).first()
        auditor = session.exec(select(User).where(User.email == "auditor@example.com")).first()
        inst = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()

        assert officer and bureau and auditor and inst
        return {
            "regional": {"Authorization": f"Bearer {create_access_token(officer.id, timedelta(minutes=60))}"},
            "bureau": {"Authorization": f"Bearer {create_access_token(bureau.id, timedelta(minutes=60))}"},
            "auditor": {"Authorization": f"Bearer {create_access_token(auditor.id, timedelta(minutes=60))}"},
            "institution": {"Authorization": f"Bearer {create_access_token(inst.id, timedelta(minutes=60))}"},
        }


def test_receipt_crypto_roundtrip_tamper_and_alg_none() -> None:
    receipt_id = str(uuid.uuid4())
    token = sign_release_receipt(
        receipt_id=receipt_id,
        instrument_id="inst-123",
        instrument_ref_no="FDR-9999",
        path="term_completion",
    )
    assert token

    # 1. Valid verify
    payload = verify_release_receipt(token)
    assert payload["receipt_id"] == receipt_id
    assert payload["path"] == "term_completion"
    assert "instrument_hash" in payload
    # Assert no PII or amounts in token
    assert "amount" not in payload
    assert "amount_paise" not in payload
    assert "email" not in payload

    # 2. Tampered token fails
    parts = token.split(".")
    tampered = f"{parts[0]}.{parts[1][:-4]}AAAA.{parts[2]}"
    with pytest.raises(Exception):
        verify_release_receipt(tampered)

    # 3. Alg None attack fails
    none_token = f"{parts[0]}.{parts[1]}."
    with pytest.raises(Exception):
        verify_release_receipt(none_token)


def test_release_maker_checker_flow_and_dual_custody(client: TestClient, users_and_tokens: dict[str, dict[str, str]]) -> None:
    # 1. Setup active instrument with confirmation
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        assert inst_user
        if not inst_user.institution_id:
            from app.models import Institution
            inst_obj = Institution(
                name="North Tech 1",
                permanent_id=f"P-NT-{uuid.uuid4().hex[:6]}",
                region="NR",
            )
            session.add(inst_obj)
            session.commit()
            session.refresh(inst_obj)
            inst_user.institution_id = inst_obj.id
            session.add(inst_user)
            session.commit()
            session.refresh(inst_user)

        institution_id = inst_user.institution_id
        assert institution_id is not None
        
        instrument = Instrument(
            institution_id=institution_id,
            region="NR",
            kind="FDR",
            ref_no=f"REL-TDD-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=150000000,
            issue_date=date.today() - timedelta(days=3650),
            maturity_date=date.today() - timedelta(days=5),
            lien_marked=True,
            lifecycle="active",
        )
        session.add(instrument)
        session.commit()
        session.refresh(instrument)
        inst_id = instrument.id

        # Add valid confirmed confirmation
        conf = Confirmation(
            instrument_id=inst_id,
            status="confirmed",
            method="signed_letter",
            token_hash="dummy_hash",
            token_expires_at=datetime.now(UTC) + timedelta(days=14),
            confirmed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=365),
            fields={
                "ref_no": instrument.ref_no,
                "bank_code": instrument.bank_code,
                "amount_paise": 150000000,
                "maturity_date": str(instrument.maturity_date),
                "lien_marked": True,
            },
        )
        session.add(conf)
        session.commit()

    # 2. Institution requests release
    req_res = client.post(
        f"/api/v1/instruments/{inst_id}/release",
        headers=users_and_tokens["institution"],
        json={"path": "term_completion"},
    )
    assert req_res.status_code == 200, req_res.text
    rel_data = req_res.json()
    rel_id = rel_data["id"]
    assert rel_data["path"] == "term_completion"
    assert rel_data["status"] == "submitted"
    assert len(rel_data["checklist"]) > 0

    # 3. Auditor tries to verify or approve -> 403
    aud_res = client.patch(
        f"/api/v1/release/{rel_id}/verify",
        headers=users_and_tokens["auditor"],
    )
    assert aud_res.status_code == 403

    # 4. Regional officer verifies (Maker side)
    reg_res = client.patch(
        f"/api/v1/release/{rel_id}/verify",
        headers=users_and_tokens["regional"],
    )
    assert reg_res.status_code == 200, reg_res.text
    ver_data = reg_res.json()
    assert ver_data["status"] == "verified"
    assert ver_data["verified_by"] is not None

    # 5. Regional officer tries to approve (Maker-Checker violation!) -> 403
    reg_app_res = client.patch(
        f"/api/v1/release/{rel_id}/approve",
        headers=users_and_tokens["regional"],
    )
    assert reg_app_res.status_code == 403
    assert "Maker cannot be checker" in reg_app_res.text or "Only Bureau" in reg_app_res.text

    # 6. Bureau officer approves (Checker side)
    bur_res = client.patch(
        f"/api/v1/release/{rel_id}/approve",
        headers=users_and_tokens["bureau"],
    )
    assert bur_res.status_code == 200, bur_res.text
    app_data = bur_res.json()
    assert app_data["status"] == "released"
    assert app_data["approved_by"] is not None
    assert app_data["receipt_token"] is not None

    # Verify instrument lifecycle became released
    with Session(engine) as session:
        inst_db = session.get(Instrument, inst_id)
        assert inst_db and inst_db.lifecycle == "released"

    # 7. Public verification of receipt token
    pub_res = client.get(
        f"/api/v1/release/verify-receipt?token={app_data['receipt_token']}"
    )
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["status"] == "valid"
    assert pub_data["path"] == "term_completion"


def test_closure_matured_waiver_and_conversion_attestation(client: TestClient, users_and_tokens: dict[str, dict[str, str]]) -> None:
    # Test closure waiver for already matured deposit
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        assert inst_user
        if not inst_user.institution_id:
            from app.models import Institution
            inst_obj = Institution(
                name="North Tech 1",
                permanent_id=f"P-NT-{uuid.uuid4().hex[:6]}",
                region="NR",
            )
            session.add(inst_obj)
            session.commit()
            session.refresh(inst_obj)
            inst_user.institution_id = inst_obj.id
            session.add(inst_user)
            session.commit()
            session.refresh(inst_user)

        institution_id = inst_user.institution_id
        assert institution_id is not None
        
        matured_inst = Instrument(
            institution_id=institution_id,
            region="NR",
            kind="FDR",
            ref_no=f"MAT-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=150000000,
            issue_date=date.today() - timedelta(days=3650),
            maturity_date=date.today() - timedelta(days=10),
            lifecycle="matured",
        )
        session.add(matured_inst)
        session.commit()
        session.refresh(matured_inst)

    res = client.post(
        f"/api/v1/instruments/{matured_inst.id}/release",
        headers=users_and_tokens["institution"],
        json={"path": "closure"},
    )
    assert res.status_code == 200
    data = res.json()
    # closure_certificate should have waived=True because deposit_matured
    items = {item["id"]: item for item in data["checklist"]}
    assert "closure_certificate" in items
    assert items["closure_certificate"].get("waived") is True


def test_maker_checker_same_user_approval_blocked(
    client: TestClient, users_and_tokens: dict[str, dict[str, str]]
) -> None:
    with Session(engine) as session:
        bureau_user = session.exec(
            select(User).where(User.email == "bureau@example.com")
        ).first()
        inst_user = session.exec(
            select(User).where(User.email == "inst.north1@example.com")
        ).first()
        assert bureau_user and inst_user
        inst = Instrument(
            institution_id=inst_user.institution_id,
            region="NR",
            kind="FDR",
            ref_no=f"MC-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=100000000,
            issue_date=date.today(),
            maturity_date=date.today() + timedelta(days=365),
            lifecycle="active",
        )
        session.add(inst)
        session.commit()
        session.refresh(inst)

        rel = ReleaseRequest(
            instrument_id=inst.id,
            path="term_completion",
            status="verified",
            requested_by=inst_user.id,
            verified_by=bureau_user.id,
        )
        session.add(rel)
        session.commit()
        session.refresh(rel)
        rel_id = rel.id

    res = client.patch(
        f"/api/v1/release/{rel_id}/approve",
        headers=users_and_tokens["bureau"],
    )
    assert res.status_code == 403
    assert "Maker cannot be checker" in res.text


@pytest.mark.parametrize(
    "role,action,expected_status",
    [
        ("institution", "request", 200),
        ("regional", "request", 403),
        ("bureau", "request", 403),
        ("auditor", "request", 403),
        ("institution", "verify", 403),
        ("regional", "verify", 200),
        ("bureau", "verify", 403),
        ("auditor", "verify", 403),
        ("institution", "approve", 403),
        ("regional", "approve", 403),
        ("bureau", "approve", 200),
        ("auditor", "approve", 403),
    ],
)
def test_release_matrix_roles_contract(
    client: TestClient,
    users_and_tokens: dict[str, dict[str, str]],
    role: str,
    action: str,
    expected_status: int,
) -> None:
    with Session(engine) as session:
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        officer_user = session.exec(select(User).where(User.email == "officer.north@example.com")).first()
        assert inst_user and officer_user
        inst = Instrument(
            institution_id=inst_user.institution_id,
            region="NR",
            kind="FDR",
            ref_no=f"MATR-{uuid.uuid4().hex[:6]}",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=150000000,
            issue_date=date.today() - timedelta(days=3650),
            maturity_date=date.today() - timedelta(days=5),
            lien_marked=True,
            lifecycle="matured",
        )
        session.add(inst)
        session.commit()
        session.refresh(inst)

        conf = Confirmation(
            instrument_id=inst.id,
            status="confirmed",
            method="signed_letter",
            token_hash="dummy_hash",
            token_expires_at=datetime.now(UTC) + timedelta(days=14),
            confirmed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=365),
            fields={
                "ref_no": inst.ref_no,
                "bank_code": inst.bank_code,
                "amount_paise": 150000000,
                "maturity_date": str(inst.maturity_date),
                "lien_marked": True,
            },
        )
        session.add(conf)

        rel = ReleaseRequest(
            instrument_id=inst.id,
            path="term_completion",
            status="submitted" if action != "approve" else "verified",
            requested_by=inst_user.id,
            verified_by=officer_user.id if action == "approve" else None,
        )
        session.add(rel)
        session.commit()
        session.refresh(rel)
        rel_id = rel.id
        inst_id = inst.id

    headers = users_and_tokens[role]
    if action == "request":
        res = client.post(
            f"/api/v1/instruments/{inst_id}/release",
            headers=headers,
            json={"path": "term_completion"},
        )
    elif action == "verify":
        res = client.patch(
            f"/api/v1/release/{rel_id}/verify",
            headers=headers,
        )
    elif action == "approve":
        res = client.patch(
            f"/api/v1/release/{rel_id}/approve",
            headers=headers,
        )

    assert res.status_code == expected_status, (
        f"Role {role} on {action} expected {expected_status}, got {res.status_code}: {res.text}"
    )

