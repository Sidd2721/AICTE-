import os
import subprocess
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.domain.clock import today
from app.domain.rules import RULES_DIR, load_rule

router = APIRouter(tags=["meta"])

SERVER_START_TIME = datetime.now(UTC).isoformat()


class MetaResponse(BaseModel):
    env_label: str
    rule_status: str
    commit: str
    built_at: str


def _get_commit_hash() -> str:
    env_commit = os.getenv("GIT_COMMIT")
    if env_commit:
        return env_commit[:7]
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "0456163"


@router.get("/meta", response_model=MetaResponse)
def get_meta() -> Any:
    """Returns runtime environment metadata without exposing secrets (CHARTER G6)."""
    rule_status = "DEMO"
    try:
        doc = load_rule(RULES_DIR, "deposit", today())
        rule_status = doc.get("status", "DEMO")
    except Exception:
        pass

    return MetaResponse(
        env_label=settings.FASTAPI_ENV or "development",
        rule_status=rule_status,
        commit=_get_commit_hash(),
        built_at=os.getenv("BUILT_AT", SERVER_START_TIME),
    )
