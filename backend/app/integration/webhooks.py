"""Versioned HMAC webhook signatures with replay protection."""

import hashlib
import hmac
import time
from collections.abc import Mapping


def _sign(body: bytes, secret: bytes, timestamp: int) -> str:
    message = str(timestamp).encode("ascii") + b"." + body
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def sign_webhook(
    body: bytes,
    secrets: Mapping[str, bytes],
    *,
    key_id: str | None = None,
    timestamp: int | None = None,
) -> dict[str, str]:
    if not body:
        raise ValueError("webhook body must not be empty")
    if not secrets:
        raise ValueError("at least one webhook secret is required")
    selected = key_id or list(secrets)[-1]
    secret = secrets.get(selected)
    if secret is None:
        raise ValueError("unknown webhook key")
    ts = int(time.time()) if timestamp is None else timestamp
    return {
        "X-FDR-Signature": f"{selected}={_sign(body, secret, ts)}",
        "X-FDR-Timestamp": str(ts),
    }


def verify_webhook(
    body: bytes,
    headers: Mapping[str, str],
    secrets: Mapping[str, bytes],
    *,
    now: int | None = None,
    replay_window_seconds: int = 300,
) -> bool:
    signature_header = headers.get("X-FDR-Signature") or headers.get("x-fdr-signature")
    timestamp_header = headers.get("X-FDR-Timestamp") or headers.get("x-fdr-timestamp")
    if not signature_header or not timestamp_header:
        raise ValueError("missing webhook signature headers")
    try:
        key_id, provided = signature_header.split("=", 1)
        timestamp = int(timestamp_header)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid webhook signature headers") from exc
    secret = secrets.get(key_id)
    if secret is None:
        raise ValueError("unknown webhook key")
    current = int(time.time()) if now is None else now
    if abs(current - timestamp) > replay_window_seconds:
        raise ValueError("webhook replay window exceeded")
    expected = _sign(body, secret, timestamp)
    if not hmac.compare_digest(provided, expected):
        raise ValueError("webhook signature mismatch")
    return True
