import sys
from app.core.config import settings

# Guard: Refuse to run test suite against remote database hosts
# The test fixture wipes tenant tables on teardown.
_db_hosts = [h.get("host") for h in settings.DATABASE_URL.hosts() if h.get("host")]
_allowed_local = {"localhost", "127.0.0.1", "::1", "db", "postgres"}
for _h in _db_hosts:
    if _h not in _allowed_local:
        sys.stderr.write(
            f"\nFATAL: Refusing to run tests against remote database host '{_h}'!\n"
            f"The test suite teardown truncates tables. Point DATABASE_URL to a local database.\n"
        )
        sys.exit(3)
