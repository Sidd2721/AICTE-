from app.domain.next_action import dashboard_bucket, next_action

BASE = dict(
    role="regional",
    lifecycle="pending",
    badge="claimed",
    docs_complete=True,
    open_flags=0,
    confirmation_status=None,
    days_to_maturity=400,
    expiring_days=90,
    has_replacement=False,
    release_status=None,
)


def act(**kw: object) -> str:
    params = {**BASE, **kw}
    return next_action(**params).code  # type: ignore[arg-type]


def test_institution_missing_docs() -> None:
    assert act(role="institution", docs_complete=False) == "upload_documents"


def test_institution_return_letter() -> None:
    assert act(role="institution", confirmation_status="requested") == "return_bank_letter"


def test_institution_renewal_window() -> None:
    assert act(role="institution", lifecycle="active", days_to_maturity=30) == "add_renewal"


def test_institution_nothing() -> None:
    assert act(role="institution", lifecycle="active") == "none"


def test_regional_request() -> None:
    assert act() == "request_confirmation"


def test_regional_review_flags() -> None:
    assert act(open_flags=2) == "review_flags"


def test_regional_accept() -> None:
    assert act(badge="confirmed", confirmation_status="confirmed") == "accept_record"


def test_regional_retry_when_unavailable() -> None:
    assert act(confirmation_status="unavailable") == "retry_confirmation"


def test_regional_stale() -> None:
    assert act(lifecycle="active", badge="stale") == "request_confirmation"


def test_regional_changed() -> None:
    assert act(lifecycle="active", badge="changed") == "request_confirmation"


def test_regional_matured_contact() -> None:
    assert act(lifecycle="matured") == "contact_institution"


def test_regional_verify_release_has_priority() -> None:
    assert act(release_status="submitted", open_flags=3) == "verify_release"


def test_bureau_approve() -> None:
    assert act(role="bureau", release_status="verified") == "approve_release"


def test_bureau_nothing_else() -> None:
    assert act(role="bureau") == "none"


def test_auditor_read_only() -> None:
    assert act(role="auditor", release_status="submitted") == "none"


def test_buckets() -> None:
    assert dashboard_bucket("active", 30, 90) == "expiring"
    assert dashboard_bucket("active", 200, 90) == "active"
    assert dashboard_bucket("active", -1, 90) == "active"  # past maturity handled by daily job
    assert dashboard_bucket("matured", -5, 90) == "matured"
    assert dashboard_bucket("pending", 30, 90) == "pending"
