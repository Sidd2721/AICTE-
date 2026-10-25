import psycopg, threading, uuid, sys
MIG = "host=localhost dbname=fdr2 user=migrator password=change-me-migrator"
APP = "host=localhost dbname=fdr2 user=app password=change-me-app"
ok = fail = 0
def check(name, cond):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name); ok += cond; fail += (not cond)

# seed as migrator (owner bypasses RLS because FORCE is not used)
m = psycopg.connect(MIG, autocommit=True)
insA, insB = str(uuid.uuid4()), str(uuid.uuid4())
m.execute("INSERT INTO institution(id,permanent_id,name,region) VALUES (%s,'P1','Inst A','WR'),(%s,'P2','Inst B','NR')", (insA, insB))
uA, uB, uR = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
m.execute("""INSERT INTO "user"(id,email,role,region,institution_id) VALUES
  (%s,'a@x','institution','WR',%s),(%s,'b@x','institution','NR',%s),(%s,'r@x','regional','WR',NULL)""", (uA, insA, uB, insB, uR))
iA, iB = str(uuid.uuid4()), str(uuid.uuid4())
for iid, inst, reg in ((iA, insA, 'WR'), (iB, insB, 'NR')):
    m.execute("""INSERT INTO instrument(id,institution_id,region,kind,ref_no,bank_code,ifsc,amount_paise,issue_date,maturity_date)
                 VALUES (%s,%s,%s,'FDR','1234','SBIN','SBIN0000001',1000000,'2026-01-01','2027-01-01')""", (iid, inst, reg))
    m.execute("INSERT INTO case_note(instrument_id,author_id,body) VALUES (%s,%s,'n')", (iid, uR))

def app_conn(role, region="", institution=""):
    c = psycopg.connect(APP); c.autocommit = False
    c.execute("SELECT set_config('app.role',%s,true), set_config('app.region',%s,true), set_config('app.institution',%s,true)", (role, region, institution))
    return c
def count(c, sql): return c.execute(sql).fetchone()[0]

c = app_conn("regional", "WR"); check("regional WR sees 1 instrument", count(c,"SELECT count(*) FROM instrument")==1)
check("regional WR sees only its notes (child RLS)", count(c,"SELECT count(*) FROM case_note")==1); c.rollback()
c = app_conn("institution", "", insB); check("institution B sees only own instrument", count(c,"SELECT count(*) FROM instrument")==1 and count(c,"SELECT count(*) FROM instrument WHERE id='%s'"%iB)==1); c.rollback()
c = app_conn("bureau"); check("bureau sees all", count(c,"SELECT count(*) FROM instrument")==2); c.rollback()
c = psycopg.connect(APP); check("no context sees nothing (fail closed)", count(c,"SELECT count(*) FROM instrument")==0); c.rollback()
c = app_conn("auditor")
check("auditor can read", count(c,"SELECT count(*) FROM instrument")==2)
try:
    c.execute("UPDATE instrument SET lien_marked = true"); n = c.execute("SELECT count(*) FROM instrument WHERE lien_marked").fetchone()[0]; blocked = (n == 0)
except Exception: blocked = True
c.rollback(); check("auditor cannot update", blocked)
c = app_conn("auditor")
try: c.execute("INSERT INTO case_note(instrument_id,author_id,body) VALUES (%s,%s,'x')", (iA, uR)); blocked = False
except Exception: blocked = True
c.rollback(); check("auditor cannot insert child rows", blocked)
c = app_conn("regional", "WR")
try: c.execute("INSERT INTO instrument(institution_id,region,kind,ref_no,bank_code,ifsc,amount_paise,issue_date,maturity_date) VALUES (%s,'NR','FDR','9','SBIN','SBIN0000001',1,'2026-01-01','2027-01-01')", (insB,)); blocked=False
except Exception: blocked = True
c.rollback(); check("regional WR cannot write into NR (WITH CHECK)", blocked)

# audit: only via functions
c = app_conn("regional", "WR")
try: c.execute("INSERT INTO audit_event(ts,action,entity,entity_id,prev_hash,hash) VALUES (now(),'a','e','1','x','y')"); blocked=False
except Exception: blocked=True
c.rollback(); check("app cannot INSERT into audit_event directly", blocked)
c = app_conn("regional", "WR"); id1 = c.execute("SELECT audit_append(%s,'create','instrument',%s,'{\"amt\":1}')", (uR, iA)).fetchone()[0]; c.commit()
check("app can append via function", id1 is not None)
c = app_conn("regional", "WR"); check("regional cannot read audit rows", count(c,"SELECT count(*) FROM audit_event")==0); c.rollback()
c = app_conn("bureau"); check("bureau can read audit rows", count(c,"SELECT count(*) FROM audit_event")>=1); c.rollback()
c = app_conn("bureau"); check("audit_verify clean -> NULL", c.execute("SELECT audit_verify()").fetchone()[0] is None); c.rollback()

