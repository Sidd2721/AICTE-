import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.integration.checkpoints import (
    AuditCheckpointSigner,
    write_latest_audit_checkpoint,
)
from app.models import AuditEvent

router = APIRouter(prefix="/audit", tags=["audit"])

CHECKPOINT_DIR = Path(__file__).resolve().parents[4] / "data" / "checkpoints"
CHECKPOINT_KEY_PATH = CHECKPOINT_DIR / "ed25519_checkpoint.key"


def get_checkpoint_signer() -> AuditCheckpointSigner:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    if CHECKPOINT_KEY_PATH.exists():
        return AuditCheckpointSigner.from_private_key_file(CHECKPOINT_DIR, CHECKPOINT_KEY_PATH)
    key = Ed25519PrivateKey.generate()
    CHECKPOINT_KEY_PATH.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return AuditCheckpointSigner(CHECKPOINT_DIR, key)


@router.get("/checkpoints")
def list_checkpoints(session: SessionDep) -> dict[str, Any]:
    """Retrieve signed detached audit checkpoints and public verification key (Requirement 3.7)."""
    signer = get_checkpoint_signer()
    try:
        write_latest_audit_checkpoint(session, signer)
    except Exception:
        pass

    checkpoints = []
    if CHECKPOINT_DIR.exists():
        for cp_file in sorted(CHECKPOINT_DIR.glob("checkpoint-*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                data = json.loads(cp_file.read_text(encoding="utf-8"))
                checkpoints.append(data)
            except Exception:
                pass

    return {
        "checkpoints": checkpoints[:20],
        "public_key_pem": signer.public_key_pem().decode("utf-8"),
        "note": "A demo key on the same host demonstrates the cryptographic protocol, but does NOT constitute independent trust; production anchors externally to an independent transparency log or HSM.",
    }


@router.get("/checkpoints/pubkey")
def get_checkpoint_pubkey() -> Response:
    """Retrieve public verification key for detached audit checkpoints in PEM format."""
    signer = get_checkpoint_signer()
    return Response(
        content=signer.public_key_pem(),
        media_type="application/x-pem-file",
    )


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
    current_user: CurrentUser,  # noqa: ARG001 — authentication dependency (I10)
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
