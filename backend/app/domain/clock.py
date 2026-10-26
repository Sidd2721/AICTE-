from datetime import UTC, date, datetime, timedelta

from app.core.config import settings

_offset_seconds: int = 0


def get_clock_offset() -> int:
    return _offset_seconds


def set_clock_offset(seconds: int) -> int:
    global _offset_seconds
    if settings.FASTAPI_ENV not in ("development", "test", "demo", None):
        raise PermissionError("Clock manipulation forbidden outside development/demo")
    _offset_seconds = seconds
    return _offset_seconds


def now() -> datetime:
    """Current simulated UTC datetime."""
    base = datetime.now(UTC)
    if settings.FASTAPI_ENV in ("development", "test", "demo", None):
        return base + timedelta(seconds=_offset_seconds)
    return base


def today() -> date:
    """Current simulated UTC date."""
    return now().date()
