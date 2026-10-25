"""Ported database behavior checks from starter/tests/sql_behaviour_check.py.

Verifies:
- Row Level Security (RLS) scoping: institution, regional, bureau, auditor, and fail-closed unauthenticated.
- Auditor write refusal and child table RLS cascade.
- Append-only cryptographic audit hash-chain (audit_append, audit_verify, concurrency, and trigger blocks).
- Superuser tampering detection.
- Dual-custody constraint on release_request (verified_by <> approved_by).
- Notice idempotency and flag_waiver validation.
- App role flags (rolsuper=false, rolbypassrls=false).
- Comprehensive RLS coverage guard across tenant tables.
"""
import os
import threading
import uuid
import psycopg
import pytest

MIG = os.environ.get(
    "MIGRATION_PG_URL",
    "host=localhost port=5432 dbname=app user=migrator password=change-me-migrator",
)
APP = os.environ.get(
    "APP_PG_URL",
    "host=localhost port=5432 dbname=app user=app password=change-me-app",
)
SUPER = os.environ.get(
    "SUPERUSER_PG_URL",
    f"host=localhost port=5432 dbname=app user=postgres password={os.environ.get('POSTGRES_PASSWORD', 'changethis')}",
)


def app_conn(role: str, region: str = "", institution: str = "") -> psycopg.Connection:
    c = psycopg.connect(APP, autocommit=False)
    c.execute(
        "SELECT set_config('app.role',%s,true), set_config('app.region',%s,true), set_config('app.institution',%s,true)",
        (role, region, institution),
    )
    return c


def count(c: psycopg.Connection, sql: str) -> int:
    res = c.execute(sql).fetchone()
    assert res is not None
    return int(res[0])


@pytest.fixture(scope="module")
def setup_test_data() -> tuple[str, str, str, str, str, str, str]:
    """Seed test fixtures using the schema owner (migrator)."""
    m = psycopg.connect(MIG, autocommit=True)
    m.execute("DELETE FROM flag_waiver")
    m.execute("DELETE FROM notice")
    m.execute("DELETE FROM obligation")
    m.execute("DELETE FROM case_note WHERE body = 'n'")
    m.execute("DELETE FROM instrument WHERE ref_no = '1234' AND bank_code = 'SBIN'")
    m.execute("DELETE FROM \"user\" WHERE email IN ('a@x', 'b@x', 'r@x')")
    m.execute("DELETE FROM institution WHERE permanent_id LIKE 'P1%' OR permanent_id LIKE 'P2%'")


    tag = uuid.uuid4().hex[:6]
    p1, p2 = f"P1_{tag}", f"P2_{tag}"
    insA, insB = str(uuid.uuid4()), str(uuid.uuid4())
    m.execute(
        "INSERT INTO institution(id,permanent_id,name,region) VALUES (%s,%s,'Inst A','WR'),(%s,%s,'Inst B','NR')",
        (insA, p1, insB, p2),
    )

    uA, uB, uR = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    m.execute(
        """INSERT INTO "user"(id,email,role,region,institution_id,hashed_password,is_active,is_superuser) VALUES
        (%s,'a@x','institution','WR',%s,'h',true,false),(%s,'b@x','institution','NR',%s,'h',true,false),(%s,'r@x','regional','WR',NULL,'h',true,false)""",
        (uA, insA, uB, insB, uR),
    )

    iA, iB = str(uuid.uuid4()), str(uuid.uuid4())
    for iid, inst, reg in ((iA, insA, "WR"), (iB, insB, "NR")):
        m.execute(
            """INSERT INTO instrument(id,institution_id,region,kind,ref_no,bank_code,ifsc,amount_paise,issue_date,maturity_date)
            VALUES (%s,%s,%s,'FDR','1234','SBIN','SBIN0000001',1000000,'2026-01-01','2027-01-01')""",
            (iid, inst, reg),
        )
        m.execute("INSERT INTO case_note(instrument_id,author_id,body) VALUES (%s,%s,'n')", (iid, uR))
    m.close()
    return insA, insB, uA, uB, uR, iA, iB


