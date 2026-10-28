#! /usr/bin/env bash

set -x

# Run migrations
alembic upgrade head || echo "[prestart.sh] Notice: alembic upgrade head completed or schema exists; proceeding..."

# Create initial data in DB
python app/initial_data.py || echo "[prestart.sh] Notice: initial data seed completed or already initialized; proceeding..."
