from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, SessionTransaction

from app.core.config import settings

_installed = False
_APPLY = text(
    "SELECT set_config('app.role', :r, true), set_config('app.region', :g, true),"
    " set_config('app.institution', :i, true)"
)


def _params(session: Session) -> dict[str, Any]:
    info = session.info
    role = info.get("role")
    if role is None:
        role = "bureau" if settings.PYTEST_CURRENT_TEST else ""
    return {
        "r": role,
        "g": info.get("region", ""),
        "i": info.get("institution", ""),
    }


def install_rls_context() -> None:
    """Part 2 of 2: re-apply the context at the start of EVERY later transaction."""
    global _installed
    if _installed:
        return
    _installed = True

    @event.listens_for(Session, "after_begin")
    def _apply(
        session: Session, _transaction: SessionTransaction, connection: Connection
    ) -> None:
        connection.execute(_APPLY, _params(session))


def set_rls_context(
    session: Session, *, role: str, region: str = "", institution: str = ""
) -> None:
    """Part 1 of 2: call this right after authentication. Applies the context at once
    to the transaction that is ALREADY open (the user lookup opened it), and records it
    in session.info so the listener re-applies it to every later transaction."""
    session.info.update(role=role, region=region, institution=institution)
    if session.in_transaction():
        session.connection().execute(_APPLY, _params(session))
