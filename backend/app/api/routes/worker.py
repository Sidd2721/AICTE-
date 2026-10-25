from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.core.audit import audit
from app.domain.worker import run_daily_obligations_job

router = APIRouter(tags=["simulation"])


@router.post("/sim/worker/run-daily")
def trigger_daily_worker(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    result = run_daily_obligations_job(session)
    audit(
        session=session,
        actor_id=current_user.id,
        action="daily_worker_executed",
        entity="system",
        entity_id="daily_worker",
        payload={
            "lock_acquired": result.get("lock_acquired", False),
            "obligations_processed": result.get("obligations_processed", 0),
            "notices_created": result.get("notices_created", 0),
        },
    )
    return result
