"""Seed rich, realistic, diverse synthetic data for AICTE Security Deposit / FDR Portal.

Populates institutions, instruments across lifecycles, confirmations, discrepancy flags,
waivers, renewal chains, release requests, and audit ledger entries.
All numbers in integer paise. All bank/institution details synthetic and labelled.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.core.audit import audit
from app.core.db import engine
from app.models import (
    Confirmation,
    FlagWaiver,
    Institution,
    Instrument,
    ReleaseRequest,
    User,
)


def seed_rich_data() -> None:
    from app.core.rls_context import install_rls_context, set_rls_context

    install_rls_context()
    with Session(engine) as session:
        set_rls_context(session, role="bureau")
        # 1. Fetch Key Users
        officer = session.exec(
            select(User).where(User.email == "officer.north@example.com")
        ).first()
        inst_user = session.exec(
            select(User).where(User.email == "inst.north1@example.com")
        ).first()
        inst2_user = session.exec(
            select(User).where(User.email == "inst.north2@example.com")
        ).first()
        west_user = session.exec(
            select(User).where(User.email == "inst.west@example.com")
        ).first()

        if not officer or not inst_user:
            from app.core.db import init_db

            init_db(session)
            officer = session.exec(
                select(User).where(User.email == "officer.north@example.com")
            ).first()
            inst_user = session.exec(
                select(User).where(User.email == "inst.north1@example.com")
            ).first()
            inst2_user = session.exec(
                select(User).where(User.email == "inst.north2@example.com")
            ).first()
            west_user = session.exec(
                select(User).where(User.email == "inst.west@example.com")
            ).first()

        fallback = session.exec(select(User)).first()
        fallback_id = fallback.id if fallback else uuid.uuid4()
        officer_id = officer.id if officer else fallback_id
        inst_user_id = inst_user.id if inst_user else fallback_id

        # 2. Seed Diverse Institutions Across Regions
        institutions_def = [
            (
                "Delhi Institute of Technology & Engineering",
                "P-DELHI-ENG-01",
                "NR",
                inst_user,
            ),
            (
                "Chandigarh Polytechnic Research Institute",
                "P-CHANDIGARH-01",
                "NR",
                inst2_user,
            ),
            ("Jaipur College of Technological Studies", "P-JAIPUR-01", "NR", None),
            ("Lucknow National Pharmaceutical Institute", "P-LUCKNOW-01", "NR", None),
            ("Mumbai Polytechnic of Advanced Science", "P-MUMBAI-01", "WR", west_user),
            ("Pune College of Engineering & Robotics", "P-PUNE-01", "WR", None),
            ("Gujarat Management Studies & Tech", "P-GUJARAT-01", "WR", None),
            ("Bangalore College of Technological Sciences", "P-BLR-01", "SR", None),
            ("Chennai Institute of Applied Technology", "P-CHENNAI-01", "SR", None),
            ("Kolkata Institute of Engineering & Research", "P-KOLKATA-01", "ER", None),
            ("Bhopal National Polytechnic & Science", "P-BHOPAL-01", "CR", None),
        ]

        inst_map: dict[str, Institution] = {}
        for name, perm_id, region, user_obj in institutions_def:
            existing_inst = session.exec(
                select(Institution).where(Institution.permanent_id == perm_id)
            ).first()
            if not existing_inst:
                inst_obj = Institution(
                    name=name,
                    permanent_id=perm_id,
                    region=region,
                )
                session.add(inst_obj)
                session.commit()
                session.refresh(inst_obj)
                inst_map[perm_id] = inst_obj
            else:
                inst_map[perm_id] = existing_inst

            if user_obj and not user_obj.institution_id:
                user_obj.institution_id = inst_map[perm_id].id
                session.add(user_obj)
                session.commit()

        nr_inst1 = inst_map["P-DELHI-ENG-01"]
        nr_inst2 = inst_map["P-CHANDIGARH-01"]
        wr_inst1 = inst_map["P-MUMBAI-01"]
        sr_inst1 = inst_map["P-BLR-01"]

        today = date.today()

        # 3. Comprehensive Synthetic Instruments Specification
        instruments_specs: list[dict[str, Any]] = [
            # --- NR: Active Confirmed FDRs ---
            {
                "ref_no": "FDR-SBIN-2024-1001",
                "inst": nr_inst1,
                "bank": "SBIN",
                "ifsc": "SBIN0001234",
                "amount": 350000000,  # ₹35,00,000
                "issue": today - timedelta(days=730),
                "maturity": today + timedelta(days=2920),
                "lifecycle": "active",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 350000000,
            },
            {
                "ref_no": "FDR-PUNB-2023-2002",
                "inst": nr_inst1,
                "bank": "PUNB",
                "ifsc": "PUNB0102030",
                "amount": 500000000,  # ₹50,00,000
                "issue": today - timedelta(days=1095),
                "maturity": today + timedelta(days=2555),
                "lifecycle": "active",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 500000000,
            },
            {
                "ref_no": "FDR-BARB-2024-3003",
                "inst": nr_inst2,
                "bank": "BARB",
                "ifsc": "BARB0DELHI1",
                "amount": 1000000000,  # ₹1,00,00,000
                "issue": today - timedelta(days=365),
                "maturity": today + timedelta(days=3285),
                "lifecycle": "active",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 1000000000,
            },
            # --- Claimed FDRs (Pending Bank Verification) ---
            {
                "ref_no": "FDR-SBIN-2026-CLAIM1",
                "inst": nr_inst1,
                "bank": "SBIN",
                "ifsc": "SBIN0001234",
                "amount": 350000000,
                "issue": today - timedelta(days=5),
                "maturity": today + timedelta(days=3645),
                "lifecycle": "pending",
                "lien": False,
                "conf_status": None,  # Unconfirmed
            },
            {
                "ref_no": "FDR-CNRB-2026-CLAIM2",
                "inst": nr_inst2,
                "bank": "CNRB",
                "ifsc": "CNRB0005544",
                "amount": 500000000,
                "issue": today - timedelta(days=3),
                "maturity": today + timedelta(days=3647),
                "lifecycle": "pending",
                "lien": False,
                "conf_status": None,
            },
            # --- Upcoming Maturities (for Maturity Report & Escalation Worker) ---
            {
                "ref_no": "FDR-SBIN-2016-EXP15D",
                "inst": nr_inst1,
                "bank": "SBIN",
                "ifsc": "SBIN0001234",
                "amount": 350000000,
                "issue": today - timedelta(days=3635),
                "maturity": today + timedelta(days=15),
                "lifecycle": "active",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 350000000,
            },
            {
                "ref_no": "FDR-PUNB-2016-EXP35D",
                "inst": nr_inst2,
                "bank": "PUNB",
                "ifsc": "PUNB0102030",
                "amount": 500000000,
                "issue": today - timedelta(days=3615),
                "maturity": today + timedelta(days=35),
                "lifecycle": "active",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 500000000,
            },
            {
                "ref_no": "FDR-BARB-2016-EXP65D",
                "inst": nr_inst1,
                "bank": "BARB",
                "ifsc": "BARB0DELHI1",
                "amount": 350000000,
                "issue": today - timedelta(days=3585),
                "maturity": today + timedelta(days=65),
                "lifecycle": "active",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 350000000,
            },
            {
                "ref_no": "FDR-HDFC-2016-EXP85D",
                "inst": nr_inst2,
                "bank": "HDFC",
                "ifsc": "HDFC0001122",
                "amount": 500000000,
                "issue": today - timedelta(days=3565),
                "maturity": today + timedelta(days=85),
                "lifecycle": "active",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 500000000,
            },
            # --- Matured FDRs ---
            {
                "ref_no": "FDR-ICIC-2016-MATURED1",
                "inst": nr_inst1,
                "bank": "ICIC",
                "ifsc": "ICIC0003344",
                "amount": 350000000,
                "issue": today - timedelta(days=3660),
                "maturity": today - timedelta(days=10),
                "lifecycle": "matured",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 350000000,
            },
            # --- Discrepancy Case: Amount Mismatch (Needs Scrutiny) ---
            {
                "ref_no": "FDR-DISC-AMOUNT-01",
                "inst": nr_inst1,
                "bank": "SBIN",
                "ifsc": "SBIN0001234",
                "amount": 500000000,  # Claimed: ₹50 Lakhs
                "issue": today - timedelta(days=90),
                "maturity": today + timedelta(days=3560),
                "lifecycle": "active",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 350000000,  # Bank confirmed: ₹35 Lakhs -> Discrepancy!
                "discrepancy": True,
            },
            # --- Discrepancy Case with Formal Waiver Recorded ---
            {
                "ref_no": "FDR-DISC-WAIVED-02",
                "inst": nr_inst2,
                "bank": "PUNB",
                "ifsc": "PUNB0102030",
                "amount": 350000000,
                "issue": today - timedelta(days=120),
                "maturity": today + timedelta(days=3530),
                "lifecycle": "active",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 250000000,
                "waiver_reason": "Original deposit split across two tranches due to bank branch ceiling; secondary tranche FDR-PUNB-2024-SUPP verified against physical letter.",
            },
            # --- WR & SR Active Confirmed FDRs ---
            {
                "ref_no": "FDR-WR-MUMBAI-501",
                "inst": wr_inst1,
                "bank": "BARB",
                "ifsc": "BARB0MUMBAI",
                "amount": 750000000,  # ₹75 Lakhs
                "issue": today - timedelta(days=400),
                "maturity": today + timedelta(days=3250),
                "lifecycle": "active",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 750000000,
            },
            {
                "ref_no": "FDR-SR-BLR-601",
                "inst": sr_inst1,
                "bank": "CNRB",
                "ifsc": "CNRB0001234",
                "amount": 1000000000,  # ₹1 Crore
                "issue": today - timedelta(days=500),
                "maturity": today + timedelta(days=3150),
                "lifecycle": "active",
                "lien": True,
                "conf_status": "confirmed",
                "conf_amount": 1000000000,
            },
        ]

        created_instruments: dict[str, Instrument] = {}

        for s in instruments_specs:
            existing = session.exec(
                select(Instrument).where(Instrument.ref_no == s["ref_no"])
            ).first()

            if not existing:
                inst_record = Instrument(
                    institution_id=s["inst"].id,
                    region=s["inst"].region,
                    kind="FDR",
                    ref_no=s["ref_no"],
                    bank_code=s["bank"],
                    ifsc=s["ifsc"],
                    amount_paise=s["amount"],
                    issue_date=s["issue"],
                    maturity_date=s["maturity"],
                    holders=[{"name": s["inst"].name, "share": 100}],
                    lien_marked=s["lien"],
                    is_duplicate_receipt=False,
                    lifecycle=s["lifecycle"],
                    created_by=inst_user_id,
                )
                session.add(inst_record)
                session.commit()
                session.refresh(inst_record)
                created_instruments[s["ref_no"]] = inst_record

                # Audit log for submission
                audit(
                    session,
                    actor_id=inst_user_id,
                    action="INSTRUMENT_SUBMIT",
                    entity="instrument",
                    entity_id=str(inst_record.id),
                    payload={
                        "ref_no": inst_record.ref_no,
                        "bank_code": inst_record.bank_code,
                        "amount_paise": inst_record.amount_paise,
                    },
                )

                # Add Confirmation if specified
                if s["conf_status"]:
                    conf = Confirmation(
                        instrument_id=inst_record.id,
                        status=s["conf_status"],
                        method="signed_letter",
                        token_hash=f"token_hash_{s['ref_no']}",
                        token_expires_at=datetime.now(UTC) + timedelta(days=30),
                        confirmed_at=datetime.now(UTC) - timedelta(days=30),
                        expires_at=datetime.now(UTC) + timedelta(days=3650),
                        fields={
                            "ref_no": inst_record.ref_no,
                            "bank_code": inst_record.bank_code,
                            "amount_paise": s["conf_amount"],
                            "maturity_date": str(inst_record.maturity_date),
                            "lien_marked": inst_record.lien_marked,
                        },
                    )
                    session.add(conf)
                    session.commit()

                    audit(
                        session,
                        actor_id=officer_id,
                        action="BANK_CONFIRMATION_VERIFIED",
                        entity="confirmation",
                        entity_id=str(conf.id),
                        payload={
                            "ref_no": inst_record.ref_no,
                            "confirmed_amount_paise": s["conf_amount"],
                            "status": s["conf_status"],
                        },
                    )

                # Add Waiver if specified
                if s.get("waiver_reason"):
                    waiver = FlagWaiver(
                        instrument_id=inst_record.id,
                        code="D1_AMOUNT_MISMATCH",
                        reason=s["waiver_reason"],
                        waived_by=officer_id,
                    )
                    session.add(waiver)
                    session.commit()

                    audit(
                        session,
                        actor_id=officer_id,
                        action="DISCREPANCY_WAIVED",
                        entity="flag_waiver",
                        entity_id=str(waiver.id),
                        payload={
                            "code": "D1_AMOUNT_MISMATCH",
                            "reason": s["waiver_reason"],
                        },
                    )
            else:
                created_instruments[s["ref_no"]] = existing

        # 4. Renewal Chain (Predecessor -> Linked Successor)
        old_ref = "FDR-RENEW-OLD-01"
        new_ref = "FDR-RENEW-NEW-02"

        old_inst = session.exec(
            select(Instrument).where(Instrument.ref_no == old_ref)
        ).first()
        if not old_inst:
            old_inst = Instrument(
                institution_id=nr_inst1.id,
                region="NR",
                kind="FDR",
                ref_no=old_ref,
                bank_code="SBIN",
                ifsc="SBIN0001234",
                amount_paise=350000000,
                issue_date=today - timedelta(days=3650),
                maturity_date=today - timedelta(days=1),
                holders=[{"name": nr_inst1.name, "share": 100}],
                lien_marked=True,
                lifecycle="renewed",
                created_by=inst_user_id,
            )
            session.add(old_inst)
            session.commit()
            session.refresh(old_inst)

        new_inst = session.exec(
            select(Instrument).where(Instrument.ref_no == new_ref)
        ).first()
        if not new_inst:
            new_inst = Instrument(
                institution_id=nr_inst1.id,
                region="NR",
                kind="FDR",
                ref_no=new_ref,
                bank_code="SBIN",
                ifsc="SBIN0001234",
                amount_paise=350000000,
                issue_date=today,
                maturity_date=today + timedelta(days=3650),
                holders=[{"name": nr_inst1.name, "share": 100}],
                lien_marked=True,
                lifecycle="active",
                replaces_id=old_inst.id,  # Renewal Chain linkage!
                created_by=inst_user_id,
            )
            session.add(new_inst)
            session.commit()
            session.refresh(new_inst)

            conf_renew = Confirmation(
                instrument_id=new_inst.id,
                status="confirmed",
                method="signed_letter",
                token_hash="token_renew_02",
                token_expires_at=datetime.now(UTC) + timedelta(days=30),
                confirmed_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(days=3650),
                fields={
                    "ref_no": new_inst.ref_no,
                    "bank_code": new_inst.bank_code,
                    "amount_paise": new_inst.amount_paise,
                    "maturity_date": str(new_inst.maturity_date),
                    "lien_marked": True,
                },
            )
            session.add(conf_renew)
            session.commit()

            audit(
                session,
                actor_id=inst_user_id,
                action="RENEWAL_SUBMITTED",
                entity="instrument",
                entity_id=str(new_inst.id),
                payload={
                    "ref_no": new_ref,
                    "replaces_ref": old_ref,
                    "coverage_gap_days": 0,
                },
            )

        # 5. Release Workflow Showcase Cases (Requested, Verified, Approved)
        # Release Case 1: Status = "submitted" (Institution requested release)
        rel_inst1 = created_instruments.get("FDR-ICIC-2016-MATURED1")
        if rel_inst1:
            existing_req = session.exec(
                select(ReleaseRequest).where(
                    ReleaseRequest.instrument_id == rel_inst1.id
                )
            ).first()
            if not existing_req:
                req1 = ReleaseRequest(
                    instrument_id=rel_inst1.id,
                    path="term_completion",
                    status="submitted",
                    requested_by=inst_user_id,
                    checklist=[
                        {"item": "Tenure Completed (10 Years)", "satisfied": True},
                        {"item": "No Pending AICTE Inquiries", "satisfied": True},
                        {"item": "Resolution from Governing Body", "satisfied": True},
                    ],
                )
                session.add(req1)
                session.commit()

                audit(
                    session,
                    actor_id=inst_user_id,
                    action="RELEASE_REQUESTED",
                    entity="release_request",
                    entity_id=str(req1.id),
                    payload={
                        "instrument_ref": rel_inst1.ref_no,
                        "path": "term_completion",
                    },
                )

        # Release Case 2: Status = "verified" (Regional Officer Maker verified, ready for Bureau)
        rel_inst2 = created_instruments.get("FDR-SBIN-2016-EXP15D")
        if rel_inst2:
            existing_req2 = session.exec(
                select(ReleaseRequest).where(
                    ReleaseRequest.instrument_id == rel_inst2.id
                )
            ).first()
            if not existing_req2:
                req2 = ReleaseRequest(
                    instrument_id=rel_inst2.id,
                    path="term_completion",
                    status="verified",
                    requested_by=inst_user_id,
                    verified_by=officer_id,
                    checklist=[
                        {"item": "Tenure Completed (10 Years)", "satisfied": True},
                        {"item": "No Pending AICTE Inquiries", "satisfied": True},
                        {"item": "Resolution from Governing Body", "satisfied": True},
                        {"item": "Scrutiny Officer Inspection", "satisfied": True},
                    ],
                )
                session.add(req2)
                session.commit()

                audit(
                    session,
                    actor_id=officer_id,
                    action="RELEASE_VERIFIED",
                    entity="release_request",
                    entity_id=str(req2.id),
                    payload={
                        "instrument_ref": rel_inst2.ref_no,
                        "verified_by": "officer.north@example.com",
                    },
                )

        # 6. Seed Statement Reports Top-Up
        from app.seed_reports_topup import seed_reports_topup

        seed_reports_topup(session)

        # 7. Run maturity worker for upcoming maturities and overdue obligations
        from app.domain.worker import run_daily_obligations_job

        run_daily_obligations_job(session)


if __name__ == "__main__":
    seed_rich_data()
