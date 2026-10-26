"""Small event envelope used by the outbox webhook adapter."""

import json
from collections.abc import Mapping
from typing import Any

from app.integration.webhooks import sign_webhook


def signed_event(
    event_type: str,
    payload: Mapping[str, Any],
    secrets: Mapping[str, bytes],
    *,
    key_id: str | None = None,
) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(
        {"type": event_type, "payload": dict(payload)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return body, sign_webhook(body, secrets, key_id=key_id)
