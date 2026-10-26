#!/usr/bin/env bash
# Reset AICTE FDR Portal Demo on a VM or container host (Sprint 2 Track 2)
# Follows D6: stop api -> dropdb/createdb (audit triggers forbid TRUNCATE) -> migrate -> seed -> start
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

echo -e "\033[1;34m[DEMO-RESET]\033[0m Resetting AICTE FDR Portal to pristine demo state..."

if [ -f "deploy/docker-compose.demo.yml" ] && command -v docker >/dev/null 2>&1 && docker compose -f deploy/docker-compose.demo.yml ps -q db >/dev/null 2>&1; then
    echo -e "\033[1;33m[1/5]\033[0m Stopping api container..."
    docker compose -f deploy/docker-compose.demo.yml stop api

    echo -e "\033[1;33m[2/5]\033[0m Recreating database (audit triggers forbid TRUNCATE)..."
    docker compose -f deploy/docker-compose.demo.yml exec -T db sh -c "dropdb -U \${POSTGRES_USER:-postgres} --if-exists \${POSTGRES_DB:-app} && createdb -U \${POSTGRES_USER:-postgres} \${POSTGRES_DB:-app}"

    echo -e "\033[1;33m[3/5]\033[0m Running database migrations..."
    docker compose -f deploy/docker-compose.demo.yml run --rm migrate sh -c "alembic upgrade head"

    echo -e "\033[1;33m[4/5]\033[0m Seeding rich synthetic demo data..."
    docker compose -f deploy/docker-compose.demo.yml run --rm migrate sh -c "python -m app.initial_data"

    echo -e "\033[1;33m[5/5]\033[0m Starting api service..."
    docker compose -f deploy/docker-compose.demo.yml start api
else
    echo -e "\033[1;33m[Local Mode]\033[0m Running initial_data seed..."
    if command -v uv >/dev/null 2>&1; then
        uv run python -m app.initial_data
    else
        python3 -m app.initial_data
    fi
fi

echo -e "\033[1;32m[OK]\033[0m Demo reset complete! Database reset, migrated, and reseeded."
