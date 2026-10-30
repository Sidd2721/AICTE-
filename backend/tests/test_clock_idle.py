from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain.clock import (
    get_clock_offset,
    now,
    reset_time_source,
    set_clock_offset,
    set_time_source,
    today,
)


def test_clock_idle_off_preserves_offset_indefinitely() -> None:
    """When DEMO_CLOCK_IDLE_MINUTES is 0 (off), behavior is identical to today: offset never resets."""
    reset_time_source()
    original_setting = settings.DEMO_CLOCK_IDLE_MINUTES
    settings.DEMO_CLOCK_IDLE_MINUTES = 0

    base_time = datetime(2026, 10, 30, 12, 0, 0, tzinfo=UTC)
    current_time = base_time
    set_time_source(lambda: current_time)

    try:
        set_clock_offset(3600)
        assert get_clock_offset() == 3600

        # Advance 10 days (14,400 minutes)
        current_time = base_time + timedelta(days=10)
        assert get_clock_offset() == 3600
        assert now() == current_time + timedelta(seconds=3600)
    finally:
        set_clock_offset(0)
        reset_time_source()
        settings.DEMO_CLOCK_IDLE_MINUTES = original_setting


def test_clock_idle_on_reverts_after_threshold() -> None:
    """When DEMO_CLOCK_IDLE_MINUTES > 0, shifted clock reverts to 0 after idle threshold."""
    reset_time_source()
    original_setting = settings.DEMO_CLOCK_IDLE_MINUTES
    settings.DEMO_CLOCK_IDLE_MINUTES = 20

    t0 = datetime(2026, 10, 30, 12, 0, 0, tzinfo=UTC)
    sim_time = t0
    set_time_source(lambda: sim_time)

    try:
        set_clock_offset(86400)
        assert get_clock_offset() == 86400

        # Advance to T0 + 19 minutes (under 20-min threshold)
        sim_time = t0 + timedelta(minutes=19)
        assert get_clock_offset() == 86400

        # Advance to T0 + 20 minutes (at threshold)
        sim_time = t0 + timedelta(minutes=20)
        assert get_clock_offset() == 0
        # now() should now equal base time with zero offset
        assert now() == sim_time
    finally:
        set_clock_offset(0)
        reset_time_source()
        settings.DEMO_CLOCK_IDLE_MINUTES = original_setting


def test_clock_idle_mutating_clock_restarts_idle_timer() -> None:
    """Mutating the clock offset again restarts the idle countdown."""
    reset_time_source()
    original_setting = settings.DEMO_CLOCK_IDLE_MINUTES
    settings.DEMO_CLOCK_IDLE_MINUTES = 20

    t0 = datetime(2026, 10, 30, 12, 0, 0, tzinfo=UTC)
    sim_time = t0
    set_time_source(lambda: sim_time)

    try:
        # First shift at T0
        set_clock_offset(3600)
        assert get_clock_offset() == 3600

        # Advance 15 minutes and change offset to 7200
        sim_time = t0 + timedelta(minutes=15)
        set_clock_offset(7200)
        assert get_clock_offset() == 7200

        # Advance to T0 + 25 minutes (10 minutes after second change: should NOT have reverted)
        sim_time = t0 + timedelta(minutes=25)
        assert get_clock_offset() == 7200

        # Advance to T0 + 36 minutes (21 minutes after second change: should revert)
        sim_time = t0 + timedelta(minutes=36)
        assert get_clock_offset() == 0
    finally:
        set_clock_offset(0)
        reset_time_source()
        settings.DEMO_CLOCK_IDLE_MINUTES = original_setting


def test_clock_idle_offset_zero_unaffected() -> None:
    """Setting offset to 0 remains 0 and never triggers idle errors."""
    reset_time_source()
    original_setting = settings.DEMO_CLOCK_IDLE_MINUTES
    settings.DEMO_CLOCK_IDLE_MINUTES = 15

    try:
        set_clock_offset(0)
        assert get_clock_offset() == 0
        assert today() == now().date()
    finally:
        reset_time_source()
        settings.DEMO_CLOCK_IDLE_MINUTES = original_setting


def test_sim_clock_api_endpoint_idle_revert(client: TestClient) -> None:
    """GET /sim/clock and /api/v1/sim/clock lazily report offset 0 after idle threshold."""
    reset_time_source()
    original_setting = settings.DEMO_CLOCK_IDLE_MINUTES
    settings.DEMO_CLOCK_IDLE_MINUTES = 10

    t0 = datetime(2026, 10, 30, 12, 0, 0, tzinfo=UTC)
    sim_time = t0
    set_time_source(lambda: sim_time)

    try:
        set_clock_offset(7200)

        # Immediate API read: simulated is True
        res = client.get("/sim/clock")
        assert res.status_code == 200
        data = res.json()
        assert data["offset_seconds"] == 7200
        assert data["is_simulated"] is True

        # Advance past 10 minutes
        sim_time = t0 + timedelta(minutes=11)
        res2 = client.get("/sim/clock")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["offset_seconds"] == 0
        assert data2["is_simulated"] is False
    finally:
        set_clock_offset(0)
        reset_time_source()
        settings.DEMO_CLOCK_IDLE_MINUTES = original_setting
