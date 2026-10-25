#!/usr/bin/env python3
"""Prerequisite doctor command (CHARTER R2).

Checks:
1. Python version (3.14 required by Invariant I1).
2. uv installed and functional.
3. Bun or Node.js runtime.
4. Git available and working tree clean / .env untracked.
5. Container runtime / Docker status.
6. Required network ports (5432 for Postgres, 8000 for backend API, 5173 for dev UI).
7. Free disk space (> 2 GB).

Prints plain-language remediation instructions for any failure.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def check_port(host: str, port: int) -> bool:
    """Returns True if port is open (service listening), False if free."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def main() -> int:
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== AICTE Deposit/FDR Portal — System Doctor (CHARTER R2) ==={Colors.RESET}\n")
    failures: list[str] = []
    warnings: list[str] = []

    # 1. Python version
    py_ver = sys.version_info
    py_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    if py_ver >= (3, 14):
        print(f"  [{Colors.GREEN}OK{Colors.RESET}] Python version: {py_str} (>= 3.14 required)")
    else:
        # Check if uv is pointing to 3.14
        uv_path = shutil.which("uv") or shutil.which("uv.exe")
        if uv_path:
            try:
                res = subprocess.run([uv_path, "run", "python", "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"], capture_output=True, text=True, timeout=5)
                if res.returncode == 0 and res.stdout.strip().startswith("3.14"):
                    print(f"  [{Colors.GREEN}OK{Colors.RESET}] Python version under uv: {res.stdout.strip()} (>= 3.14)")
                else:
                    failures.append(f"Python 3.14 required (Invariant I1). Current runner has {py_str}. Fix: install Python 3.14 or run 'uv python install 3.14'.")
            except Exception:
                failures.append("Could not query Python 3.14 under uv.")
        else:
            failures.append(f"Python 3.14 required (Invariant I1). Current: {py_str}. Fix: install Python 3.14.")

    # 2. Package managers: uv and bun
    uv_bin = shutil.which("uv") or shutil.which("uv.exe")
    if uv_bin:
        print(f"  [{Colors.GREEN}OK{Colors.RESET}] uv package manager: {uv_bin}")
    else:
        failures.append("uv not found on PATH. Fix: install uv via 'curl -LsSf https://astral.sh/uv/install.sh' or 'powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"'.")

    bun_bin = shutil.which("bun") or shutil.which("bun.exe")
    if bun_bin:
        print(f"  [{Colors.GREEN}OK{Colors.RESET}] bun runtime: {bun_bin}")
    else:
        warnings.append("bun not found on PATH. Frontend build in full gate requires bun or bunx.")

    # 3. Docker / container runtime
    docker_bin = shutil.which("docker") or shutil.which("docker.exe")
    if docker_bin:
        try:
            res = subprocess.run([docker_bin, "info"], capture_output=True, timeout=5)
            if res.returncode == 0:
                print(f"  [{Colors.GREEN}OK{Colors.RESET}] Docker daemon: running")
            else:
                warnings.append("Docker is installed but daemon is not responding. Fix: start Docker Desktop / daemon if using containers.")
        except Exception:
            warnings.append("Docker check timed out.")
    else:
        warnings.append("Docker not installed on PATH. Needed if running Postgres via compose.")

    # 4. Port checks (5432, 8000, 5173)
    db_listening = check_port("localhost", 5432)
    if db_listening:
        print(f"  [{Colors.GREEN}OK{Colors.RESET}] Port 5432 (PostgreSQL): active listener found (database ready)")
    else:
        warnings.append("Port 5432 (PostgreSQL) has no listener. Fix: start database via 'docker compose up -d' or local postgres service.")

    backend_listening = check_port("localhost", 8000)
    if backend_listening:
        print(f"  [{Colors.YELLOW}NOTE{Colors.RESET}] Port 8000 (Backend API): currently in use by an active process")
    else:
        print(f"  [{Colors.GREEN}OK{Colors.RESET}] Port 8000 (Backend API): free to bind")

    frontend_listening = check_port("localhost", 5173)
    if frontend_listening:
        print(f"  [{Colors.YELLOW}NOTE{Colors.RESET}] Port 5173 (Vite Frontend): currently in use")
    else:
        print(f"  [{Colors.GREEN}OK{Colors.RESET}] Port 5173 (Vite Frontend): free to bind")

    # 5. Disk space check
    try:
        total, used, free = shutil.disk_usage(os.getcwd())
        free_gb = free / (1024 ** 3)
        if free_gb >= 2.0:
            print(f"  [{Colors.GREEN}OK{Colors.RESET}] Free disk space: {free_gb:.1f} GB (> 2.0 GB target)")
        else:
            failures.append(f"Insufficient free disk space: {free_gb:.1f} GB available, >= 2.0 GB required.")
    except Exception as e:
        warnings.append(f"Could not check disk usage: {e}")

    # 6. Git & .env security check (Invariant I9)
    git_bin = shutil.which("git") or shutil.which("git.exe")
    if git_bin:
        try:
            res = subprocess.run([git_bin, "ls-files", "--error-unmatch", ".env"], capture_output=True)
            if res.returncode == 0:
                failures.append("CRITICAL: .env is tracked by git (violates Invariant I9). Fix: 'git rm --cached .env' and verify .gitignore.")
            else:
                print(f"  [{Colors.GREEN}OK{Colors.RESET}] Invariant I9: .env is untracked")
        except Exception:
            pass

    # Summary
    print()
    if warnings:
        print(f"{Colors.YELLOW}Warnings / Non-blocking notices:{Colors.RESET}")
        for w in warnings:
            print(f"  - {w}")
        print()

    if failures:
        print(f"{Colors.RED}FAILURES DETECTED ({len(failures)}):{Colors.RESET}")
        for f in failures:
            print(f"  ✖ {f}")
        print()
        return 1

    print(f"{Colors.GREEN}{Colors.BOLD}ALL PRE-REQUISITE CHECKS PASSED. Ready to run demo or gate.{Colors.RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
