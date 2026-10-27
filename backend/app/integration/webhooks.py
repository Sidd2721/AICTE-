"""Versioned HMAC webhook signatures with replay protection."""

import hashlib
import hmac
import time
from collections.abc import Mapping
from typing import Any


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


def deliver_to_subscription(
    sub: Any,
    event_type: str,
    payload: dict[str, Any],
    session: Any,
    timeout_seconds: float = 5.0,
) -> tuple[bool, int | None, str | None, int]:
    """Delivers an event to a single webhook subscription.

    Returns (success, status_code, error_message, latency_ms).
    """
    import json
    from datetime import UTC, datetime

    import httpx

    from app.models import WebhookDeliveryLog

    envelope = {
        "event_type": event_type,
        "payload": payload,
        "subscription_id": str(sub.id),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    raw_body = json.dumps(envelope, sort_keys=True).encode("utf-8")
    sig_headers = sign_webhook(raw_body, {"key1": sub.secret.encode("utf-8")})
    headers = {
        "Content-Type": "application/json",
        **sig_headers,
    }

    t0 = time.perf_counter()
    success = False
    status_code: int | None = None
    error_message: str | None = None

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(sub.target_url, content=raw_body, headers=headers)
            status_code = resp.status_code
            success = 200 <= resp.status_code < 300
            if not success:
                error_message = f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as exc:
        error_message = str(exc)[:400]

    latency_ms = int((time.perf_counter() - t0) * 1000)
    now_dt = datetime.now(UTC)

    if success:
        sub.last_delivered_at = now_dt
        sub.failure_count = 0
    else:
        sub.failure_count += 1

    log = WebhookDeliveryLog(
        subscription_id=sub.id,
        event_type=event_type,
        status_code=status_code,
        success=success,
        error_message=error_message,
        latency_ms=latency_ms,
        delivered_at=now_dt,
    )
    session.add(sub)
    session.add(log)
    session.commit()

    return success, status_code, error_message, latency_ms
