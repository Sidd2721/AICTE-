"""Authentication dependencies for machine-to-machine integration clients."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.rls_context import set_rls_context
from app.integration.apikeys import hash_api_key, verify_api_key
from app.models import MachineApiKey


def get_machine_client(
    session: SessionDep,
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> MachineApiKey:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    key_hash = hash_api_key(api_key)
    record = session.exec(
        select(MachineApiKey).where(MachineApiKey.key_hash == key_hash)
    ).first()
    if record is None or not verify_api_key(api_key, record):
        raise HTTPException(status_code=401, detail="Invalid or expired API key")

    # Machine clients are explicitly scoped before any tenant query. The integration
    # scope is national, so it uses the same bureau read policy as a human bureau user.
    set_rls_context(session, role="bureau")
    record.last_used_at = datetime.now(UTC)
    session.add(record)
    return record


def require_scope(scope: str) -> Callable[..., MachineApiKey]:
    def dependency(
        client: MachineApiKey = Depends(get_machine_client),
    ) -> MachineApiKey:
        if scope not in set(client.scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key lacks required scope: {scope}",
            )
        return client

    return dependency