def test_sql_behaviour_checks(setup_test_data: tuple[str, str, str, str, str, str, str]) -> None:
    insA, insB, uA, uB, uR, iA, iB = setup_test_data
    m = psycopg.connect(MIG, autocommit=True)

    # 1. regional WR sees 1 instrument
    c = app_conn("regional", "WR")
    assert count(c, "SELECT count(*) FROM instrument") == 1
    # 2. regional WR sees only its notes (child RLS)
    assert count(c, "SELECT count(*) FROM case_note") == 1
    c.rollback()
    c.close()

    # 3. institution B sees only own instrument
    c = app_conn("institution", "", insB)
    assert count(c, "SELECT count(*) FROM instrument") == 1
    assert count(c, f"SELECT count(*) FROM instrument WHERE id='{iB}'") == 1
    c.rollback()
    c.close()

    # 4. bureau sees all
    c = app_conn("bureau")
    assert count(c, "SELECT count(*) FROM instrument") >= 2
    c.rollback()
    c.close()

    # 5. no context sees nothing (fail closed)
    c = psycopg.connect(APP)
    assert count(c, "SELECT count(*) FROM instrument") == 0
    c.rollback()
    c.close()

    # 6. auditor can read
    c = app_conn("auditor")
    assert count(c, "SELECT count(*) FROM instrument") >= 2
    # 7. auditor cannot update
    try:
        c.execute("UPDATE instrument SET lien_marked = true")
        n = c.execute("SELECT count(*) FROM instrument WHERE lien_marked").fetchone()[0]
        blocked = (n == 0)
    except Exception:
        blocked = True
    c.rollback()
    assert blocked, "auditor must not be able to update instruments"

    # 8. auditor cannot insert child rows
    try:
        c.execute("INSERT INTO case_note(instrument_id,author_id,body) VALUES (%s,%s,'x')", (iA, uR))
        blocked = False
    except Exception:
        blocked = True
    c.rollback()
    c.close()
    assert blocked, "auditor must not be able to insert case_note"

    # 9. regional WR cannot write into NR (WITH CHECK)
    c = app_conn("regional", "WR")
    try:
        c.execute(
            "INSERT INTO instrument(institution_id,region,kind,ref_no,bank_code,ifsc,amount_paise,issue_date,maturity_date) "
            "VALUES (%s,'NR','FDR','9','SBIN','SBIN0000001',1,'2026-01-01','2027-01-01')",
            (insB,),
        )
        blocked = False
    except Exception:
        blocked = True
    c.rollback()
    c.close()
    assert blocked, "regional WR cannot insert into NR region"

    # 10. audit: app cannot INSERT into audit_event directly
    c = app_conn("regional", "WR")
    try:
        c.execute("INSERT INTO audit_event(ts,action,entity,entity_id,prev_hash,hash) VALUES (now(),'a','e','1','x','y')")
        blocked = False
    except Exception:
        blocked = True
    c.rollback()
    assert blocked, "app role cannot directly insert into audit_event"

    # 11. app can append via function
    id1 = c.execute("SELECT audit_append(%s,'create','instrument',%s,'{\"amt\":1}')", (uR, iA)).fetchone()[0]
    c.commit()
    assert id1 is not None, "audit_append returned null id"

    # 12. regional cannot read audit rows
    assert count(c, "SELECT count(*) FROM audit_event") == 0
    c.rollback()
    c.close()

    # 13. bureau can read audit rows
    c = app_conn("bureau")
    assert count(c, "SELECT count(*) FROM audit_event") >= 1

    # 14. audit_verify clean -> NULL
    res = c.execute("SELECT audit_verify()").fetchone()
    assert res is not None and res[0] is None, "audit_verify should return NULL for clean chain"
    c.rollback()
    c.close()

    # 15. concurrency: 8 threads x 15 appends must give one linear chain
    def worker() -> None:
        cc = app_conn("regional", "WR")
        for _ in range(15):
            cc.execute("SELECT audit_append(%s,'t','x','1','{\"k\":\"v\"}')", (uR,))
            cc.commit()
            cc.execute("SELECT set_config('app.role','regional',true)")
        cc.close()

    ts = [threading.Thread(target=worker) for _ in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    rows = m.execute("SELECT count(*), count(DISTINCT prev_hash) FROM audit_event").fetchone()
    assert rows is not None
    assert rows[0] == rows[1], f"concurrent appends must be strictly linear (count={rows[0]}, distinct_prev={rows[1]})"

    c = app_conn("bureau")
    assert c.execute("SELECT audit_verify()").fetchone()[0] is None, "audit_verify must be clean after concurrent appends"
    c.rollback()
    c.close()

    # 16. owner UPDATE/DELETE/TRUNCATE blocked by triggers
    for sql in (
        "UPDATE audit_event SET action='x' WHERE id=2",
        "DELETE FROM audit_event WHERE id=2",
        "TRUNCATE audit_event",
    ):
        try:
            m.execute(sql)
            blocked = False
        except Exception:
            blocked = True
        assert blocked, f"Trigger failed to block: {sql}"

    # 17. superuser tamper detection
    su = psycopg.connect(SUPER, autocommit=True)
    su.execute("ALTER TABLE audit_event DISABLE TRIGGER USER")
    su.execute("UPDATE audit_event SET payload='{\"k\":\"EVIL\"}' WHERE id=5")
    su.execute("ALTER TABLE audit_event ENABLE TRIGGER USER")
    su.close()

    c = app_conn("bureau")
    bad = c.execute("SELECT audit_verify()").fetchone()[0]
    c.rollback()
    c.close()
    assert bad == 5, f"tamper by superuser should be detected at id 5, got {bad}"

    # Restore the tampered row so chain is valid again for remaining tests
    su = psycopg.connect(SUPER, autocommit=True)
    su.execute("ALTER TABLE audit_event DISABLE TRIGGER USER")
    su.execute("UPDATE audit_event SET payload='{\"k\":\"v\"}' WHERE id=5")
    su.execute("ALTER TABLE audit_event ENABLE TRIGGER USER")
    su.close()

    # 18. release: verifier != approver CHECK
    try:
        m.execute(
            "INSERT INTO release_request(instrument_id,path,requested_by,verified_by,approved_by) VALUES (%s,'closure',%s,%s,%s)",
            (iA, uA, uR, uR),
        )
        blocked = False
    except Exception:
        blocked = True
    assert blocked, "CHECK constraint must forbid verified_by == approved_by"

    # 19. notice idempotency
    ob = str(uuid.uuid4())
    m.execute(
        "INSERT INTO obligation(id,instrument_id,kind,due_date,owner_role) VALUES (%s,%s,'maturity','2027-01-01','regional')",
        (ob, iA),
    )
    m.execute(
        "INSERT INTO notice(instrument_id,obligation_id,step) VALUES (%s,%s,'T-30') ON CONFLICT (obligation_id, step) DO NOTHING",
        (iA, ob),
    )
    m.execute(
        "INSERT INTO notice(instrument_id,obligation_id,step) VALUES (%s,%s,'T-30') ON CONFLICT (obligation_id, step) DO NOTHING",
        (iA, ob),
    )
    assert m.execute(f"SELECT count(*) FROM notice WHERE obligation_id = '{ob}'").fetchone()[0] == 1

    # 20. flag waiver needs a real reason (>= 10 chars)
    try:
        m.execute(
            "INSERT INTO flag_waiver(instrument_id,code,reason,waived_by) VALUES (%s,'D1','short',%s)",
            (iA, uR),
        )
        blocked = False
    except Exception:
        blocked = True
    assert blocked, "flag_waiver must reject reasons with < 10 characters"

    # 21. flag_waiver is region-scoped
    c = app_conn("regional", "WR")
    c.execute(
        "INSERT INTO flag_waiver(instrument_id,code,reason,waived_by) VALUES (%s,'D1','Bank confirmed by phone, letter pending',%s)",
        (iA, uR),
    )
    c.commit()
    c.close()

    c = app_conn("regional", "NR")
    assert count(c, "SELECT count(*) FROM flag_waiver") == 0, "flag_waiver must be scoped to WR only"
    c.rollback()
    c.close()

    # 22. app role flags are false/false
    g = m.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='app'").fetchone()
    assert g == (False, False), f"app role must have rolsuper=False, rolbypassrls=False, got {g}"

    # 23. RLS coverage guard
    missing = m.execute(
        """SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind='r' AND NOT c.relrowsecurity
          AND EXISTS (SELECT 1 FROM information_schema.columns k WHERE k.table_name=c.relname AND k.table_schema='public' AND k.column_name IN ('instrument_id','institution_id'))
          AND c.relname <> 'user'"""
    ).fetchall()
    assert missing == [], f"Tenant tables missing RLS: {missing}"

    m.close()
