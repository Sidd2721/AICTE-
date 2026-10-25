from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.api.deps import CurrentUser, SessionDep

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
