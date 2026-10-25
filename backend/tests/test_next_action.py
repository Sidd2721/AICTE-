from app.domain.next_action import Action, dashboard_bucket, next_action


BASE = dict(role="regional", lifecycle="pending", badge="claimed", docs_complete=True, open_flags=0,
            confirmation_status=None, days_to_maturity=400, expiring_days=90, has_replacement=False,
            release_status=None)
def act(**kw): return next_action(**{**BASE, **kw}).code

def test_institution_missing_docs(): assert act(role="institution", docs_complete=False) == "upload_documents"
def test_institution_return_letter(): assert act(role="institution", confirmation_status="requested") == "return_bank_letter"
def test_institution_renewal_window(): assert act(role="institution", lifecycle="active", days_to_maturity=30) == "add_renewal"
def test_institution_nothing(): assert act(role="institution", lifecycle="active") == "none"
def test_regional_request(): assert act() == "request_confirmation"
def test_regional_review_flags(): assert act(open_flags=2) == "review_flags"
def test_regional_accept(): assert act(badge="confirmed", confirmation_status="confirmed") == "accept_record"
def test_regional_retry_when_unavailable(): assert act(confirmation_status="unavailable") == "retry_confirmation"
def test_regional_stale(): assert act(lifecycle="active", badge="stale") == "request_confirmation"
def test_regional_changed(): assert act(lifecycle="active", badge="changed") == "request_confirmation"
def test_regional_matured_contact(): assert act(lifecycle="matured") == "contact_institution"
def test_regional_verify_release_has_priority(): assert act(release_status="submitted", open_flags=3) == "verify_release"
def test_bureau_approve(): assert act(role="bureau", release_status="verified") == "approve_release"
def test_bureau_nothing_else(): assert act(role="bureau") == "none"
def test_auditor_read_only(): assert act(role="auditor", release_status="submitted") == "none"
def test_buckets():
    assert dashboard_bucket("active", 30, 90) == "expiring"
    assert dashboard_bucket("active", 200, 90) == "active"
    assert dashboard_bucket("active", -1, 90) == "active"     # past maturity is handled by the daily job -> matured
    assert dashboard_bucket("matured", -5, 90) == "matured"
    assert dashboard_bucket("pending", 30, 90) == "pending"
