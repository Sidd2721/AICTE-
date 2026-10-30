"""Postgres-backed rate limiter for auth and bank reply endpoints.

Ensures rate limits are enforced across multiple worker processes and server restarts.
Keys are throttled per route, client IP, account, or token.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import text
from sqlmodel import Session


def ensure_rate_limit_table(session: Session) -> None:
    """Ensure the rate_limit_bucket table exists."""
    try:
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS rate_limit_bucket (
                    key VARCHAR(255) PRIMARY KEY,
                    count INTEGER NOT NULL DEFAULT 1,
                    reset_at TIMESTAMPTZ NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_rate_limit_bucket_reset_at ON rate_limit_bucket (reset_at);
                """
            )
        )
        session.commit()
    except Exception:
        session.rollback()


def check_rate_limit(
    session: Session,
    key: str,
    max_requests: int,
    window_seconds: int,
    now: datetime | None = None,
) -> tuple[bool, int]:
    """Check if the key is within rate limits.

    Returns (allowed, retry_after_seconds).
    """
    if now is None:
        now = datetime.now(UTC)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    # Clean up expired row for this key or check existing
    result = session.execute(
        text("SELECT count, reset_at FROM rate_limit_bucket WHERE key = :k FOR UPDATE"),
        {"k": key},
    )
    row = result.first()

    if row is None:
        reset_at = datetime.fromtimestamp(now.timestamp() + window_seconds, tz=UTC)
        session.execute(
            text(
                "INSERT INTO rate_limit_bucket (key, count, reset_at) VALUES (:k, 1, :r) "
                "ON CONFLICT (key) DO UPDATE SET count = 1, reset_at = :r"
            ),
            {"k": key, "r": reset_at},
        )
        session.commit()
        return True, 0

    current_count: int = int(row[0])
    reset_at_val: Any = row[1]
    if isinstance(reset_at_val, datetime):
        reset_at = reset_at_val
    else:
        reset_at = datetime.fromisoformat(str(reset_at_val))

    if reset_at.tzinfo is None:
        reset_at = reset_at.replace(tzinfo=UTC)

    if now >= reset_at:
        # Window expired; reset
        new_reset_at = datetime.fromtimestamp(now.timestamp() + window_seconds, tz=UTC)
        session.execute(
            text(
                "UPDATE rate_limit_bucket SET count = 1, reset_at = :r WHERE key = :k"
            ),
            {"k": key, "r": new_reset_at},
        )
        session.commit()
        return True, 0

    if current_count >= max_requests:
        retry_after = max(1, int((reset_at - now).total_seconds()))
        return False, retry_after

    session.execute(
        text("UPDATE rate_limit_bucket SET count = count + 1 WHERE key = :k"),
        {"k": key},
    )
    session.commit()
    return True, 0


def get_client_ip(request: Request, trusted_hops: int | None = None) -> str:
    """Extract client IP securely based on trusted proxy hops.

    Source: Render Documentation (https://render.com/docs/web-services#client-ip-address)
    Render's reverse proxy appends the incoming client IP to X-Forwarded-For and also
    injects True-Client-IP containing the client's public IP address.

    When trusted_hops == 0 (default / backward compatibility):
        Fallback to the legacy first X-Forwarded-For entry or direct socket client.
    When trusted_hops > 0:
        Prefer True-Client-IP if present from Render's edge, or traverse backwards
        from the right of X-Forwarded-For by trusted_hops.
    """
    from app.core.config import settings

    if trusted_hops is None:
        trusted_hops = getattr(settings, "TRUSTED_PROXY_HOPS", 0)

    if trusted_hops > 0:
        true_client = request.headers.get("True-Client-IP")
        if true_client and true_client.strip():
            return true_client.strip()

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
            if ips:
                idx = max(0, len(ips) - trusted_hops)
                return ips[idx]
        return request.client.host if request.client else "127.0.0.1"

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def enforce_rate_limit(
    _request: Request,
    session: Session,
    key: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    """Convenience helper to enforce rate limit or raise 429 Too Many Requests."""
    ensure_rate_limit_table(session)
    allowed, retry_after = check_rate_limit(
        session, key=key, max_requests=max_requests, window_seconds=window_seconds
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
