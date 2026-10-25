#! /usr/bin/env bash

set -e
set -x

export PATH="/mnt/c/Users/avadu/.local/bin:/mnt/c/Users/avadu/.bun/bin:$HOME/.local/bin:$HOME/.bun/bin:$PATH"

if ! command -v uv >/dev/null 2>&1 && command -v uv.exe >/dev/null 2>&1; then
    uv() { uv.exe "$@"; }
fi
if ! command -v bun >/dev/null 2>&1 && command -v bun.exe >/dev/null 2>&1; then
    bun() { bun.exe "$@"; }
    bunx() { bun.exe x "$@"; }
fi

cd backend
FASTAPI_ENV=development uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../openapi.json
cd ..
mv openapi.json frontend/
bun run --filter frontend generate-client
bun run lint
