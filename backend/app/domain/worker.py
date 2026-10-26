from datetime import date
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, col, select

from app.domain.clock import today as default_today
from app.models import Instrument, Notice, Obligation

OBLIGATIONS_ADVISORY_LOCK_ID = 847291


def run_daily_obligations_job(
    session: Session, current_date: date | None = None
) -> dict[str, Any]:
    """Execute the daily obligations check under a PostgreSQL advisory lock (Invariant I10)."""
    # Attempt to acquire advisory lock
    lock_result = session.execute(
        text("SELECT pg_try_advisory_lock(:lock_id)"),
        params={"lock_id": OBLIGATIONS_ADVISORY_LOCK_ID},
    ).scalar()

    if not lock_result:
        return {
            "lock_acquired": False,
            "reason": "Lock already held by another worker",
            "scanned_instruments": 0,
            "obligations_processed": 0,
            "notices_created": 0,
        }

    obligations_created = 0
    notices_created = 0
    target_date = current_date or default_today()

    try:
        instruments = session.exec(
            select(Instrument).where(
                col(Instrument.lifecycle).in_(["pending", "active", "matured"])
            )
        ).all()

        for inst in instruments:
            days_to_maturity = (inst.maturity_date - target_date).days

            # 1. Renewal due within 90 days
            if 0 <= days_to_maturity <= 90:
                existing_ob = session.exec(
                    select(Obligation).where(
                        Obligation.instrument_id == inst.id,
                        Obligation.kind == "renewal_due",
                        Obligation.due_date == inst.maturity_date,
                    )
                ).first()

                if not existing_ob:
                    ob = Obligation(
                        instrument_id=inst.id,
                        kind="renewal_due",
                        due_date=inst.maturity_date,
                        status="open",
                        owner_role="institution",
                    )
                    session.add(ob)
                    session.commit()
                    session.refresh(ob)
                    obligations_created += 1

                    # Send notice
                    notice = Notice(
                        instrument_id=inst.id,
                        obligation_id=ob.id,
                        step=f"expiring_{days_to_maturity}d",
                        channel="email",
                        delivered=True,
                    )
                    session.add(notice)
                    session.commit()
                    notices_created += 1

            # 2. Maturity reached
            elif days_to_maturity < 0:
                if inst.lifecycle == "active":
                    inst.lifecycle = "matured"
                    session.add(inst)

                existing_mat = session.exec(
                    select(Obligation).where(
                        Obligation.instrument_id == inst.id,
                        Obligation.kind == "maturity",
                        Obligation.due_date == inst.maturity_date,
                    )
                ).first()

                if not existing_mat:
                    mat_ob = Obligation(
                        instrument_id=inst.id,
                        kind="maturity",
                        due_date=inst.maturity_date,
                        status="open",
                        owner_role="regional",
                    )
                    session.add(mat_ob)
                    session.commit()
                    session.refresh(mat_ob)
                    obligations_created += 1

        session.commit()

        return {
            "lock_acquired": True,
            "scanned_instruments": len(instruments),
            "obligations_processed": obligations_created,
            "notices_created": notices_created,
        }

    finally:
        try:
            session.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                params={"lock_id": OBLIGATIONS_ADVISORY_LOCK_ID},
            )
            session.commit()
        except Exception:
            session.rollback()


def run_daily_worker(session: Session, today: date | None = None) -> dict[str, Any]:
    """Alias for running daily obligations check with optional target date."""
    return run_daily_obligations_job(session=session, current_date=today)
