"""Public receipt verification and public key endpoints (Invariant I8 / I9).

Endpoints are public, unauthenticated, outside the OpenAPI schema, and write zero audit rows.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import jwt
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.rls_context import set_rls_context
from app.domain.receipt import (
    get_public_key_info,
    get_public_key_pem,
    verify_release_receipt,
)
from app.domain.receipt_pdf import build_release_receipt_pdf
from app.models import Institution, Instrument, ReleaseRequest

router = APIRouter(tags=["receipts"])

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


@router.get("/receipts/public-key", include_in_schema=False)
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
    algorithm: str = "RS256"
    issued_at: str | None = None


@router.post(
    "/receipts/verify",
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
            algorithm="RS256",
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
            algorithm="RS256",
            issued_at=None,
        )


def _get_seeded_sample_release_request(
    session: Session,
) -> tuple[ReleaseRequest, Instrument, Institution | None]:
    """Retrieve the seeded released request for demo showcase."""
    set_rls_context(session, role="bureau")
    req = session.exec(
        select(ReleaseRequest)
        .where(ReleaseRequest.status == "released")
        .order_by(col(ReleaseRequest.created_at).desc())
    ).first()
    if not req or not req.receipt_token:
        raise HTTPException(
            status_code=404,
            detail="No released sample receipt found in database",
        )
    inst = session.get(Instrument, req.instrument_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found")
    institution = session.get(Institution, inst.institution_id)
    return req, inst, institution


@router.get("/demo/sample-receipt.pdf", include_in_schema=False)
def get_sample_receipt_pdf(session: SessionDep) -> Response:
    """Download demo sample release receipt PDF (demo mode only)."""
    if settings.FASTAPI_ENV == "production":
        raise HTTPException(
            status_code=404,
            detail="Sample receipt endpoint is disabled in production",
        )
    req, inst, institution = _get_seeded_sample_release_request(session)
    assert req.receipt_token is not None
    inst_name = institution.name if institution else "AICTE Regulated Institution"
    pdf_bytes = build_release_receipt_pdf(
        token=req.receipt_token,
        instrument_ref_no=inst.ref_no,
        institution_name=inst_name,
        bank_code=inst.bank_code,
        amount_paise=inst.amount_paise,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="sample_release_receipt.pdf"'
        },
    )


@router.get("/demo/sample-receipt", include_in_schema=False)
def get_sample_receipt(
    session: SessionDep,
    format: str | None = Query(None),
) -> Any:
    """Get demo sample release receipt token or PDF (demo mode only)."""
    if settings.FASTAPI_ENV == "production":
        raise HTTPException(
            status_code=404,
            detail="Sample receipt endpoint is disabled in production",
        )
    if format == "pdf":
        return get_sample_receipt_pdf(session)

    req, inst, _ = _get_seeded_sample_release_request(session)
    return {
        "status": "released",
        "release_id": str(req.id),
        "instrument_id": str(inst.id),
        "instrument_ref_no": inst.ref_no,
        "token": req.receipt_token,
    }
