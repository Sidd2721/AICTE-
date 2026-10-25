"""Tamper-evident append-only audit ledger helper.

Enforces Invariant I4: Audit only through audit_append(). Never write to audit_event directly.
Enforces Invariant I5: Payloads must reject floats, NaN, and non-string keys. Money must be integer paise.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session


def validate_audit_payload(payload: dict[str, Any]) -> None:
    """Ensure payload has string keys and no float / NaN values (Invariant I5)."""
    if not isinstance(payload, dict):
        raise TypeError("Audit payload must be a dictionary")
    for k, v in payload.items():
        if not isinstance(k, str):
            raise TypeError(
                f"Audit payload keys must be strings, got {type(k).__name__}"
            )
        if isinstance(v, float):
            raise ValueError(
                f"Floating point values are forbidden in audit payloads: {k}={v}"
            )
        if isinstance(v, dict):
            validate_audit_payload(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, float):
                    raise ValueError(
                        f"Floating point values are forbidden in audit payloads: {item}"
                    )
                if isinstance(item, dict):
                    validate_audit_payload(item)


def audit(
    session: Session,
    *,
    actor_id: UUID | str | None,
    action: str,
    entity: str,
    entity_id: str,
    payload: dict[str, Any] | None = None,
) -> int:
    """Append an event to the cryptographic SHA-256 hash-chained audit log."""
    if payload is None:
        payload = {}
    validate_audit_payload(payload)

    actor_uuid = str(actor_id) if actor_id is not None else None
    payload_json = json.dumps(payload, separators=(",", ":"))

    result = session.execute(
        text(
            "SELECT audit_append(:actor, :action, :entity, :entity_id, CAST(:payload AS jsonb))"
        ),
        {
            "actor": actor_uuid,
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
            "payload": payload_json,
        },
    )

    event_id = result.scalar()
    session.commit()
    if event_id is None:
        raise RuntimeError("audit_append returned null event id")
    return int(event_id)


audit_append = audit
