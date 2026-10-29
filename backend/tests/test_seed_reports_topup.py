"""Tests for Statement Reports Synthetic Seed Top-Up (S1).

Verifies:
1. Idempotency: Second run inserts 0 records.
2. Minimum counts: Each region (NR, WR) meets the required minimums across all 4 tabs.
3. RLS Isolation: NR sees zero WR records and WR sees zero NR records.
4. Audit Chain: Continues to verify clean after top-up and maturity worker execution.
5. Production safety: Top-up is a no-op under FASTAPI_ENV == 'production'.
"""

from datetime import date, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.db import init_db
from app.domain.clock import today as default_today
from app.domain.worker import run_daily_obligations_job
from app.models import Document, Instrument, Obligation
from app.seed_reports_topup import seed_reports_topup
from app.seed_rich_synthetic_data import seed_rich_data
from tests.utils.user import authentication_token_from_email


def test_seed_reports_topup_idempotency(db: Session) -> None:
    """Second run of seed_reports_topup must add 0 records."""
    init_db(db)
    seed_rich_data()
    first_run_added = seed_reports_topup(db)
    # Could be > 0 on first explicit run, or 0 if seed_rich_data already called it
    assert first_run_added >= 0

    second_run_added = seed_reports_topup(db)
    assert second_run_added == 0, "Second run must not insert any duplicate instruments"


def test_minimum_counts_per_region_per_tab(db: Session) -> None:
    """Each region with an officer persona must meet minimum synthetic record counts."""
    init_db(db)
    seed_rich_data()
    seed_reports_topup(db)
    today_val = default_today()

    for region in ("NR", "WR"):
        # 1. Pending Verifications: >= 3 records
        pending = db.exec(
            select(Instrument)
            .where(Instrument.region == region)
            .where(Instrument.lifecycle == "pending")
        ).all()
        assert len(pending) >= 3, f"{region} must have >= 3 pending instruments"

        # 2. Upcoming Maturities: >= 3 active instruments maturing in [0, 90] days
        cutoff = today_val + timedelta(days=90)
        upcoming = db.exec(
            select(Instrument)
            .where(Instrument.region == region)
            .where(Instrument.lifecycle == "active")
            .where(Instrument.maturity_date <= cutoff)
        ).all()
        assert len(upcoming) >= 3, f"{region} must have >= 3 upcoming maturity instruments"

        # 3. Missing Documents: >= 2 instruments missing fdr_scan or payment_proof
        active_or_pending = db.exec(
            select(Instrument)
            .where(Instrument.region == region)
            .where(col(Instrument.lifecycle).in_(["pending", "active"]))
        ).all()
        missing_count = 0
        for inst in active_or_pending:
            docs = db.exec(
                select(Document).where(Document.instrument_id == inst.id)
            ).all()
            kinds = {d.kind for d in docs}
            if "fdr_scan" not in kinds or "payment_proof" not in kinds:
                missing_count += 1
        assert missing_count >= 2, f"{region} must have >= 2 missing document cases"

        # 4. Cases Needing Intervention: >= 2 records (matured or overdue obligation)
        intervention_instruments = db.exec(
            select(Instrument)
            .where(Instrument.region == region)
            .where(col(Instrument.lifecycle).in_(["pending", "active", "matured"]))
        ).all()
        intervention_count = 0
        for inst in intervention_instruments:
            has_overdue_ob = db.exec(
                select(Obligation)
                .where(Obligation.instrument_id == inst.id)
                .where(Obligation.status == "open")
                .where(Obligation.due_date < today_val)
            ).first()
            if inst.lifecycle == "matured" or has_overdue_ob is not None:
                intervention_count += 1
        assert intervention_count >= 2, f"{region} must have >= 2 intervention cases"


def test_nr_and_wr_rls_isolation(client: TestClient, db: Session) -> None:
    """NR officer must see zero WR records, and WR officer must see zero NR records."""
    init_db(db)
    seed_rich_data()
    seed_reports_topup(db)

    nr_headers = authentication_token_from_email(
        client=client, email="officer.north@example.com", db=db
    )
    wr_headers = authentication_token_from_email(
        client=client, email="officer.west@example.com", db=db
    )

    endpoints = [
        f"{settings.API_V1_STR}/reports/pending-verifications/preview",
        f"{settings.API_V1_STR}/reports/upcoming-maturities/preview",
        f"{settings.API_V1_STR}/reports/missing-documents/preview",
        f"{settings.API_V1_STR}/reports/cases-needing-intervention/preview",
    ]

    for ep in endpoints:
        # NR check
        res_nr = client.get(ep, headers=nr_headers)
        assert res_nr.status_code == 200
        rows_nr = res_nr.json().get("rows", [])
        for row in rows_nr:
            assert row.get("region") == "NR", f"NR preview returned non-NR row: {row}"
            assert not str(row.get("ref_no", "")).startswith("SYN-REP-WR"), (
                f"NR officer saw WR synthetic record: {row['ref_no']}"
            )

        # WR check
        res_wr = client.get(ep, headers=wr_headers)
        assert res_wr.status_code == 200
        rows_wr = res_wr.json().get("rows", [])
        for row in rows_wr:
            assert row.get("region") == "WR", f"WR preview returned non-WR row: {row}"
            assert not str(row.get("ref_no", "")).startswith("SYN-REP-NR"), (
                f"WR officer saw NR synthetic record: {row['ref_no']}"
            )


def test_audit_chain_verifies_after_seed_and_maturity_worker(
    client: TestClient, db: Session
) -> None:
    """Cryptographic audit chain remains verified after reports top-up and maturity worker run."""
    init_db(db)
    seed_rich_data()
    seed_reports_topup(db)

    # Run maturity worker once
    worker_res = run_daily_obligations_job(db)
    assert worker_res.get("lock_acquired") is True

    # Verify audit chain with auditor credentials
    auditor_headers = authentication_token_from_email(
        client=client, email="auditor@example.com", db=db
    )
    r = client.get(f"{settings.API_V1_STR}/audit/verify", headers=auditor_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "clean"
    assert r.json()["tampered_event_id"] is None


def test_production_mode_does_not_run_topup(
    monkeypatch: Any, db: Session
) -> None:
    """Under FASTAPI_ENV=production, seed_reports_topup must immediately return 0 without inserting."""
    monkeypatch.setattr(settings, "FASTAPI_ENV", "production")
    added = seed_reports_topup(db)
    assert added == 0
