#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "========================================================="
echo "       AICTE FDR PORTAL — FULL GATE VERIFICATION         "
echo "========================================================="

echo -e "\n>>> 1. Backend Tests (pytest)"
(cd backend && uv run pytest -q)

echo -e "\n>>> 2. Backend Types (mypy)"
(cd backend && uv run mypy app)

echo -e "\n>>> 3. Backend Lint (ruff)"
(cd backend && uv run ruff check app)

echo -e "\n>>> 4. Frontend Lint (biome)"
(cd frontend && bunx biome check --no-errors-on-unmatched --files-ignore-unknown=true ./)

echo -e "\n>>> 5. Frontend Bundle Build (bun run build)"
(cd frontend && bun run build)

echo -e "\n>>> 6. Production Dist Leak Checks"
DIST_DIR="$ROOT_DIR/backend/app/frontend"
if [ ! -d "$DIST_DIR" ]; then
    echo "ERROR: Dist directory does not exist: $DIST_DIR"
    exit 1
fi
if grep -rn "changethis" "$DIST_DIR"; then
    echo "ERROR: Found 'changethis' leak in dist bundle!"
    exit 1
fi

echo -e "\n>>> 7. Capability Map Coverage (gen_coverage.py)"
(cd backend && uv run python ../scripts/gen_coverage.py)

echo -e "\n>>> 8. OpenAPI Client Drift Check"
git diff --exit-code frontend/src/client

echo -e "\n>>> 9. Guide / DEMO.md Drift Check"
uv run python scripts/generate_demo_md.py
git diff --exit-code DEMO.md

echo -e "\n>>> 10. Honest Claims Lint"
uv run python scripts/claims_lint.py

echo -e "\n>>> 11. Document Script References"
uv run python scripts/doc_refs.py

echo -e "\n>>> 12. Environment Variable Contract Check"
uv run python scripts/print_env_contract.py backend/app

echo -e "\n========================================================="
echo "       ALL CHECKS PASSED. Verification Gate GREEN.       "
echo "========================================================="
