"""Scoped machine API keys. Only a SHA-256 digest is persisted."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from typing import Any

from app.models import MachineApiKey


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def issue_api_key(
    client_name: str,
    scopes: set[str],
    *,
    expires_at: datetime | None = None,
) -> tuple[str, MachineApiKey]:
    if not client_name.strip():
        raise ValueError("client name is required")
    if not scopes:
        raise ValueError("at least one scope is required")
    key_id = secrets.token_urlsafe(9)
    raw_key = f"fdr_{key_id}_{secrets.token_urlsafe(32)}"
    record = MachineApiKey(
        client_name=client_name.strip(),
        key_id=key_id,
        key_hash=hash_api_key(raw_key),
        scopes=sorted(scopes),
        expires_at=expires_at,
    )
    return raw_key, record


def verify_api_key(
    raw_key: str,
    record: MachineApiKey,
    required_scope: str | None = None,
    *,
    now: datetime | None = None,
) -> bool:
    if not hmac.compare_digest(hash_api_key(raw_key), record.key_hash):
        return False
    current = now or datetime.now(UTC)
    if not record.active or (
        record.expires_at is not None and record.expires_at <= current
    ):
        return False
    return required_scope is None or required_scope in set(record.scopes)


def public_key_record(record: MachineApiKey) -> dict[str, Any]:
    return {
        "key_id": record.key_id,
        "client_name": record.client_name,
        "scopes": record.scopes,
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
    }
