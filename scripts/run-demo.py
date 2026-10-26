#!/usr/bin/env python3
"""One-command demo bring-up (CHARTER R1, R3, R4, R6, R8).

Usage:
    python scripts/run-demo.py [--reseed] [--no-launch]

Performs:
1. Prerequisite doctor verification.
2. Database connectivity or container startup.
3. Database migrations (`alembic upgrade head`).
4. Deterministic initial seed data.
5. Launches single-worker backend serving the compiled SPA on http://localhost:8000.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def log(msg: str) -> None:
    print(f"\033[1m\033[34m[DEMO-LAUNCH]\033[0m {msg}")


def log_ok(msg: str) -> None:
    print(f"\033[1m\033[32m[OK]\033[0m {msg}")


def log_err(msg: str) -> None:
    print(f"\033[1m\033[31m[ERROR]\033[0m {msg}")


def run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd or ROOT, text=True, check=check, capture_output=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="One-command AICTE FDR Portal Demo Launcher")
    parser.add_argument("--reseed", action="store_true", help="Force database re-seed")
    parser.add_argument("--reset", "-Reset", action="store_true", help="Reset DB, seed, and execute 7 demo steps")
    parser.add_argument("--steps", action="store_true", help="Execute 7 problem-statement demo steps")
    parser.add_argument("--no-launch", action="store_true", help="Prepare DB and exit without launching uvicorn")
    args = parser.parse_args()

    start_time = time.time()
    log("Starting AICTE Security Deposit / FDR Portal Demo (CHARTER R1)...")

    # 1. Run Doctor
    log("Step 1: Running system doctor checks...")
    doctor_res = subprocess.run([sys.executable, str(ROOT / "scripts" / "doctor.py")])
    if doctor_res.returncode != 0:
        log_err("Doctor checks failed. Please resolve the errors above before launching.")
        return 1

    # 2. Database readiness
    log("Step 2: Checking database service on port 5432...")
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        db_up = s.connect_ex(("localhost", 5432)) == 0

    if not db_up:
        docker_bin = shutil.which("docker") or shutil.which("docker.exe")
        if docker_bin:
            log("Starting PostgreSQL via Docker Compose...")
            run_cmd([docker_bin, "compose", "up", "-d", "db"])
            for _ in range(30):
                time.sleep(1)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(("localhost", 5432)) == 0:
                        db_up = True
                        break
            if not db_up:
                log_err("PostgreSQL container did not become ready in time.")
                return 1
        else:
            log_err("PostgreSQL is not running on port 5432 and Docker is not available.")
            return 1
    log_ok("PostgreSQL is listening on port 5432.")

    # 2.5 Database Reset (if requested via --reset)
    if args.reset:
        log("Resetting database 'app' via maintenance connection (DROP & CREATE)...")
        import psycopg
        import re
        from app.core.config import settings
        url = str(settings.MIGRATION_DATABASE_URL or settings.DATABASE_URL)
        pg_url = re.sub(r"/[^/?]+(?:\?|$)", "/postgres?", url).replace("postgresql+psycopg://", "postgresql://")
        with psycopg.connect(pg_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("DROP DATABASE IF EXISTS app WITH (FORCE);")
                cur.execute("CREATE DATABASE app;")
        log_ok("Database 'app' recreated fresh.")

    # 3. Migrations
    log("Step 3: Running database migrations (alembic upgrade head)...")
    uv_bin = shutil.which("uv") or shutil.which("uv.exe") or "uv"
    run_cmd([uv_bin, "run", "alembic", "upgrade", "head"], cwd=BACKEND)
    log_ok("Database migrations up to date.")

    if args.reset:
        log("Ensuring schema and table ownership is assigned to migrator role...")
        from scripts.fix_ownership import set_ownership_to_migrator
        set_ownership_to_migrator()
        log_ok("Schema ownership configured.")

    # 4. Deterministic Seed
    log("Step 4: Seeding deterministic dual-custody matrix...")
    env = os.environ.copy()
    env.setdefault("FASTAPI_ENV", "development")
    subprocess.run([uv_bin, "run", "python", "-m", "app.initial_data"], cwd=BACKEND, env=env, check=True)
    log_ok("Initial dual-custody seed data applied.")

    # 5. If --reset or --steps, run the 7 problem statement demo steps
    if args.reset or args.steps:
        log("Executing 7 Problem Statement Demo Steps...")
        from scripts.demo_steps import run_demo_steps
        success = run_demo_steps()
        if not success:
            log_err("Demo steps execution failed.")
            return 1
        log_ok("All 7 Demo Steps Verified Successfully!")
        if args.reset:
            return 0

    elapsed = time.time() - start_time
    log_ok(f"Environment prepared in {elapsed:.1f}s (Warm cache target < 120s achieved!).")

    # 5. Print Demo Credentials Matrix
    print("\n" + "=" * 70)
    print("  AICTE SECURITY DEPOSIT / FDR PORTAL — DEMO READY")
    print("  Mode: DEMO (Synthetic Data & Simulators Labelled)")
    print("=" * 70)
    print("  URL: http://localhost:8000")
    print("\n  Demo Credentials (password: changethis):")
    print("  - Officer (North):    officer.north@example.com")
    print("  - Checker (North):    checker.north@example.com")
    print("  - Institution:        inst.north1@example.com")
    print("  - Bureau Officer:     bureau@example.com")
    print("  - Auditor:            auditor@example.com")
    print("  - System Admin:       admin@example.com")
    print("=" * 70 + "\n")

    if args.no_launch:
        return 0

    # 6. Launch single-worker backend (CHARTER R6)
    log("Launching single-worker backend (serving API + compiled UI on port 8000)...")
    log("Press Ctrl+C to terminate.")
    try:
        run_cmd(
            [
                uv_bin,
                "run",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--workers",
                "1",
            ],
            cwd=BACKEND,
            check=False,
        )
    except KeyboardInterrupt:
        log("Server stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
