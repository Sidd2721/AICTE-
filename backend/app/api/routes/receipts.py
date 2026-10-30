"""Public receipt verification and public key endpoints (Invariant I8 / I9).

Endpoints are public, unauthenticated, outside the OpenAPI schema, and write zero audit rows.
"""

import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import jwt
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.domain.receipt import (
    get_public_key_info,
    get_public_key_pem,
    verify_release_receipt,
)

router = APIRouter(prefix="/receipts", tags=["receipts"])

# In-memory sliding window rate limiter: zero database writes, zero audit rows
# 120 requests/minute per client IP (satisfies requirement of at least 60/min)
_RATE_LIMIT_BUCKETS: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_MAX = 120
_RATE_LIMIT_WINDOW = 60.0


def _check_verify_rate_limit(client_ip: str) -> None:
    now = time.time()
    cutoff = now - _RATE_LIMIT_WINDOW
    timestamps = [t for t in _RATE_LIMIT_BUCKETS[client_ip] if t > cutoff]
    if len(timestamps) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for receipt verification (maximum 120 per minute)",
        )
    timestamps.append(now)
    _RATE_LIMIT_BUCKETS[client_ip] = timestamps


def reset_rate_limit_buckets() -> None:
    """Helper for testing rate limit reset."""
    _RATE_LIMIT_BUCKETS.clear()


@router.get("/public-key", include_in_schema=False)
def get_receipt_public_key(request: Request) -> Any:
    """Public endpoint to fetch the portal's active receipt verification public key.

    Excluded from the OpenAPI schema.
    """
    accept = request.headers.get("accept", "")
    if "application/x-pem-file" in accept or "text/plain" in accept:
        return Response(content=get_public_key_pem(), media_type="text/plain")
    return get_public_key_info()


class VerifyReceiptRequest(BaseModel):
    token: str = Field(..., max_length=4096)


class VerifyReceiptResponse(BaseModel):
    valid: bool
    reason: str | None = None
    claims: dict[str, Any] | None = None
    kid: str | None = None
    issued_at: str | None = None


@router.post(
    "/verify",
    response_model=VerifyReceiptResponse,
    include_in_schema=False,
)
async def verify_receipt_endpoint(request: Request) -> VerifyReceiptResponse:
    """Public endpoint to verify release receipt tokens.

    Strict body limit of 4 KB (returns 413 if exceeded).
    Pinned to RS256 algorithm.
    Rate limited to at least 60 requests/minute.
    Stores nothing and records zero audit events.
    """
    # 1. Enforce strict 4 KB body size limit (413 Payload Too Large)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 4096:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Payload too large: receipt verification body exceeds 4 KB maximum",
                )
        except ValueError:
            pass

    body_bytes = await request.body()
    if len(body_bytes) > 4096:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload too large: receipt verification body exceeds 4 KB maximum",
        )

    # 2. Rate limiting per client IP
    client_ip = request.client.host if request.client else "unknown"
    _check_verify_rate_limit(client_ip)

    # 3. Parse JSON payload
    try:
        data = VerifyReceiptRequest.model_validate_json(body_bytes)
    except Exception as exc:
        return VerifyReceiptResponse(
            valid=False,
            reason=f"malformed: invalid JSON payload ({exc})",
        )

    token = data.token.strip()
    if not token:
        return VerifyReceiptResponse(
            valid=False,
            reason="malformed: empty token",
        )

    # 4. Cryptographic verification pinned to RS256
    try:
        claims = verify_release_receipt(token)
        kid = claims.get("kid")
        iat = claims.get("iat")
        issued_at_str = datetime.fromtimestamp(iat, tz=UTC).isoformat() if iat else None
        return VerifyReceiptResponse(
            valid=True,
            reason=None,
            claims=claims,
            kid=kid,
            issued_at=issued_at_str,
        )
    except ValueError as val_err:
        kid_hint = None
        try:
            hdr = jwt.get_unverified_header(token)
            kid_hint = hdr.get("kid")
        except Exception:
            pass
        return VerifyReceiptResponse(
            valid=False,
            reason=str(val_err),
            claims=None,
            kid=kid_hint,
            issued_at=None,
        )
