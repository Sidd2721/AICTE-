from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.api.routes import bank, clock
from app.core.config import settings
from app.domain.clock import today
from app.domain.rules import RULES_DIR, load_rule, startup_guard

FRONTEND_DIR = Path(__file__).parent / "frontend"


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Invariant I7: outside development, refuse to start while any rule is DEMO
    names = ["deposit", "timelines", "release_paths"]
    try:
        docs = [load_rule(RULES_DIR, name, today()) for name in names]
        startup_guard(docs, settings.FASTAPI_ENV)
    except Exception as e:
        if settings.FASTAPI_ENV != "development":
            raise RuntimeError(f"Startup guard failed: {e}") from e
    yield


if settings.SENTRY_DSN and settings.FASTAPI_ENV != "development":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_HOST],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clock.router)
app.include_router(bank.router)
app.include_router(api_router, prefix=settings.API_V1_STR)

if FRONTEND_DIR.is_dir():
    app.frontend("/", directory=FRONTEND_DIR)
