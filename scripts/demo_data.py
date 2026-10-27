#!/usr/bin/env python3
"""AICTE FDR Portal — Demo Data Management & Scenario Controller (Phase 2).

Cross-platform script for managing demo scenarios, CSV imports/exports,
database resets, and table status reporting.

Usage:
    uv run python scripts/demo_data.py status
    uv run python scripts/demo_data.py load --scenario judge|rich|stress|empty
    uv run python scripts/demo_data.py reset
    uv run python scripts/demo_data.py import --dir data/ [--partial]
    uv run python scripts/demo_data.py export [--dir data/]
    uv run python scripts/demo_data.py schema
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import re
import sys
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

# Configure paths
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import text
from sqlmodel import Session, col, func, select

from app.core.audit import audit
from app.core.config import settings
from app.core.db import engine, init_db
from app.domain.clock import now
from app.models import (
    AuditCheckpoint,
    AuditEvent,
    CaseNote,
    Confirmation,
    Document,
    FlagWaiver,
    IdempotencyRecord,
    Institution,
    Instrument,
    MachineApiKey,
    Notice,
    Obligation,
    OutboxMessage,
    RateLimitBucket,
    ReleaseRequest,
    User,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("demo_data")

def get_db_name() -> str:
    """Extract database name from settings."""
    if hasattr(settings, "DATABASE_URL") and settings.DATABASE_URL.path:
        return settings.DATABASE_URL.path.lstrip("/")
    return "app"
JUDGE_INSTITUTION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
JUDGE_INSTRUMENT_1 = uuid.UUID("00000000-0000-0000-0001-000000000001")
JUDGE_INSTRUMENT_2 = uuid.UUID("00000000-0000-0000-0001-000000000002")
JUDGE_INSTRUMENT_3 = uuid.UUID("00000000-0000-0000-0001-000000000003")
JUDGE_INSTRUMENT_4 = uuid.UUID("00000000-0000-0000-0001-000000000004")
JUDGE_INSTRUMENT_5 = uuid.UUID("00000000-0000-0000-0001-000000000005")

JUDGE_CONFIRMATION_2 = uuid.UUID("00000000-0000-0000-0002-000000000002")
JUDGE_CONFIRMATION_3 = uuid.UUID("00000000-0000-0000-0002-000000000003")
JUDGE_CONFIRMATION_4 = uuid.UUID("00000000-0000-0000-0002-000000000004")
JUDGE_CONFIRMATION_5 = uuid.UUID("00000000-0000-0000-0002-000000000005")

JUDGE_RELEASE_4 = uuid.UUID("00000000-0000-0000-0003-000000000004")

IFSC_REGEX = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


# ==========================================
# Pydantic Schemas for CSV Validation
# ==========================================
class InstitutionCSVRow(BaseModel):
    permanent_id: str = Field(min_length=3, max_length=100)
    name: str = Field(min_length=3, max_length=255)
    region: str = Field(min_length=2, max_length=10)
    is_government: bool = False
    leased_private: bool = False
    programmes: list[dict[str, Any]] = Field(default_factory=list)
    contact_email: str | None = None

    @field_validator("is_government", "leased_private", mode="before")
    @classmethod
    def parse_bool(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "y")
        return bool(v)

    @field_validator("programmes", mode="before")
    @classmethod
    def parse_programmes(cls, v: Any) -> list[dict[str, Any]]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass
            # Comma-separated categories
            parts = [p.strip() for p in s.split(";") if p.strip()]
            return [{"category": p, "level": "UG"} for p in parts]
        return []


class InstrumentCSVRow(BaseModel):
    institution_permanent_id: str = Field(min_length=3, max_length=100)
    ref_no: str = Field(min_length=3, max_length=100)
    bank_code: str = Field(min_length=2, max_length=50)
    ifsc: str = Field(min_length=11, max_length=11)
    amount_paise: int = Field(gt=0)
    issue_date: date
    maturity_date: date
    kind: str = Field(default="FDR", max_length=20)
    lifecycle: str = Field(default="pending", max_length=30)
    lien_marked: bool = False

    @field_validator("ifsc")
    @classmethod
    def validate_ifsc(cls, v: str) -> str:
        v = v.strip().upper()
        if not IFSC_REGEX.match(v):
            raise ValueError(f"Invalid IFSC format '{v}'. Must match ^[A-Z]{{4}}0[A-Z0-9]{{6}}$")
        return v

    @field_validator("amount_paise", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> int:
        try:
            val = int(v)
            if val <= 0:
                raise ValueError("Amount in paise must be strictly positive (> 0)")
            return val
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid amount_paise '{v}': must be positive integer") from e

    @field_validator("lien_marked", mode="before")
    @classmethod
    def parse_lien(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "y")
        return bool(v)

    @field_validator("maturity_date")
    @classmethod
    def validate_dates(cls, v: date, info: Any) -> date:
        issue = info.data.get("issue_date")
        if issue and v < issue:
            raise ValueError(f"maturity_date ({v}) cannot precede issue_date ({issue})")
        return v


# ==========================================
# Database Table Helper Functions
# ==========================================
def get_table_counts(session: Session) -> dict[str, int]:
    """Retrieve row counts for all application models."""
    models = [
        ("user", User),
        ("institution", Institution),
        ("instrument", Instrument),
        ("confirmation", Confirmation),
        ("document", Document),
        ("obligation", Obligation),
        ("notice", Notice),
        ("case_note", CaseNote),
        ("flag_waiver", FlagWaiver),
        ("release_request", ReleaseRequest),
        ("audit_event", AuditEvent),
        ("audit_checkpoint", AuditCheckpoint),
        ("machine_api_key", MachineApiKey),
        ("outbox_message", OutboxMessage),
        ("idempotency_record", IdempotencyRecord),
    ]
    counts = {}
    for name, model in models:
        try:
            counts[name] = session.exec(select(func.count()).select_from(model)).one()
        except Exception:
            counts[name] = 0
    return counts


def detect_scenario(session: Session) -> str:
    """Infer current scenario name based on table counts and record signatures."""
    inst_count = session.exec(select(func.count(Instrument.id))).one()
    if inst_count == 0:
        return "empty"
    if inst_count == 2000:
        return "stress"
    if inst_count == 5:
        refs = session.exec(select(Instrument.ref_no)).all()
        if "FDR-B9-301" in refs and "FDR-B9-304" in refs:
            return "judge"
    if 10 <= inst_count <= 50:
        delhi = session.exec(select(Institution).where(Institution.permanent_id == "P-DELHI-ENG-01")).first()
        if delhi:
            return "rich"
    return "custom"


def print_status_table() -> None:
    """Display clean formatted status table."""
    with Session(engine) as session:
        counts = get_table_counts(session)
        scenario = detect_scenario(session)

    print("\n" + "=" * 55)
    print("      AICTE FDR PORTAL — DATABASE STATUS REPORT")
    print("=" * 55)
    print(f" Environment : {settings.FASTAPI_ENV.upper()}")
    print(f" Database    : {get_db_name()}")
    print(f" Scenario    : {scenario.upper()}")
    print("-" * 55)
    print(f" {'Table Name':<28} | {'Row Count':>15}")
    print("-" * 55)
    for table, count in counts.items():
        print(f" {table:<28} | {count:>15,}")
    print("=" * 55 + "\n")


# ==========================================
# Scenario Loaders
# ==========================================
def clear_scenario_data(session: Session) -> None:
    """Remove dependent scenario records while preserving users and audit chain."""
    session.exec(text("DELETE FROM release_request"))
    session.exec(text("DELETE FROM flag_waiver"))
    session.exec(text("DELETE FROM case_note"))
    session.exec(text("DELETE FROM notice"))
    session.exec(text("DELETE FROM obligation"))
    session.exec(text("DELETE FROM confirmation"))
    session.exec(text("DELETE FROM document"))
    session.exec(text("DELETE FROM instrument"))
    session.exec(text("DELETE FROM outbox_message"))
    session.exec(text("DELETE FROM idempotency_record"))
    session.commit()


def load_empty_scenario() -> None:
    """Reset to empty scenario: users and system rules only."""
    with Session(engine) as session:
        clear_scenario_data(session)
        session.exec(text('UPDATE "user" SET institution_id = NULL'))
        session.exec(text("DELETE FROM institution"))
        session.commit()
        init_db(session)
    logger.info("Loaded scenario: EMPTY (users + rules only; 0 instruments)")


def load_judge_scenario() -> None:
    """Load the deterministic 7-step story with fixed UUIDs and relative dates."""
    with Session(engine) as session:
        init_db(session)
        clear_scenario_data(session)

        # 1. Fetch Key Users
        inst_user = session.exec(select(User).where(User.email == "inst.north1@example.com")).first()
        ro_user = session.exec(select(User).where(User.email == "officer.north@example.com")).first()
        bureau_user = session.exec(select(User).where(User.email == "bureau@example.com")).first()

        fallback = session.exec(select(User)).first()
        inst_user_id = inst_user.id if inst_user else fallback.id
        ro_user_id = ro_user.id if ro_user else fallback.id
        bureau_user_id = bureau_user.id if bureau_user else fallback.id

        # 2. Institution: North Technical Institute
        inst = session.exec(select(Institution).where(Institution.permanent_id == "P-DELHI-ENG-01")).first()
        if not inst:
            inst = Institution(
                permanent_id="P-DELHI-ENG-01",
                name="North Technical Institute (Delhi Campus)",
                region="NR",
                is_government=False,
                leased_private=False,
                programmes=[{"category": "Engineering and Technology", "level": "UG"}],
                contact_email="inst.north1@example.com",
            )
            session.add(inst)
            session.commit()
            session.refresh(inst)
        else:
            inst.name = "North Technical Institute (Delhi Campus)"
            inst.region = "NR"
            inst.programmes = [{"category": "Engineering and Technology", "level": "UG"}]
            inst.contact_email = "inst.north1@example.com"
            session.add(inst)
            session.commit()
            session.refresh(inst)

        if inst_user and inst_user.institution_id != inst.id:
            inst_user.institution_id = inst.id
            session.add(inst_user)
            session.commit()

        cur_date = now().date()

        # Step 2: Submitted FDR (Claimed badge)
        ins1 = Instrument(
            id=JUDGE_INSTRUMENT_1,
            institution_id=inst.id,
            region="NR",
            kind="FDR",
            ref_no="FDR-B9-301",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=350000000,  # 35 Lakh
            issue_date=cur_date - timedelta(days=30),
            maturity_date=cur_date + timedelta(days=3620),
            lifecycle="pending",
            lien_marked=False,
            created_by=inst_user_id,
        )

        # Step 3: Confirmed FDR (SIMULATED bank confirmed)
        ins2 = Instrument(
            id=JUDGE_INSTRUMENT_2,
            institution_id=inst.id,
            region="NR",
            kind="FDR",
            ref_no="FDR-B9-302",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=350000000,
            issue_date=cur_date - timedelta(days=60),
            maturity_date=cur_date + timedelta(days=3590),
            lifecycle="active",
            lien_marked=True,
            created_by=inst_user_id,
        )

        # Step 4: Discrepancy Case (Bank reports 25L vs Claimed 35L -> 10L Mismatch)
        ins3 = Instrument(
            id=JUDGE_INSTRUMENT_3,
            institution_id=inst.id,
            region="NR",
            kind="FDR",
            ref_no="FDR-B9-303",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=350000000,
            issue_date=cur_date - timedelta(days=45),
            maturity_date=cur_date + timedelta(days=3605),
            lifecycle="pending",
            lien_marked=False,
            created_by=inst_user_id,
        )

        # Step 5: Dual-Custody Release (Matured 10 years, RO verified, waiting for Bureau approval)
        ins4 = Instrument(
            id=JUDGE_INSTRUMENT_4,
            institution_id=inst.id,
            region="NR",
            kind="FDR",
            ref_no="FDR-B9-304",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=350000000,
            issue_date=cur_date - timedelta(days=3653),
            maturity_date=cur_date - timedelta(days=3),
            lifecycle="matured",
            lien_marked=True,
            created_by=inst_user_id,
        )

        # Step 6: Renewal Replacement Instrument
        ins5 = Instrument(
            id=JUDGE_INSTRUMENT_5,
            institution_id=inst.id,
            region="NR",
            kind="FDR",
            ref_no="FDR-B9-305",
            bank_code="SBIN",
            ifsc="SBIN0001234",
            amount_paise=350000000,
            issue_date=cur_date - timedelta(days=10),
            maturity_date=cur_date + timedelta(days=3640),
            lifecycle="active",
            lien_marked=True,
            replaces_id=JUDGE_INSTRUMENT_4,
            created_by=inst_user_id,
        )

        # Flush instruments first
        session.add_all([ins1, ins2, ins3, ins4, ins5])
        session.flush()

        conf2 = Confirmation(
            id=JUDGE_CONFIRMATION_2,
            instrument_id=JUDGE_INSTRUMENT_2,
            status="confirmed",
            method="signed_letter",
            token_hash="judge_token_hash_step3",
            token_expires_at=now() + timedelta(days=14),
            confirmed_at=now() - timedelta(days=58),
            expires_at=now() + timedelta(days=365),
            fields={
                "ref_no": "FDR-B9-302",
                "bank_code": "SBIN",
                "amount_paise": 350000000,
                "maturity_date": str(cur_date + timedelta(days=3590)),
                "lien_marked": True,
            },
        )
        conf3 = Confirmation(
            id=JUDGE_CONFIRMATION_3,
            instrument_id=JUDGE_INSTRUMENT_3,
            status="confirmed",
            method="signed_letter",
            token_hash="judge_token_hash_step4",
            token_expires_at=now() + timedelta(days=14),
            confirmed_at=now() - timedelta(days=40),
            expires_at=now() + timedelta(days=365),
            fields={
                "ref_no": "FDR-B9-303",
                "bank_code": "SBIN",
                "amount_paise": 250000000,  # 25L (10L Discrepancy)
                "maturity_date": str(cur_date + timedelta(days=3605)),
                "lien_marked": True,
            },
        )
        conf4 = Confirmation(
            id=JUDGE_CONFIRMATION_4,
            instrument_id=JUDGE_INSTRUMENT_4,
            status="confirmed",
            method="signed_letter",
            token_hash="judge_token_hash_step5",
            token_expires_at=now() + timedelta(days=14),
            confirmed_at=now() - timedelta(days=3600),
            expires_at=now() + timedelta(days=365),
            fields={
                "ref_no": "FDR-B9-304",
                "bank_code": "SBIN",
                "amount_paise": 350000000,
                "maturity_date": str(cur_date - timedelta(days=3)),
                "lien_marked": True,
            },
        )
        rel4 = ReleaseRequest(
            id=JUDGE_RELEASE_4,
            instrument_id=JUDGE_INSTRUMENT_4,
            path="term_completion",
            status="verified",  # RO verified; ready for Bureau approve
            requested_by=inst_user_id,
            verified_by=ro_user_id,
            approved_by=None,
        )
        conf5 = Confirmation(
            id=JUDGE_CONFIRMATION_5,
            instrument_id=JUDGE_INSTRUMENT_5,
            status="confirmed",
            method="signed_letter",
            token_hash="judge_token_hash_step6",
            token_expires_at=now() + timedelta(days=14),
            confirmed_at=now() - timedelta(days=5),
            expires_at=now() + timedelta(days=365),
            fields={
                "ref_no": "FDR-B9-305",
                "bank_code": "SBIN",
                "amount_paise": 350000000,
                "maturity_date": str(cur_date + timedelta(days=3640)),
                "lien_marked": True,
            },
        )
        session.add_all([conf2, conf3, conf4, rel4, conf5])
        session.commit()

        # Audit events for judge scenario
        for ins in [ins1, ins2, ins3, ins4, ins5]:
            audit(
                session,
                actor_id=inst_user_id,
                action="instrument.submitted",
                entity="instrument",
                entity_id=str(ins.id),
                payload={"ref_no": ins.ref_no, "scenario": "judge"},
            )

    logger.info("Loaded scenario: JUDGE (5 fixed-UUID instruments for 7-step presentation)")


def load_rich_scenario() -> None:
    """Load the comprehensive rich seed (11 institutions / 18+ instruments)."""
    from app.seed_rich_synthetic_data import seed_rich_data

    with Session(engine) as session:
        clear_scenario_data(session)
    seed_rich_data()
    logger.info("Loaded scenario: RICH (11 institutions, 18+ instruments, waivers, and notices)")


def load_stress_scenario() -> None:
    """Load stress dataset: 2,000 instruments / 60 institutions / 4 regions (seeded deterministically)."""
    start_t = time.time()
    random.seed(42)  # Deterministic seed

    regions = ["NR", "WR", "SR", "ER"]
    banks = ["SBIN", "PNBB", "HDFC", "ICIC", "CANB"]
    amounts = [150000000, 350000000, 500000000, 700000000]

    with Session(engine) as session:
        init_db(session)
        clear_scenario_data(session)

        # 1. Fetch or create admin creator
        creator = session.exec(select(User).where(User.is_superuser == True)).first()
        creator_id = creator.id if creator else uuid.uuid4()

        # 2. Generate 60 Institutions
        institutions: list[Institution] = []
        for i in range(1, 61):
            reg = regions[(i - 1) % len(regions)]
            perm_id = f"P-STR-{reg}-{i:03d}"
            inst = session.exec(select(Institution).where(Institution.permanent_id == perm_id)).first()
            if not inst:
                inst = Institution(
                    permanent_id=perm_id,
                    name=f"Stress Academic Institute {i:03d} ({reg})",
                    region=reg,
                    is_government=(i % 5 == 0),
                    leased_private=(i % 3 == 0),
                    programmes=[{"category": "Engineering and Technology", "level": "UG"}],
                )
                session.add(inst)
            institutions.append(inst)
        session.commit()
        for inst in institutions:
            session.refresh(inst)

        # 3. Generate 2,000 Instruments
        cur_date = date.today()
        instruments: list[Instrument] = []
        for i in range(1, 2001):
            inst = institutions[(i - 1) % len(institutions)]
            bank = banks[i % len(banks)]
            amt = amounts[i % len(amounts)]
            days_offset = (i * 7) % 3000
            issue_d = cur_date - timedelta(days=days_offset)
            maturity_d = issue_d + timedelta(days=3650)
            is_matured = maturity_d < cur_date

            ins = Instrument(
                institution_id=inst.id,
                region=inst.region,
                kind="FDR",
                ref_no=f"FDR-STR-{i:04d}",
                bank_code=bank,
                ifsc=f"{bank}000{1000 + (i % 800):04d}",
                amount_paise=amt,
                issue_date=issue_d,
                maturity_date=maturity_d,
                lifecycle="matured" if is_matured else "active",
                lien_marked=True,
                created_by=creator_id,
            )
            instruments.append(ins)

        # Batch insert
        session.bulk_save_objects(instruments)
        session.commit()

    elapsed = time.time() - start_t
    logger.info(f"Loaded scenario: STRESS (2,000 instruments / 60 institutions) in {elapsed:.2f}s")


# ==========================================
# Database Reset Controller
# ==========================================
def reset_database() -> None:
    """Drop and recreate schema public, run migrations, and load default judge scenario."""
    env = settings.FASTAPI_ENV.lower()
    if env not in ("development", "demo"):
        sys.exit(f"FATAL: Database reset refused. FASTAPI_ENV is '{env}' (allowed: development, demo)")

    db_name = get_db_name().lower()
    allowlist = ("app", "postgres", "aicte_fdr", "test_app", "aicte_test")
    if db_name not in allowlist:
        sys.exit(f"FATAL: Database reset refused. Database '{db_name}' is not in allowlist {allowlist}")

    logger.info(f"[RESET] Resetting database '{db_name}' in environment '{env}'...")

    # Drop and recreate schema public
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"))
        conn.commit()

    # Run alembic migrations
    logger.info("[RESET] Running Alembic migrations to head...")
    import subprocess
    res = subprocess.run(["uv", "run", "alembic", "upgrade", "head"], cwd=BACKEND, capture_output=True, text=True)
    if res.returncode != 0:
        # Fallback if alembic executable is invoked differently
        from alembic import command
        from alembic.config import Config
        cfg = Config(str(BACKEND / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND / "app" / "alembic"))
        command.upgrade(cfg, "head")

    # Load default scenario
    load_judge_scenario()
    logger.info("[OK] Database reset complete! Migration at head, scenario JUDGE loaded.")


# ==========================================
# CSV Import / Export / Schema
# ==========================================
def import_csv_data(data_dir: Path, partial: bool = False) -> None:
    """Import institutions.csv and instruments.csv with strict Pydantic validation."""
    inst_file = data_dir / "institutions.csv"
    instr_file = data_dir / "instruments.csv"

    if not inst_file.exists():
        sys.exit(f"File not found: {inst_file}")
    if not instr_file.exists():
        sys.exit(f"File not found: {instr_file}")

    errors: list[dict[str, Any]] = []

    # 1. Parse Institutions
    valid_inst_rows: list[InstitutionCSVRow] = []
    with open(inst_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            try:
                valid_inst_rows.append(InstitutionCSVRow(**row))
            except ValidationError as ve:
                for err in ve.errors():
                    errors.append({
                        "file": "institutions.csv",
                        "line": idx,
                        "field": ".".join(str(loc) for loc in err["loc"]),
                        "message": err["msg"],
                    })

    # 2. Parse Instruments
    valid_instr_rows: list[InstrumentCSVRow] = []
    with open(instr_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            try:
                valid_instr_rows.append(InstrumentCSVRow(**row))
            except ValidationError as ve:
                for err in ve.errors():
                    errors.append({
                        "file": "instruments.csv",
                        "line": idx,
                        "field": ".".join(str(loc) for loc in err["loc"]),
                        "message": err["msg"],
                    })

    # If errors and not partial, abort
    if errors and not partial:
        print("\n" + "!" * 65)
        print(" CSV IMPORT VALIDATION FAILED (ALL-OR-NOTHING)")
        print("!" * 65)
        for e in errors:
            print(f" [{e['file']}:L{e['line']}] Field '{e['field']}': {e['message']}")
        print("!" * 65)
        sys.exit(1)

    # 3. Apply to Database with Cross-Institution Duplicate Reference Defense
    with Session(engine) as session:
        # Pre-fetch existing permanent IDs & instrument refs
        inst_id_map: dict[str, uuid.UUID] = {}
        for inst in session.exec(select(Institution)).all():
            inst_id_map[inst.permanent_id] = inst.id

        # Upsert Institutions
        imported_insts = 0
        for row in valid_inst_rows:
            inst_obj = session.exec(select(Institution).where(Institution.permanent_id == row.permanent_id)).first()
            if not inst_obj:
                inst_obj = Institution(
                    permanent_id=row.permanent_id,
                    name=row.name,
                    region=row.region,
                    is_government=row.is_government,
                    leased_private=row.leased_private,
                    programmes=row.programmes,
                    contact_email=row.contact_email,
                )
                session.add(inst_obj)
                session.flush()
                imported_insts += 1
            inst_id_map[row.permanent_id] = inst_obj.id

        # Insert Instruments
        imported_instrs = 0
        admin = session.exec(select(User).where(User.is_superuser == True)).first()
        admin_id = admin.id if admin else uuid.uuid4()

        seen_refs_in_batch: dict[str, str] = {}  # ref_no -> permanent_id

        for idx, row in enumerate(valid_instr_rows, start=2):
            target_inst_id = inst_id_map.get(row.institution_permanent_id)
            if not target_inst_id:
                err_msg = f"Unknown institution '{row.institution_permanent_id}'"
                if not partial:
                    session.rollback()
                    sys.exit(f"Import error at instruments.csv:L{idx}: {err_msg}")
                continue

            # Cross-Institution Duplicate Ref Check (Invariant Defense)
            # Check DB
            existing_ins = session.exec(select(Instrument).where(Instrument.ref_no == row.ref_no)).first()
            if existing_ins and existing_ins.institution_id != target_inst_id:
                err_msg = f"Duplicate reference number across institutions: {row.ref_no}"
                if not partial:
                    session.rollback()
                    sys.exit(f"Security error at instruments.csv:L{idx}: {err_msg}")
                continue

            # Check batch
            if row.ref_no in seen_refs_in_batch and seen_refs_in_batch[row.ref_no] != row.institution_permanent_id:
                err_msg = f"Duplicate reference number across institutions: {row.ref_no}"
                if not partial:
                    session.rollback()
                    sys.exit(f"Security error at instruments.csv:L{idx}: {err_msg}")
                continue
            seen_refs_in_batch[row.ref_no] = row.institution_permanent_id

            if not existing_ins:
                new_ins = Instrument(
                    institution_id=target_inst_id,
                    region=row.ifsc[:2],  # default or mapped
                    kind=row.kind,
                    ref_no=row.ref_no,
                    bank_code=row.bank_code,
                    ifsc=row.ifsc,
                    amount_paise=row.amount_paise,
                    issue_date=row.issue_date,
                    maturity_date=row.maturity_date,
                    lifecycle=row.lifecycle,
                    lien_marked=row.lien_marked,
                    created_by=admin_id,
                )
                session.add(new_ins)
                session.flush()
                audit(
                    session,
                    actor_id=admin_id,
                    action="instrument.csv_imported",
                    entity="instrument",
                    entity_id=str(new_ins.id),
                    payload={"ref_no": row.ref_no, "source": "demo_data_import"},
                )
                imported_instrs += 1

        session.commit()

    logger.info(f"[OK] CSV Import successful: {imported_insts} institutions, {imported_instrs} instruments imported.")


def export_csv_data(data_dir: Path) -> None:
    """Export current institution and instrument tables to CSV files."""
    data_dir.mkdir(parents=True, exist_ok=True)
    inst_file = data_dir / "institutions.csv"
    instr_file = data_dir / "instruments.csv"

    with Session(engine) as session:
        institutions = session.exec(select(Institution)).all()
        instruments = session.exec(select(Instrument)).all()

        inst_perm_map = {inst.id: inst.permanent_id for inst in institutions}

        # Export Institutions
        with open(inst_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["permanent_id", "name", "region", "is_government", "leased_private", "programmes", "contact_email"])
            for inst in institutions:
                writer.writerow([
                    inst.permanent_id,
                    inst.name,
                    inst.region,
                    inst.is_government,
                    inst.leased_private,
                    json.dumps(inst.programmes),
                    inst.contact_email or "",
                ])

        # Export Instruments
        with open(instr_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["institution_permanent_id", "ref_no", "bank_code", "ifsc", "amount_paise", "issue_date", "maturity_date", "kind", "lifecycle", "lien_marked"])
            for ins in instruments:
                perm_id = inst_perm_map.get(ins.institution_id, "UNKNOWN")
                writer.writerow([
                    perm_id,
                    ins.ref_no,
                    ins.bank_code,
                    ins.ifsc,
                    ins.amount_paise,
                    ins.issue_date.isoformat(),
                    ins.maturity_date.isoformat(),
                    ins.kind,
                    ins.lifecycle,
                    ins.lien_marked,
                ])

    logger.info(f"[OK] Exported {len(institutions)} institutions -> {inst_file}")
    logger.info(f"[OK] Exported {len(instruments)} instruments -> {instr_file}")


def print_csv_schema() -> None:
    """Print documentation on expected CSV columns and schema."""
    schema_doc = """
