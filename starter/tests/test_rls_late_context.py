from sqlmodel import Session, create_engine, text
from rls_context import install_rls_context, set_rls_context
install_rls_context()
eng = create_engine("postgresql+psycopg://app:change-me-app@localhost/fdr2", pool_size=1, max_overflow=0)
def n(s): return s.exec(text("SELECT count(*) FROM instrument")).one()[0]

def test_late_context_needs_immediate_apply():
    with Session(eng) as s:
        s.exec(text('SELECT count(*) FROM "user"')).one()      # like get_current_user: opens the transaction first
        s.info.update(role="bureau")                            # listener-only approach: too late for this transaction
        assert n(s) == 0                                        # fail closed (but wrong for the request!)
        s.rollback()
        assert n(s) == 2                                        # next transaction picks it up
def test_set_rls_context_covers_open_and_later_transactions():
    with Session(eng) as s:
        s.exec(text('SELECT count(*) FROM "user"')).one()
        set_rls_context(s, role="bureau")
        assert n(s) == 2                                        # already-open transaction
        s.commit()
        assert n(s) == 2                                        # later transaction
def test_scope_switch_and_no_context():
    with Session(eng) as s:
        set_rls_context(s, role="regional", region="WR"); assert n(s) == 1; s.commit()
    with Session(eng) as s2:
        assert n(s2) == 0
