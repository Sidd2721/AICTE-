#!/usr/bin/env bash

set -e
set -x

# Ensure virtualenv binaries are on PATH under Windows bash
[ -d ".venv/Scripts" ] && export PATH="$PWD/.venv/Scripts:$PATH"
[ -d "../.venv/Scripts" ] && export PATH="$(cd .. && pwd)/.venv/Scripts:$PATH"

if [ -f "../.venv/Scripts/python.exe" ]; then
    PYTHON="../.venv/Scripts/python.exe"
elif [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python"
fi

"$PYTHON" -m mypy app
command -v ty >/dev/null 2>&1 && ty check app || true
"$PYTHON" -m ruff check app
"$PYTHON" -m ruff format app --check
