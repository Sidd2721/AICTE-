#!/usr/bin/env python3
"""Measure representative PostgreSQL query latency in the current environment."""

import argparse
import statistics
import time

from app.core.db import engine
from app.core.rls_context import set_rls_context
from app.models import Instrument
from sqlalchemy import func
from sqlmodel import Session, select


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()
    if args.iterations < 2:
        raise SystemExit("--iterations must be at least 2")

    queries = {
        "instrument_list": select(Instrument.id).order_by(Instrument.id).limit(50),
        "dashboard_count": select(func.count()).select_from(Instrument),
        "needs_action": select(Instrument.id)
        .where(Instrument.lifecycle.in_(["pending", "active"]))
        .order_by(Instrument.maturity_date)
        .limit(50),
    }
    with Session(engine) as session:
        set_rls_context(session, role="bureau")
        for name, statement in queries.items():
            timings: list[float] = []
            for _ in range(args.iterations):
                started = time.perf_counter()
                session.exec(statement).all()
                timings.append((time.perf_counter() - started) * 1000)
            print(
                f"{name}: p50={statistics.median(timings):.2f} ms "
                f"p95={percentile(timings, 0.95):.2f} ms "
                f"n={len(timings)}"
            )


if __name__ == "__main__":
    main()
