from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.domain.clock import get_clock_offset, now, set_clock_offset

router = APIRouter(tags=["simulation"])


class ClockUpdate(BaseModel):
    offset_seconds: int


@router.get("/sim/clock")
def get_clock() -> dict[str, Any]:
    return {
        "now": now().isoformat(),
        "offset_seconds": get_clock_offset(),
        "is_simulated": get_clock_offset() != 0,
        "env": settings.FASTAPI_ENV,
    }


@router.put("/sim/clock")
def update_clock(update: ClockUpdate) -> dict[str, Any]:
    try:
        new_offset = set_clock_offset(update.offset_seconds)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    return {
        "now": now().isoformat(),
        "offset_seconds": new_offset,
        "is_simulated": new_offset != 0,
    }
