#!/usr/bin/env bash
# The one gate an agent must run before it says "done". Run from the repository root.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"

if ! command -v uv >/dev/null 2>&1 && command -v uv.exe >/dev/null 2>&1; then
    uv() { uv.exe "$@"; }
fi
if ! command -v bun >/dev/null 2>&1 && command -v bun.exe >/dev/null 2>&1; then
    bun() { bun.exe "$@"; }
fi
if ! command -v bunx >/dev/null 2>&1 && command -v bun.exe >/dev/null 2>&1; then
    bunx() { bun.exe x "$@"; }
fi

echo "== .env must not be tracked"
if git ls-files --error-unmatch .env >/dev/null 2>&1; then echo "FAIL: .env is tracked by git"; exit 1; fi

echo "== migrations check"
(cd backend && uv run alembic check)

echo "== database role flags"
(cd backend && uv run python -c "
from sqlmodel import Session, create_engine, text
from app.core.config import settings
engine = create_engine(str(settings.DATABASE_URL))
with Session(engine) as s:
    r = s.exec(text(\"SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'app'\")).first()
    assert r is not None, 'Role app does not exist in pg_roles'
    assert not r[0], 'Role app must NOT be superuser'
    assert not r[1], 'Role app must NOT bypass RLS'
print('app role: rolsuper=false, rolbypassrls=false (OK)')
")

echo "== backend tests"
(cd backend && FASTAPI_ENV=development uv run pytest -q)

echo "== backend lint/types"
(cd backend && uv run bash scripts/lint.sh)

if [ "${SKIP_FRONTEND:-0}" != "1" ]; then
  echo "== frontend check (read-only)"
  (cd frontend && bunx biome check --no-errors-on-unmatched --files-ignore-unknown=true ./)
  echo "== frontend build"
  (cd frontend && bun run build)
fi

echo "ALL CHECKS PASSED"
