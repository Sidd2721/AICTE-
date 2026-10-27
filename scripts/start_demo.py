#!/usr/bin/env python3
"""AICTE FDR Portal — Single Cross-Platform Demo Launcher (Requirement 2.2).

Ensures database is running, applies migrations, loads judge scenario if empty,
ensures SPA bundle is ready, starts the FastAPI server, prints URLs/personas,
and opens /guide in the default browser.

Usage:
    uv run python scripts/start_demo.py [--port 8000] [--no-browser] [--no-launch]
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("start_demo")


def check_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a network port is listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def ensure_database_up() -> bool:
    """Ensure PostgreSQL is accessible on port 5432, starting container if needed."""
    logger.info("[1/5] Checking database connectivity on port 5432...")
    if check_port("127.0.0.1", 5432):
        logger.info("  -> Database is up and listening on port 5432.")
        return True

    # Try starting docker compose if docker is installed
    if shutil.which("docker"):
        logger.info("  -> Port 5432 not listening. Attempting 'docker compose up -d db'...")
        compose_files = [
            ROOT / "docker-compose.yml",
            ROOT / "deploy" / "docker-compose.demo.yml",
        ]
        target_compose = next((f for f in compose_files if f.exists()), None)
        if target_compose:
            subprocess.run(["docker", "compose", "-f", str(target_compose), "up", "-d", "db"], check=False)
            # Wait up to 15 seconds for DB port
            for _ in range(15):
                time.sleep(1)
                if check_port("127.0.0.1", 5432):
                    logger.info("  -> Database container successfully started on port 5432.")
                    return True

    logger.warning("  -> Database port 5432 is not accessible. Please ensure PostgreSQL is running.")
    return False


def run_migrations() -> None:
    """Apply Alembic migrations to head."""
    logger.info("[2/5] Running database migrations ('alembic upgrade head')...")
    res = subprocess.run(["uv", "run", "alembic", "upgrade", "head"], cwd=BACKEND, capture_output=True, text=True)
    if res.returncode != 0:
        logger.info(f"  -> Alembic output: {res.stdout.strip()} {res.stderr.strip()}")
    else:
        logger.info("  -> Database schema verified at head revision.")


def ensure_initial_scenario() -> None:
    """If database has 0 instruments, load the judge scenario automatically."""
    logger.info("[3/5] Checking database scenario state...")
    from sqlmodel import Session, func, select
    from app.core.db import engine, init_db
    from app.models import Instrument

    with Session(engine) as session:
        init_db(session)
        count = session.exec(select(func.count(Instrument.id))).one()

    if count == 0:
        logger.info("  -> Database is empty. Loading JUDGE scenario (7-step presentation story)...")
        subprocess.run(["uv", "run", "python", str(ROOT / "scripts" / "demo_data.py"), "load", "--scenario", "judge"], check=True)
    else:
        logger.info(f"  -> Database already populated with {count:,} instruments (reusing current state).")


def ensure_frontend_built() -> None:
    """Verify frontend/dist exists, or build it."""
    logger.info("[4/5] Checking compiled frontend SPA...")
    dist_index = FRONTEND / "dist" / "index.html"
    if dist_index.exists():
        logger.info(f"  -> Compiled SPA found at {dist_index} (reusing).")
        return

    logger.info("  -> dist/index.html not found. Building frontend bundle...")
    use_shell = sys.platform == "win32"
    if shutil.which("bun") or shutil.which("bun.cmd"):
        subprocess.run(["bun", "run", "build"], cwd=FRONTEND, check=True, shell=use_shell)
    elif shutil.which("npm") or shutil.which("npm.cmd"):
        subprocess.run(["npm", "run", "build"], cwd=FRONTEND, check=True, shell=use_shell)
    else:
        logger.warning("  -> Neither bun nor npm found. Please build frontend manually.")


def print_banner(port: int) -> None:
    """Print URLs and demo personas."""
    banner = f"""
================================================================================
 AICTE FIXED DEPOSIT RECEIPT & SECURITY DEPOSIT REGULATORY PORTAL (PS 26265)
================================================================================
 Prototype Status : DEMO • ALL BANK APIS SIMULATED • DATED APH 2024-27 RULES
 
 Live Application URLs:
   • Home / Dashboard : http://localhost:{port}/
   • 6-Minute Tour    : http://localhost:{port}/guide
   • Evidence & Gates : http://localhost:{port}/evidence
   • Integration API  : http://localhost:{port}/integrate
   • OpenAPI / Docs   : http://localhost:{port}/docs (development only)

 Verified Demonstration Personas (Password: 'changethis'):
   • Institution User   : inst.north1@example.com   (North Technical Institute)
   • Regional Officer   : officer.north@example.com (Maker - North Region)
   • Regional Checker   : checker.north@example.com (Regional Scrutiny)
   • AICTE Bureau Head  : bureau@example.com        (Checker - Dual-Custody Approval)
   • Regulatory Auditor : auditor@example.com       (Read-Only System Audit)
================================================================================
"""
    print(banner)


def main() -> int:
    parser = argparse.ArgumentParser(description="One-command demo launcher for AICTE FDR Portal")
    parser.add_argument("--port", type=int, default=8000, help="HTTP server port (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")
    parser.add_argument("--no-launch", action="store_true", help="Prepare DB and exit without starting uvicorn")
    args = parser.parse_args()

    ensure_database_up()
    run_migrations()
    ensure_initial_scenario()
    ensure_frontend_built()

    print_banner(args.port)

    guide_url = f"http://localhost:{args.port}/guide"
    if not args.no_browser and not args.no_launch:
        logger.info(f"Opening guided tour in default browser: {guide_url}")
        try:
            webbrowser.open(guide_url)
        except Exception:
            pass

    if args.no_launch:
        logger.info("[OK] System prepared successfully (--no-launch specified).")
        return 0

    logger.info(f"[5/5] Launching Uvicorn server on http://127.0.0.1:{args.port}...")
    cmd = [
        "uv", "run", "uvicorn", "app.main:app",
        "--host", "127.0.0.1",
        "--port", str(args.port),
        "--log-level", "info",
    ]
    try:
        subprocess.run(cmd, cwd=BACKEND, check=True)
    except KeyboardInterrupt:
        logger.info("\nDemo server stopped cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
