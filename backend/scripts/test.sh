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

FASTAPI_ENV=development "$PYTHON" -m coverage run -m pytest tests/
"$PYTHON" -m coverage report
"$PYTHON" -m coverage html --title "${@-coverage}"

