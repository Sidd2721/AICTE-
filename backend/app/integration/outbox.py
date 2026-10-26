"""Transactional outbox enqueue and SKIP LOCKED dispatcher."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, col, select

from app.models import OutboxMessage


def enqueue(
    session: Session,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
) -> OutboxMessage:
    message = OutboxMessage(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
    )
    session.add(message)
    session.flush()
    return message


def dispatch_once(
    session: Session,
    deliver: Callable[[OutboxMessage], None],
    *,
    batch_size: int = 20,
    max_attempts: int = 8,
    now: datetime | None = None,
) -> int:
    current = now or datetime.now(UTC)
    sent = 0
    for _ in range(batch_size):
        message = session.exec(
            select(OutboxMessage)
            .where(
                col(OutboxMessage.delivered_at).is_(None),
                col(OutboxMessage.dead_lettered_at).is_(None),
                OutboxMessage.available_at <= current,
            )
            .order_by(col(OutboxMessage.created_at))
            .limit(1)
            .with_for_update(skip_locked=True)
        ).first()
        if message is None:
            break
        message.attempts += 1
        message.locked_at = current
        session.add(message)
        try:
            deliver(message)
        except Exception as exc:
            message.last_error = str(exc)[:1000]
            if message.attempts >= max_attempts:
                message.dead_lettered_at = current
            else:
                message.available_at = current + timedelta(seconds=2**message.attempts)
            session.add(message)
            session.commit()
        else:
            message.delivered_at = datetime.now(UTC)
            message.last_error = None
            session.add(message)
            session.commit()
            sent += 1
    return sent
