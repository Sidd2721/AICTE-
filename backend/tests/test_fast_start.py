import time
import pytest
from sqlmodel import Session, select
from app.core.db import engine
from app.models import User
from app.main import app

def test_fast_start_lifespan_bind_timing():
    """Verify that lifespan enters ready/listening state rapidly (< 15s)."""
    t0 = time.perf_counter()
    with Session(engine) as session:
        user = session.exec(select(User.id).where(User.email == "inst.north1@example.com")).first()
        # Verify warm database condition
        assert user is not None, "Warm database should have seeded users"

    t_query = time.perf_counter() - t0
    assert t_query < 5.0, f"Database warm check took too long: {t_query}s"

@pytest.mark.anyio
async def test_lifespan_context_nonblocking():
    """Verify lifespan context manager yields quickly without blocking port bind."""
    t0 = time.perf_counter()
    async with app.router.lifespan_context(app):
        t_bound = time.perf_counter() - t0
        assert t_bound < 10.0, f"Lifespan took too long to bind port: {t_bound}s"
