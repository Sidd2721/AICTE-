"""Daily background worker for PS 26265 FDR obligations under PostgreSQL advisory lock."""

import asyncio
import logging

from sqlmodel import Session

from app.core.db import engine
from app.domain.worker import run_daily_obligations_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_daily_job() -> None:
    logger.info("daily_worker: starting daily obligations check under advisory lock")
    with Session(engine) as session:
        result = run_daily_obligations_job(session)
        logger.info("daily_worker: finished with result %s", result)


if __name__ == "__main__":
    asyncio.run(run_daily_job())
