#!/usr/bin/env bash
# Rebuilds a scratch database from starter/sql and runs every starter test.
# Needs: a running PostgreSQL 16+ with a superuser, and Python 3.14 with:
#   pytest sqlmodel psycopg[binary] pyhanko reportlab cryptography
# Usage: PGPASSWORD=<superuser password> PY=/path/to/python bash scripts/verify-pack.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-python}"; SUPER="${SUPER:-psql -q -h localhost -U postgres}"
echo "== rebuild scratch database fdr2"
$SUPER -c "DROP DATABASE IF EXISTS fdr2" -c "REVOKE ALL ON DATABASE app FROM app, migrator" -c "DROP ROLE IF EXISTS app" -c "DROP ROLE IF EXISTS migrator" 2>&1 | grep -v NOTICE || true
$SUPER -v ON_ERROR_STOP=1 -f starter/sql/roles.sql
for f in schema audit hardening; do
  PGPASSWORD=change-me-migrator psql -q -h localhost -U migrator -d fdr2 -v ON_ERROR_STOP=1 -f starter/sql/$f.sql
done
export PGPASSWORD="${PGPASSWORD:-changethis}"
echo "== database behaviour checks"; $PY starter/tests/sql_behaviour_check.py | tail -3
echo "== unit tests"; PYTHONPATH=starter/py $PY -m pytest -q starter/tests -p no:cacheprovider
