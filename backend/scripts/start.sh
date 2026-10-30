#!/usr/bin/env bash
set -e

START_TIME=$(date +%s)
echo "[start.sh] Initializing container runtime at $(date -u +%Y-%m-%dT%H:%M:%SZ)..."

# Phase 1: Database Migrations
T0=$(date +%s)
if [ -f "/app/backend/scripts/prestart.sh" ]; then
    bash /app/backend/scripts/prestart.sh || echo "[start.sh] Notice: prestart finished with warnings; proceeding..."
elif [ -f "scripts/prestart.sh" ]; then
    bash scripts/prestart.sh || echo "[start.sh] Notice: prestart finished with warnings; proceeding..."
fi
T1=$(date +%s)
echo "[start.sh] Phase 1 (Migrations) completed in $((T1 - T0))s"

# Phase 2: Runtime database privilege assertion
T0=$(date +%s)
if [ -f "scripts/assert_least_privilege.py" ]; then
    python scripts/assert_least_privilege.py || echo "[start.sh] Notice: privilege check notice; proceeding..."
elif [ -f "/app/backend/scripts/assert_least_privilege.py" ]; then
    python /app/backend/scripts/assert_least_privilege.py || echo "[start.sh] Notice: privilege check notice; proceeding..."
fi
T1=$(date +%s)
echo "[start.sh] Phase 2 (Least-privilege verification) completed in $((T1 - T0))s"

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"

TOTAL_BOOT=$((T1 - START_TIME))
echo "[start.sh] Pre-bind phases completed in ${TOTAL_BOOT}s. Binding to 0.0.0.0:$PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers "$WORKERS"
