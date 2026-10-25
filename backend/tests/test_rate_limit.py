from datetime import datetime, timedelta, timezone
from sqlmodel import Session

from app.core.rate_limit import check_rate_limit, ensure_rate_limit_table


def test_postgres_rate_limiter(db: Session) -> None:
    ensure_rate_limit_table(db)
    now = datetime.now(timezone.utc)
    key = "test:login:ip:192.168.1.1"

    # Clean prior run
    db.exec(
        __import__("sqlalchemy").text("DELETE FROM rate_limit_bucket WHERE key = :k"),
        params={"k": key},
    )
    db.commit()

    # Allow up to 3 requests per 60 seconds
    for _ in range(3):
        allowed, retry_after = check_rate_limit(
            db, key=key, max_requests=3, window_seconds=60, now=now
        )
        assert allowed is True
        assert retry_after == 0

    # 4th request must be rejected
    allowed, retry_after = check_rate_limit(
        db, key=key, max_requests=3, window_seconds=60, now=now
    )
    assert allowed is False
    assert retry_after > 0

    # Fast forward clock past window
    future = now + timedelta(seconds=65)
    allowed, retry_after = check_rate_limit(
        db, key=key, max_requests=3, window_seconds=60, now=future
    )
    assert allowed is True
    assert retry_after == 0
