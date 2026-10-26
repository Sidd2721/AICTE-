#!/usr/bin/env python3
"""Assert runtime database role conforms to least-privilege invariants (I1, I4).

Must have rolsuper = false and rolbypassrls = false.
Exits 0 if valid or in development; exits 1 with diagnosis if superuser / bypassrls detected.
"""
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

def check_privileges() -> None:
    if settings.FASTAPI_ENV == "development":
        print("[assert_least_privilege] FASTAPI_ENV is development; skipping strict role check.")
        return

    db_url = str(settings.DATABASE_URL)
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT CURRENT_USER, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = CURRENT_USER")).fetchone()
            if not row:
                sys.stderr.write("[assert_least_privilege] FATAL: Could not query pg_roles for CURRENT_USER.\n")
                sys.exit(1)
            user, is_super, bypass_rls = row[0], row[1], row[2]
            print(f"[assert_least_privilege] Connected as user '{user}': rolsuper={is_super}, rolbypassrls={bypass_rls}")
            if is_super or bypass_rls:
                sys.stderr.write(
                    f"\n[assert_least_privilege] FATAL: Database role '{user}' has excessive privileges! "
                    f"(rolsuper={is_super}, rolbypassrls={bypass_rls}).\n"
                    f"Invariant I4 strictly requires runtime role to have NOSUPERUSER and NOBYPASSRLS.\n"
                    f"Create and use the restricted 'app' role via scripts/db-roles-managed.sql or scripts/roles.sql.\n"
                )
                sys.exit(1)
            print("[assert_least_privilege] OK: Runtime database role enforces least privilege.")
    except Exception as e:
        sys.stderr.write(f"[assert_least_privilege] Database connection check failed: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    check_privileges()
