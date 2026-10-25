#!/usr/bin/env bash
# One-command demo bring-up for Bash / Linux / macOS / Git Bash (CHARTER R1, R8)
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
    uv run python scripts/run-demo.py "$@"
else
    python3 scripts/run-demo.py "$@"
fi
