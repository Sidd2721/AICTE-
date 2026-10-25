#!/usr/bin/env bash
# Prerequisite doctor command wrapper (CHARTER R2)
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
    uv run python scripts/doctor.py
elif command -v python3 >/dev/null 2>&1; then
    python3 scripts/doctor.py
else
    python scripts/doctor.py
fi
