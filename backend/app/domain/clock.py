from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from app.core.config import settings

_offset_seconds: int = 0
_last_changed_at: datetime | None = None


def _default_time_source() -> datetime:
    return datetime.now(UTC)


_time_source_fn: Callable[[], datetime] = _default_time_source


def set_time_source(fn: Callable[[], datetime] | None) -> None:
    """Inject a custom time source for deterministic testing of clock idle expiry."""
    global _time_source_fn
    if fn is None:
        _time_source_fn = _default_time_source
    else:
        _time_source_fn = fn


def reset_time_source() -> None:
    """Reset injected time source back to default UTC wall clock."""
    set_time_source(None)


def _check_idle_reset() -> None:
    """Lazily revert shifted clock offset if untouched beyond idle threshold."""
    global _offset_seconds, _last_changed_at
    idle_minutes = settings.DEMO_CLOCK_IDLE_MINUTES
    if idle_minutes > 0 and _offset_seconds != 0:
        now_dt = _time_source_fn()
        if _last_changed_at is None:
            _last_changed_at = now_dt
        else:
            t1 = (
                _last_changed_at
                if _last_changed_at.tzinfo is not None
                else _last_changed_at.replace(tzinfo=UTC)
            )
            t2 = now_dt if now_dt.tzinfo is not None else now_dt.replace(tzinfo=UTC)
            elapsed = (t2 - t1).total_seconds()
            if elapsed >= idle_minutes * 60:
                _offset_seconds = 0
                _last_changed_at = None


def get_clock_offset() -> int:
    _check_idle_reset()
    return _offset_seconds


def set_clock_offset(seconds: int) -> int:
    global _offset_seconds, _last_changed_at
    if settings.FASTAPI_ENV not in ("development", "test", "demo", None):
        raise PermissionError("Clock manipulation forbidden outside development/demo")
    _offset_seconds = seconds
    _last_changed_at = _time_source_fn() if seconds != 0 else None
    return _offset_seconds


def now() -> datetime:
    """Current simulated UTC datetime."""
    _check_idle_reset()
    base = _time_source_fn()
    if settings.FASTAPI_ENV in ("development", "test", "demo", None):
        return base + timedelta(seconds=_offset_seconds)
    return base


def today() -> date:
    """Current simulated UTC date."""
    return now().date()
