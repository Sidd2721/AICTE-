import logging

from sqlmodel import Session

from app.core.db import engine, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init() -> None:
    with Session(engine) as session:
        init_db(session)
    try:
        from app.seed_rich_synthetic_data import seed_rich_data

        seed_rich_data()
    except Exception as e:
        logger.warning("Rich synthetic data seed warning: %s", e)


def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":
    main()