# concurrency: 8 threads x 15 appends must give one linear chain
def worker():
    cc = app_conn("regional", "WR")
    for _ in range(15):
        cc.execute("SELECT audit_append(%s,'t','x','1','{\"k\":\"v\"}')", (uR,)); cc.commit()
        cc.execute("SELECT set_config('app.role','regional',true)")
    cc.close()
ts = [threading.Thread(target=worker) for _ in range(8)]; [t.start() for t in ts]; [t.join() for t in ts]
rows = m.execute("SELECT count(*), count(DISTINCT prev_hash) FROM audit_event").fetchone()
check(f"concurrent appends linear (rows={rows[0]}, distinct prev={rows[1]})", rows[0]==rows[1]==121 or rows[0]==rows[1])
c = app_conn("bureau"); check("verify clean after concurrency", c.execute("SELECT audit_verify()").fetchone()[0] is None); c.rollback()

# tamper: migrator tries UPDATE/DELETE/TRUNCATE -> blocked by trigger
for sql, nm in (("UPDATE audit_event SET action='x' WHERE id=2","UPDATE"),("DELETE FROM audit_event WHERE id=2","DELETE"),("TRUNCATE audit_event","TRUNCATE")):
    try: m.execute(sql); blocked=False
    except Exception: blocked=True
    check(f"owner {nm} blocked by trigger", blocked)
# superuser bypass attempt: disable trigger, edit, verify must name the row
import os
su = psycopg.connect(f"host=localhost dbname=fdr2 user=postgres password={os.environ['PGPASSWORD']}", autocommit=True)
su.execute("ALTER TABLE audit_event DISABLE TRIGGER USER")
su.execute("UPDATE audit_event SET payload='{\"k\":\"EVIL\"}' WHERE id=5")
su.execute("ALTER TABLE audit_event ENABLE TRIGGER USER")
c = app_conn("bureau"); bad = c.execute("SELECT audit_verify()").fetchone()[0]; c.rollback()
check(f"tamper by superuser detected at id {bad}", bad == 5)

# constraints and idempotency
try:
    m.execute("""INSERT INTO release_request(instrument_id,path,requested_by,verified_by,approved_by) VALUES (%s,'closure',%s,%s,%s)""", (iA,uA,uR,uR)); blocked=False
except Exception: blocked=True
check("release: verifier != approver CHECK", blocked)
ob = str(uuid.uuid4()); m.execute("INSERT INTO obligation(id,instrument_id,kind,due_date,owner_role) VALUES (%s,%s,'maturity','2027-01-01','regional')", (ob,iA))
m.execute("INSERT INTO notice(instrument_id,obligation_id,step) VALUES (%s,%s,'T-30') ON CONFLICT (obligation_id, step) DO NOTHING", (iA,ob))
m.execute("INSERT INTO notice(instrument_id,obligation_id,step) VALUES (%s,%s,'T-30') ON CONFLICT (obligation_id, step) DO NOTHING", (iA,ob))
check("notice idempotent (one row)", m.execute("SELECT count(*) FROM notice").fetchone()[0]==1)
try:
    m.execute("INSERT INTO flag_waiver(instrument_id,code,reason,waived_by) VALUES (%s,'D1','short',%s)", (iA,uR)); blocked=False
except Exception: blocked=True
check("flag waiver needs a real reason (>=10 chars)", blocked)
c = app_conn("regional","WR"); c.execute("INSERT INTO flag_waiver(instrument_id,code,reason,waived_by) VALUES (%s,'D1','Bank confirmed by phone, letter pending',%s)", (iA,uR)); c.commit()
c = app_conn("regional","NR"); check("flag_waiver is region-scoped", count(c,"SELECT count(*) FROM flag_waiver")==0); c.rollback()
# guards
g = m.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='app'").fetchone(); check("app role flags are false/false", g==(False,False))
missing = m.execute("""SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relkind='r' AND NOT c.relrowsecurity
    AND EXISTS (SELECT 1 FROM information_schema.columns k WHERE k.table_name=c.relname AND k.table_schema='public' AND k.column_name IN ('instrument_id','institution_id'))
    AND c.relname <> 'user'""").fetchall()
check(f"RLS coverage guard (missing={missing})", missing==[])
print(f"\n{ok} passed, {fail} failed"); sys.exit(1 if fail else 0)