================================================================================
 AICTE FDR PORTAL — CSV IMPORT / EXPORT SPECIFICATIONS
================================================================================

1. institutions.csv
--------------------------------------------------------------------------------
 Column          Type     Required  Description & Example
 permanent_id    String   YES       Unique AICTE institute ID (e.g. 'P-DELHI-ENG-01')
 name            String   YES       Full legal name of the institution
 region          String   YES       AICTE Region code: NR, WR, SR, ER, CR, NW, SC
 is_government   Boolean  NO        true/false (Central/State government exemption)
 leased_private  Boolean  NO        true/false (Private leased land 2x multiplier)
 programmes      JSON     NO        [{"category": "Engineering and Technology", "level": "UG"}]
 contact_email   String   NO        Email for statutory notices

2. instruments.csv
--------------------------------------------------------------------------------
 Column                   Type     Required  Description & Example
 institution_permanent_id String   YES       Foreign key matching institutions.csv
 ref_no                   String   YES       FDR receipt / reference number
 bank_code                String   YES       4-letter bank code (e.g. 'SBIN', 'PNBB')
 ifsc                     String   YES       11-character Indian Financial System Code
 amount_paise             Integer  YES       Deposit amount in exact integer paise (> 0)
                                            (1 Lakh = 10,000,000 paise; 35 Lakh = 350,000,000)
 issue_date               Date     YES       Format YYYY-MM-DD (e.g. '2024-01-15')
 maturity_date            Date     YES       Format YYYY-MM-DD (e.g. '2034-01-15')
 kind                     String   NO        'FDR' or 'RTGS' (Default: FDR)
 lifecycle                String   NO        pending | active | matured | renewed | released
 lien_marked              Boolean  NO        true/false (Joint lien marked with AICTE)
