import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import text
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.models import AuditEvent

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/verify")
def verify_audit_chain(
    session: SessionDep,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Verify cryptographic SHA-256 hash-chain integrity.

    Restricted to bureau, auditor, and admin roles.
    Returns clean status if untampered, or the corrupted event ID if tampering is detected.
    """
    if current_user.role not in ("bureau", "auditor") and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only bureau and auditor roles have permission to verify the audit chain",
        )

    result = session.execute(text("SELECT audit_verify()")).scalar()
    if result is None:
        return {
            "status": "clean",
            "tampered_event_id": None,
            "message": "Audit hash-chain is intact and verified",
        }
    return {
        "status": "corrupted",
        "tampered_event_id": int(result),
        "message": f"Tampering detected at audit event ID {result}",
    }


@router.get("/events")
def list_audit_events(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    entity_id: str | None = Query(default=None),
    entity: str | None = Query(default=None),
) -> dict[str, Any]:
    """Paged audit event list. Bureau and auditor see all; others see only their entity events."""
    if current_user.role not in ("bureau", "auditor") and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only bureau and auditor roles can list all audit events",
        )
    query = select(AuditEvent).order_by(col(AuditEvent.id).desc())
    if entity_id:
        query = query.where(AuditEvent.entity_id == entity_id)
    if entity:
        query = query.where(AuditEvent.entity == entity)

    total = session.exec(select(AuditEvent)).all()
    events = session.exec(query.offset(skip).limit(limit)).all()
    return {
        "data": [
            {
                "id": e.id,
                "ts": e.ts.isoformat(),
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "action": e.action,
                "entity": e.entity,
                "entity_id": e.entity_id,
                "payload": e.payload,
                "hash": e.hash,
            }
            for e in events
        ],
        "count": len(total),
    }


@router.get("/events/{entity_id}")
def list_entity_audit_events(
    entity_id: str,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Per-entity audit timeline for the case page (accessible to all authenticated users)."""
    events = session.exec(
        select(AuditEvent)
        .where(AuditEvent.entity_id == entity_id)
        .order_by(col(AuditEvent.id).desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return {
        "data": [
            {
                "id": e.id,
                "ts": e.ts.isoformat(),
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "action": e.action,
                "entity": e.entity,
                "entity_id": e.entity_id,
                "payload": e.payload,
            }
            for e in events
        ],
        "count": len(events),
    }
