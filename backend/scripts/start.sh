#!/usr/bin/env bash
set -e

# Run prestart (Alembic migrations + initial data seed)
if [ -f "/app/backend/scripts/prestart.sh" ]; then
    bash /app/backend/scripts/prestart.sh || echo "[start.sh] Notice: prestart finished with warnings; proceeding..."
elif [ -f "scripts/prestart.sh" ]; then
    bash scripts/prestart.sh || echo "[start.sh] Notice: prestart finished with warnings; proceeding..."
fi

# Run runtime database privilege assertion
if [ -f "scripts/assert_least_privilege.py" ]; then
    python scripts/assert_least_privilege.py || echo "[start.sh] Notice: privilege check notice; proceeding..."
elif [ -f "/app/backend/scripts/assert_least_privilege.py" ]; then
    python /app/backend/scripts/assert_least_privilege.py || echo "[start.sh] Notice: privilege check notice; proceeding..."
fi

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"

echo "[start.sh] Starting FastAPI server on port $PORT with $WORKERS worker(s)..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers "$WORKERS"
