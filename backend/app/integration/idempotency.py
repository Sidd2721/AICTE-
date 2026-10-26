"""Request fingerprints and durable idempotency records."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import IdempotencyRecord


class IdempotencyConflict(ValueError):
    """Raised when a key is reused with a different request body."""


def body_hash(body: Any) -> str:
    encoded = json.dumps(
        body, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def ensure_same_request(existing_hash: str, requested_hash: str) -> bool:
    if existing_hash != requested_hash:
        raise IdempotencyConflict(
            "same Idempotency-Key was used for a different request"
        )
    return True


def claim_request(
    session: Session,
    *,
    scope: str,
    key: str,
    request_hash: str,
    ttl: timedelta = timedelta(hours=24),
) -> tuple[IdempotencyRecord, bool]:
    if not 1 <= len(key) <= 255:
        raise ValueError("Idempotency-Key must be between 1 and 255 characters")
    existing = session.exec(
        select(IdempotencyRecord).where(
            IdempotencyRecord.scope == scope, IdempotencyRecord.key == key
        )
    ).first()
    if existing:
        ensure_same_request(existing.request_hash, request_hash)
        return existing, False
    record = IdempotencyRecord(
        scope=scope,
        key=key,
        request_hash=request_hash,
        expires_at=datetime.now(UTC) + ttl,
    )
    session.add(record)
    try:
        session.commit()
        session.refresh(record)
        return record, True
    except IntegrityError:
        session.rollback()
        existing = session.exec(
            select(IdempotencyRecord).where(
                IdempotencyRecord.scope == scope, IdempotencyRecord.key == key
            )
        ).one()
        ensure_same_request(existing.request_hash, request_hash)
        return existing, False


def complete_request(
    session: Session,
    record: IdempotencyRecord,
    *,
    status_code: int,
    response: dict[str, Any],
) -> None:
    record.status_code = status_code
    record.response_json = response
    session.add(record)
    session.commit()


def replay_response(record: IdempotencyRecord) -> dict[str, Any] | None:
    if record.response_json is None:
        return None
    return dict(record.response_json)
