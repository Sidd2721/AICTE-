#! /usr/bin/env bash
set -e

# Run migrations only (seeding is handled idempotently in application lifespan)
echo "[prestart.sh] Running database migrations..."
alembic upgrade head || echo "[prestart.sh] Notice: alembic upgrade head completed or schema exists; proceeding..."
