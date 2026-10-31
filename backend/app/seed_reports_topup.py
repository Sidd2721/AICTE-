"""Idempotent demo-only synthetic seed top-up for Statement Reports.

Ensures every regional officer persona (NR, WR) has realistic records across all 4 Statement Reports tabs:
1. Pending Verifications (at least 3 records of different ages)
2. Upcoming Maturities (at least 3 records maturing within 5-85 days)
3. Missing Documents (at least 2 records with distinct missing document types)
4. Cases Needing Intervention (at least 2 records with distinct intervention reasons)

All data is synthetic, labelled, and audited through audit_append().
Never runs in production.
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

from sqlmodel import Session, select

from app.core.audit import audit
from app.core.config import settings
from app.core.db import engine, init_db
from app.domain.clock import today as get_today
from app.models import (
    Confirmation,
    Document,
    Institution,
    Instrument,
    Obligation,
    User,
)


def seed_reports_topup(session: Session | None = None) -> int:
    """Seed synthetic top-up records for Statement Reports across NR and WR.

    Returns the count of newly inserted instruments (0 on subsequent runs).
    """
    if settings.FASTAPI_ENV == "production":
        return 0

    if session is not None:
        return _seed_reports_topup_in_session(session)

    with Session(engine) as s:
        return _seed_reports_topup_in_session(s)


def _seed_reports_topup_in_session(session: Session) -> int:
    from app.core.rls_context import set_rls_context

    set_rls_context(session, role="bureau")
    today_val = get_today()
    inserted_count = 0

    # Ensure demo institutions and users exist
    nr_inst = session.exec(
        select(Institution).where(Institution.permanent_id == "P-DELHI-ENG-01")
    ).first()
    wr_inst = session.exec(
        select(Institution).where(Institution.permanent_id == "P-MUMBAI-01")
    ).first()

    if not nr_inst or not wr_inst:
        init_db(session)
        from app.seed_rich_synthetic_data import seed_rich_data

        seed_rich_data()
        nr_inst = session.exec(
            select(Institution).where(Institution.permanent_id == "P-DELHI-ENG-01")
        ).first()
        wr_inst = session.exec(
            select(Institution).where(Institution.permanent_id == "P-MUMBAI-01")
        ).first()

    # User mappings
    nr_officer = session.exec(
        select(User).where(User.email == "officer.north@example.com")
    ).first()
    wr_officer = session.exec(
        select(User).where(User.email == "officer.west@example.com")
    ).first()
    nr_inst_user = session.exec(
        select(User).where(User.email == "inst.north1@example.com")
    ).first()
    wr_inst_user = session.exec(
        select(User).where(User.email == "inst.west@example.com")
    ).first()

    fallback_user = session.exec(select(User)).first()
    fallback_id = fallback_user.id if fallback_user else uuid.uuid4()

    class RegionSeedTarget(NamedTuple):
        region: str
        inst: Institution
        officer_id: uuid.UUID
        inst_user_id: uuid.UUID

    if not nr_inst or not wr_inst:
        return 0

    targets = [
        RegionSeedTarget(
            region="NR",
            inst=nr_inst,
            officer_id=nr_officer.id if nr_officer else fallback_id,
            inst_user_id=nr_inst_user.id if nr_inst_user else fallback_id,
        ),
        RegionSeedTarget(
            region="WR",
            inst=wr_inst,
            officer_id=wr_officer.id if wr_officer else fallback_id,
            inst_user_id=wr_inst_user.id if wr_inst_user else fallback_id,
        ),
    ]

    for target in targets:
        reg = target.region
        inst = target.inst
        officer_id = target.officer_id
        inst_user_id = target.inst_user_id

        specs: list[dict[str, Any]] = [
            # 1. Pending Verifications (3 of different ages: 2d, 15d, 45d)
            {
                "ref_no": f"SYN-REP-{reg}-PV-01",
                "bank": "SBIN",
                "ifsc": "SBIN0001234",
                "amount": 350000000,
                "issue": today_val - timedelta(days=2),
                "maturity": today_val + timedelta(days=3648),
                "lifecycle": "pending",
                "lien": False,
                "confirmed": False,
                "docs": ["fdr_scan", "payment_proof"],
                "overdue_ob": None,
            },
            {
                "ref_no": f"SYN-REP-{reg}-PV-02",
                "bank": "PUNB",
                "ifsc": "PUNB0102030",
                "amount": 500000000,
                "issue": today_val - timedelta(days=15),
                "maturity": today_val + timedelta(days=3635),
                "lifecycle": "pending",
                "lien": False,
                "confirmed": False,
                "docs": ["fdr_scan", "payment_proof"],
                "overdue_ob": None,
            },
            {
                "ref_no": f"SYN-REP-{reg}-PV-03",
                "bank": "BARB",
                "ifsc": "BARB0DELHI1" if reg == "NR" else "BARB0MUMBAI",
                "amount": 1000000000,
                "issue": today_val - timedelta(days=45),
                "maturity": today_val + timedelta(days=3605),
                "lifecycle": "pending",
                "lien": False,
                "confirmed": False,
                "docs": ["fdr_scan", "payment_proof"],
                "overdue_ob": None,
            },
            # 2. Upcoming Maturities (3 maturing between 5 and 85 days: +18d, +42d, +70d)
            {
                "ref_no": f"SYN-REP-{reg}-UM-01",
                "bank": "SBIN",
                "ifsc": "SBIN0001234",
                "amount": 350000000,
                "issue": today_val - timedelta(days=3632),
                "maturity": today_val + timedelta(days=18),
                "lifecycle": "active",
                "lien": True,
                "confirmed": True,
                "docs": ["fdr_scan", "payment_proof"],
                "overdue_ob": None,
            },
            {
                "ref_no": f"SYN-REP-{reg}-UM-02",
                "bank": "HDFC",
                "ifsc": "HDFC0001122",
                "amount": 500000000,
                "issue": today_val - timedelta(days=3608),
                "maturity": today_val + timedelta(days=42),
                "lifecycle": "active",
                "lien": True,
                "confirmed": True,
                "docs": ["fdr_scan", "payment_proof"],
                "overdue_ob": None,
            },
            {
                "ref_no": f"SYN-REP-{reg}-UM-03",
                "bank": "ICIC",
                "ifsc": "ICIC0003344",
                "amount": 750000000,
                "issue": today_val - timedelta(days=3580),
                "maturity": today_val + timedelta(days=70),
                "lifecycle": "active",
                "lien": True,
                "confirmed": True,
                "docs": ["fdr_scan", "payment_proof"],
                "overdue_ob": None,
            },
            # 3. Missing Documents (2 records: one missing fdr_scan, one missing payment_proof)
            {
                "ref_no": f"SYN-REP-{reg}-MD-01",
                "bank": "SBIN",
                "ifsc": "SBIN0001234",
                "amount": 350000000,
                "issue": today_val - timedelta(days=60),
                "maturity": today_val + timedelta(days=3590),
                "lifecycle": "active",
                "lien": True,
                "confirmed": True,
                "docs": ["payment_proof"],  # missing fdr_scan
                "overdue_ob": None,
            },
            {
                "ref_no": f"SYN-REP-{reg}-MD-02",
                "bank": "PUNB",
                "ifsc": "PUNB0102030",
                "amount": 500000000,
                "issue": today_val - timedelta(days=30),
                "maturity": today_val + timedelta(days=3620),
                "lifecycle": "pending",
                "lien": False,
                "confirmed": False,
                "docs": ["fdr_scan"],  # missing payment_proof
                "overdue_ob": None,
            },
            # 4. Cases Needing Intervention (2 records: one matured past due, one with overdue obligation)
            {
                "ref_no": f"SYN-REP-{reg}-CN-01",
                "bank": "SBIN",
                "ifsc": "SBIN0001234",
                "amount": 350000000,
                "issue": today_val - timedelta(days=3670),
                "maturity": today_val - timedelta(days=20),
                "lifecycle": "matured",
                "lien": True,
                "confirmed": True,
                "docs": ["fdr_scan", "payment_proof"],
                "overdue_ob": None,
            },
            {
                "ref_no": f"SYN-REP-{reg}-CN-02",
                "bank": "BARB",
                "ifsc": "BARB0DELHI1" if reg == "NR" else "BARB0MUMBAI",
                "amount": 500000000,
                "issue": today_val - timedelta(days=700),
                "maturity": today_val + timedelta(days=2950),
                "lifecycle": "active",
                "lien": True,
                "confirmed": True,
                "docs": ["fdr_scan", "payment_proof"],
                "overdue_ob": {
                    "kind": "renewal_due",
                    "due_date": today_val - timedelta(days=12),
                    "status": "open",
                    "owner_role": "institution",
                },
            },
        ]

        for s in specs:
            existing = session.exec(
                select(Instrument).where(Instrument.ref_no == s["ref_no"])
            ).first()
            if existing:
                if (
                    existing.lifecycle != s["lifecycle"]
                    or existing.maturity_date != s["maturity"]
                    or existing.issue_date != s["issue"]
                ):
                    existing.lifecycle = s["lifecycle"]
                    existing.maturity_date = s["maturity"]
                    existing.issue_date = s["issue"]
                    session.add(existing)
                    session.commit()
                continue

            inst_obj = Instrument(
                institution_id=inst.id,
                region=reg,
                kind="FDR",
                ref_no=s["ref_no"],
                bank_code=s["bank"],
                ifsc=s["ifsc"],
                amount_paise=s["amount"],
                issue_date=s["issue"],
                maturity_date=s["maturity"],
                holders=[{"name": inst.name, "share": 100}],
                lien_marked=s["lien"],
                is_duplicate_receipt=False,
                lifecycle=s["lifecycle"],
                created_by=inst_user_id,
            )
            session.add(inst_obj)
            session.commit()
            session.refresh(inst_obj)
            inserted_count += 1

            # Audit log for submission
            audit(
                session,
                actor_id=inst_user_id,
                action="INSTRUMENT_SUBMIT",
                entity="instrument",
                entity_id=str(inst_obj.id),
                payload={
                    "ref_no": inst_obj.ref_no,
                    "bank_code": inst_obj.bank_code,
                    "amount_paise": inst_obj.amount_paise,
                },
            )

            # Confirmation if active / confirmed
            if s["confirmed"]:
                conf = Confirmation(
                    instrument_id=inst_obj.id,
                    status="confirmed",
                    method="signed_letter",
                    token_hash=f"token_{s['ref_no']}",
                    token_expires_at=datetime.now(UTC) + timedelta(days=30),
                    confirmed_at=datetime.now(UTC) - timedelta(days=10),
                    expires_at=datetime.now(UTC) + timedelta(days=3650),
                    fields={
                        "ref_no": inst_obj.ref_no,
                        "bank_code": inst_obj.bank_code,
                        "amount_paise": inst_obj.amount_paise,
                        "maturity_date": str(inst_obj.maturity_date),
                        "lien_marked": inst_obj.lien_marked,
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
                        "ref_no": inst_obj.ref_no,
                        "confirmed_amount_paise": inst_obj.amount_paise,
                        "status": "confirmed",
                    },
                )

            # Documents
            for doc_kind in s["docs"]:
                raw_hash = hashlib.sha256(
                    f"{inst_obj.ref_no}:{doc_kind}".encode()
                ).hexdigest()
                doc = Document(
                    instrument_id=inst_obj.id,
                    kind=doc_kind,
                    version=1,
                    filename=f"{doc_kind}_{inst_obj.ref_no}.pdf",
                    mime="application/pdf",
                    size_bytes=24576,
                    sha256=raw_hash,
                    storage_key=f"demo/{inst_obj.id}/{doc_kind}_v1.pdf",
                    uploaded_by=inst_user_id,
                )
                session.add(doc)
                session.commit()

            # Overdue obligation if configured
            if s["overdue_ob"]:
                ob = Obligation(
                    instrument_id=inst_obj.id,
                    kind=s["overdue_ob"]["kind"],
                    due_date=s["overdue_ob"]["due_date"],
                    status=s["overdue_ob"]["status"],
                    owner_role=s["overdue_ob"]["owner_role"],
                )
                session.add(ob)
                session.commit()

    return inserted_count


if __name__ == "__main__":
    seed_reports_topup()
