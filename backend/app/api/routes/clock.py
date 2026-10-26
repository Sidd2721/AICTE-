from typing import Any

import jwt
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.domain.clock import get_clock_offset, now, set_clock_offset
from app.models import User

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
def update_clock(update: ClockUpdate, request: Request) -> dict[str, Any]:
    if settings.FASTAPI_ENV == "demo":
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clock manipulation in demo mode requires Bureau role authentication",
            )
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
            )
            user_id = payload.get("sub")
            with Session(engine) as session:
                user = session.get(User, user_id)
                if not user or user.role != "bureau":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Clock manipulation in demo mode is restricted to Bureau Approver persona",
                    )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid credentials for clock manipulation",
            ) from e

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
