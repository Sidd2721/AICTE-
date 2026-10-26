#!/usr/bin/env bash
set -e

# Run prestart (Alembic migrations + initial data seed)
if [ -f "/app/backend/scripts/prestart.sh" ]; then
    bash /app/backend/scripts/prestart.sh
elif [ -f "scripts/prestart.sh" ]; then
    bash scripts/prestart.sh
fi

# Run runtime database privilege assertion
if [ -f "scripts/assert_least_privilege.py" ]; then
    python scripts/assert_least_privilege.py
elif [ -f "/app/backend/scripts/assert_least_privilege.py" ]; then
    python /app/backend/scripts/assert_least_privilege.py
fi

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"

echo "[start.sh] Starting FastAPI server on port $PORT with $WORKERS worker(s)..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers "$WORKERS"
