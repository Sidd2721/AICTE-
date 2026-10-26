#!/usr/bin/env bash
# Reset AICTE FDR Portal Demo on a VM or container host (Sprint 2 Track 2)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

echo -e "\033[1;34m[DEMO-RESET]\033[0m Resetting AICTE FDR Portal to pristine demo state..."

# 1. If running inside Docker Compose environment
if [ -f "deploy/docker-compose.demo.yml" ] && command -v docker >/dev/null 2>&1 && docker compose -f deploy/docker-compose.demo.yml ps --services --filter "status=running" | grep -q "api"; then
    echo -e "\033[1;33m[1/2]\033[0m Resetting and reseeding database via docker compose api container..."
    docker compose -f deploy/docker-compose.demo.yml exec -T api uv run python -m app.initial_data
    echo -e "\033[1;33m[2/2]\033[0m Replaying 7 problem-statement demo steps..."
    docker compose -f deploy/docker-compose.demo.yml exec -T api uv run python scripts/demo_steps.py
else
    # 2. Local VM / bare-metal environment
    echo -e "\033[1;33m[1/2]\033[0m Resetting and reseeding local database..."
    if command -v uv >/dev/null 2>&1; then
        uv run python -m app.initial_data
        echo -e "\033[1;33m[2/2]\033[0m Replaying 7 problem-statement demo steps..."
        uv run python scripts/demo_steps.py
    else
        python3 -m app.initial_data
        echo -e "\033[1;33m[2/2]\033[0m Replaying 7 problem-statement demo steps..."
        python3 scripts/demo_steps.py
    fi
fi

echo -e "\033[1;32m[OK]\033[0m Demo reset complete! All 7 problem-statement scenarios active and verified."
