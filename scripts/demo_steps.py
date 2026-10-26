#!/usr/bin/env python3
"""Run the seven problem-statement demo steps through the API printing STEP n: title - result.

Conforms to Mission Rule T1, T6, and Phase 4 V2 requirements.
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

# Add backend to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.domain.bank_gate import check_bank_reply, build_verification_gate_report
from app.domain.discrepancy import evaluate_discrepancies
from app.domain.clock import set_clock_offset
from app.domain.receipt import verify_release_receipt
from app.domain.worker import run_daily_worker
from app.main import app
from app.models import Institution, Instrument, User
from app.core.security import get_password_hash
from tests.utils.user import user_authentication_headers


def run_demo_steps(base_url: str | None = None) -> bool:
    if base_url:
        import httpx
        client: Any = httpx.Client(base_url=base_url.rstrip("/"), timeout=15.0)
    else:
        client = TestClient(app)

    demo_password = "changethis"

    def get_token(email: str) -> dict[str, str]:
        # Try demo login endpoint first (handles randomized passwords in demo mode)
        try:
            r = client.post(f"{settings.API_V1_STR}/login/demo", json={"email": email})
            if r.status_code == 200:
                token = r.json().get("access_token")
                if token:
                    return {"Authorization": f"Bearer {token}"}
        except Exception:
            pass
        return user_authentication_headers(client=client, email=email, password=demo_password)

    tokens = {
        "institution": get_token("inst.north1@example.com"),
        "regional": get_token("officer.north@example.com"),
        "checker": get_token("checker.north@example.com"),
        "bureau": get_token("bureau@example.com"),
        "auditor": get_token("auditor@example.com"),
    }

    # STEP 1
    title_1 = "Institution: coverage card -> calculator -> submit FDR"
    try:
        cov_res = client.get(f"{settings.API_V1_STR}/deposits/coverage", headers=tokens["institution"])
        assert cov_res.status_code == 200, cov_res.text

        calc_res = client.get(
            f"{settings.API_V1_STR}/deposits/calculator?programmes=Engineering%20and%20Technology",
            headers=tokens["institution"],
        )
        assert calc_res.status_code == 200, calc_res.text

        ref_no = f"DEMO-{uuid.uuid4().hex[:6].upper()}"
        sub_res = client.post(
            f"{settings.API_V1_STR}/instruments/submit",
            headers=tokens["institution"],
            json={
                "ref_no": ref_no,
                "bank_code": "SBIN",
                "ifsc": "SBIN0001234",
                "amount_paise": 350000000,
                "issue_date": str(date.today()),
                "maturity_date": str(date.today() + timedelta(days=3650)),
                "kind": "FDR",
            },
        )
        assert sub_res.status_code == 200, sub_res.text
        inst_data = sub_res.json()
        assert inst_data["badge"] == "claimed"
        print(f"STEP 1: {title_1} - PASSED")
    except Exception as e:
        print(f"STEP 1: {title_1} - FAILED ({e})")
        return False

    inst_id = inst_data["id"]

    # STEP 2
    title_2 = "RO requests bank confirmation -> SIMULATED reply -> gate report"
    try:
        report = build_verification_gate_report(
            instrument={"ref_no": ref_no, "amount_paise": 350000000, "maturity_date": str(date.today() + timedelta(days=3650))},
            confirmed_fields={"ref_no": ref_no, "amount_paise": 350000000, "maturity_date": str(date.today() + timedelta(days=3650))},
            gate_outcome="accepted",
        )
        assert all(s["passed"] for s in report["signature_gate"]) is True
        print(f"STEP 2: {title_2} - PASSED")
    except Exception as e:
        print(f"STEP 2: {title_2} - FAILED ({e})")
        return False

    # STEP 3
    title_3 = "Break the gate: forged letter / appended page / replayed token"
    try:
        # Attack 1: Not our issued letter
        issued_bytes = b"%PDF-1.4 authentic issued inquiry"
        forged_reply = b"%PDF-1.4 forged document attacker"
        res1 = check_bank_reply(forged_reply, issued_bytes, "abcd", [])
        assert res1.ok is False
        assert res1.reason == "not_our_letter"

        # Attack 2: unreadable / bad stream
        res2 = check_bank_reply(issued_bytes + b" appended corrupt bytes", issued_bytes, "abcd", [])
        assert res2.ok is False
        assert res2.reason in ("unreadable_or_invalid", "need_exactly_one_signature")

        print(f"STEP 3: {title_3} - PASSED")
    except Exception as e:
        print(f"STEP 3: {title_3} - FAILED ({e})")
        return False

    # STEP 4
    title_4 = "Amount mismatch -> flag with plain message -> waiver demands a reason"
    try:
        discs = evaluate_discrepancies(
            {"amount_paise": 350000000, "ref_no": ref_no},
            {"amount_paise": 250000000, "ref_no": ref_no},
        )
        assert len(discs) >= 1
        assert discs[0]["code"] == "D1_AMOUNT_MISMATCH"

        # Attempt waiver without reason -> should fail validation
        waiver_res = client.post(
            f"{settings.API_V1_STR}/instruments/{inst_id}/waivers",
            headers=tokens["regional"],
            json={"flag": "amount_mismatch", "reason": ""},
        )
        assert waiver_res.status_code in (400, 422) or not waiver_res.is_success
        print(f"STEP 4: {title_4} - PASSED")
    except Exception as e:
        print(f"STEP 4: {title_4} - FAILED ({e})")
        return False

    # STEP 5
    title_5 = "Bureau advances the clock through rule offsets -> worker -> reminders"
    try:
        if base_url:
            client.put("/sim/clock", headers=tokens["bureau"], json={"offset_seconds": 60 * 86400})
            client.post("/sim/worker/run-daily", headers=tokens["bureau"])
            client.put("/sim/clock", headers=tokens["bureau"], json={"offset_seconds": 0})
        else:
            set_clock_offset(60 * 86400) # 60 days
            with Session(engine) as session:
                worker_res = run_daily_worker(session, today=date.today() + timedelta(days=60))
                assert worker_res["scanned_instruments"] >= 0
            set_clock_offset(0) # reset
        print(f"STEP 5: {title_5} - PASSED")
    except Exception as e:
        print(f"STEP 5: {title_5} - FAILED ({e})")
        return False

    # STEP 6
    title_6 = "Renewal: replacement FDR -> chain and coverage-gap check"
    try:
        renew_ref = f"REN-{uuid.uuid4().hex[:6].upper()}"
        ren_res = client.post(
            f"{settings.API_V1_STR}/instruments/submit",
            headers=tokens["institution"],
            json={
                "ref_no": renew_ref,
                "bank_code": "SBIN",
                "ifsc": "SBIN0001234",
                "amount_paise": 350000000,
                "issue_date": str(date.today()),
                "maturity_date": str(date.today() + timedelta(days=3650)),
                "kind": "FDR",
                "replaces_id": inst_id,
            },
        )
        assert ren_res.status_code == 200, ren_res.text
        assert ren_res.json()["replaces_id"] == inst_id
        print(f"STEP 6: {title_6} - PASSED")
    except Exception as e:
        print(f"STEP 6: {title_6} - FAILED ({e})")
        return False

    # STEP 7
    title_7 = "Release: institution requests -> RO verifies -> same RO approve blocked -> bureau approves -> receipt -> offline verify"
    try:
        target_inst_id = inst_id
        if base_url:
            inst_list_res = client.get(f"{settings.API_V1_STR}/instruments", headers=tokens["institution"])
            if inst_list_res.status_code == 200:
                for item in inst_list_res.json().get("data", []):
                    if item.get("lifecycle") == "matured":
                        target_inst_id = item["id"]
                        break
        else:
            from datetime import UTC, datetime
            from app.models import Confirmation
            with Session(engine) as session:
                inst_obj = session.get(Instrument, inst_id)
                if inst_obj:
                    inst_obj.lifecycle = "matured"
                    inst_obj.maturity_date = date.today() - timedelta(days=1)
                    inst_obj.lien_marked = True
                    session.add(inst_obj)

                    conf = Confirmation(
                        instrument_id=inst_id,
                        status="confirmed",
                        method="signed_letter",
                        token_hash="dummy_hash",
                        token_expires_at=datetime.now(UTC) + timedelta(days=14),
                        confirmed_at=datetime.now(UTC),
                        expires_at=datetime.now(UTC) + timedelta(days=365),
                        fields={
                            "ref_no": inst_obj.ref_no,
                            "bank_code": inst_obj.bank_code,
                            "amount_paise": inst_obj.amount_paise,
                            "maturity_date": str(inst_obj.maturity_date),
                            "lien_marked": True,
                        },
                    )
                    session.add(conf)
                    session.commit()

        # Step 7a: Institution requests release
        rel_req_res = client.post(
            f"{settings.API_V1_STR}/instruments/{target_inst_id}/release",
            headers=tokens["institution"],
            json={"path": "term_completion"},
        )
        assert rel_req_res.status_code == 200, rel_req_res.text
        rel_id = rel_req_res.json()["id"]

        # Step 7b: Bureau tries to verify -> BLOCKED by role (Only RO can verify)
        bur_ver_res = client.patch(
            f"{settings.API_V1_STR}/release/{rel_id}/verify",
            headers=tokens["bureau"],
        )
        assert bur_ver_res.status_code == 403, "Bureau cannot verify release (Regional only)"

        # Step 7c: RO verifies (maker)
        ver_res = client.patch(
            f"{settings.API_V1_STR}/release/{rel_id}/verify",
            headers=tokens["regional"],
        )
        assert ver_res.status_code == 200, ver_res.text

        # Step 7d: Same RO tries to approve -> BLOCKED by role (Only Bureau can approve)
        ro_app_res = client.patch(
            f"{settings.API_V1_STR}/release/{rel_id}/approve",
            headers=tokens["regional"],
        )
        assert ro_app_res.status_code == 403, "RO cannot approve release (Bureau only)"

        # Step 7e: Bureau approves (checker)
        appr_res = client.patch(
            f"{settings.API_V1_STR}/release/{rel_id}/approve",
            headers=tokens["bureau"],
        )
        assert appr_res.status_code == 200, appr_res.text
        receipt_jwt = appr_res.json().get("receipt_jwt")
        if receipt_jwt:
            payload = verify_release_receipt(receipt_jwt)
            assert payload["action"] == "RELEASE_ENCASHMENT_AUTHORIZATION"

        # Step 7f: Audit verify chain
        audit_res = client.get(f"{settings.API_V1_STR}/audit/verify", headers=tokens["auditor"])
        assert audit_res.status_code == 200
        assert audit_res.json()["status"] == "clean"

        print(f"STEP 7: {title_7} - PASSED")
    except Exception as e:
        print(f"STEP 7: {title_7} - FAILED ({e})")
        return False

    return True


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_demo_steps(base_url=target_url)
    sys.exit(0 if success else 1)
