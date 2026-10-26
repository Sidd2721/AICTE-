from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.api.routes import bank, clock, worker
from app.core.config import settings
from app.domain.clock import today
from app.domain.rules import RULES_DIR, load_rule, startup_guard

FRONTEND_DIR = Path(__file__).parent / "frontend"


def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags else "api"
    return f"{tag}-{route.name}"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
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
    openapi_url=None
    if settings.FASTAPI_ENV == "demo"
    else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if settings.FASTAPI_ENV == "demo" else "/docs",
    redoc_url=None if settings.FASTAPI_ENV == "demo" else "/redoc",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)


@app.middleware("http")
async def add_security_headers(
    request: Request, call_next: Callable[[Request], Any]
) -> Response:
    response: Response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
        "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_HOST],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clock.router)
app.include_router(bank.router)
app.include_router(worker.router)
app.include_router(api_router, prefix=settings.API_V1_STR)


if FRONTEND_DIR.is_dir():
    app.frontend("/", directory=FRONTEND_DIR)