================================================================================
"""
    print(schema_doc)


# ==========================================
# Main CLI Entrypoint
# ==========================================
def main() -> int:
    parser = argparse.ArgumentParser(description="AICTE FDR Portal — Demo Data Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser("status", help="Print live counts for all tables and current scenario")

    # load
    load_parser = subparsers.add_parser("load", help="Load a pre-configured synthetic scenario")
    load_parser.add_argument("--scenario", choices=["judge", "rich", "stress", "empty"], required=True)

    # reset
    subparsers.add_parser("reset", help="Reset DB to pristine state, migrate, and load judge scenario")

    # import
    import_parser = subparsers.add_parser("import", help="Import data from CSV files")
    import_parser.add_argument("--dir", type=Path, default=ROOT / "data", help="Directory containing CSV files")
    import_parser.add_argument("--partial", action="store_true", help="Continue importing valid rows on errors")

    # export
    export_parser = subparsers.add_parser("export", help="Export database to CSV files")
    export_parser.add_argument("--dir", type=Path, default=ROOT / "data", help="Target directory for export")

    # schema
    subparsers.add_parser("schema", help="Print CSV column schema specifications")

    args = parser.parse_args()

    if args.command == "status":
        print_status_table()
    elif args.command == "load":
        if args.scenario == "judge":
            load_judge_scenario()
        elif args.scenario == "rich":
            load_rich_scenario()
        elif args.scenario == "stress":
            load_stress_scenario()
        elif args.scenario == "empty":
            load_empty_scenario()
        print_status_table()
    elif args.command == "reset":
        reset_database()
        print_status_table()
    elif args.command == "import":
        import_csv_data(args.dir, partial=args.partial)
        print_status_table()
    elif args.command == "export":
        export_csv_data(args.dir)
    elif args.command == "schema":
        print_csv_schema()

    return 0


if __name__ == "__main__":
    sys.exit(main())
