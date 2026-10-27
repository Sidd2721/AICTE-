from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.api.routes import bank, clock, integration_v1, worker
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

    # Ensure demo database has initial seed data if unseeded in dev/demo
    if settings.FASTAPI_ENV in ("development", "demo") and settings.AUTO_SEED:
        try:
            from sqlmodel import Session, select

            from app.core.db import engine, init_db
            from app.models import User
            from app.seed_rich_synthetic_data import seed_rich_data

            with Session(engine) as session:
                has_demo = session.exec(
                    select(User).where(User.email == "inst.north1@example.com")
                ).first()
                if not has_demo:
                    init_db(session)
                    seed_rich_data()
        except Exception:
            pass

    yield


if settings.SENTRY_DSN and settings.FASTAPI_ENV != "development":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
    if settings.FASTAPI_ENV == "development"
    else None,
    docs_url="/docs" if settings.FASTAPI_ENV == "development" else None,
    redoc_url="/redoc" if settings.FASTAPI_ENV == "development" else None,
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)


@app.middleware("http")
async def guard_docs_outside_dev(
    request: Request, call_next: Callable[[Request], Any]
) -> Response:
    path = request.url.path
    if path in ("/docs", "/redoc", f"{settings.API_V1_STR}/openapi.json"):
        if settings.FASTAPI_ENV != "development":
            return Response(
                status_code=404, content=b"Not Found", media_type="text/plain"
            )
    response: Response = await call_next(request)
    return response


@app.middleware("http")
async def integration_v1_middleware(
    request: Request, call_next: Callable[[Request], Any]
) -> Response:
    if request.url.path.startswith("/api/integration/v1"):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:
            return Response(
                status_code=413,
                content=b'{"code":"PAYLOAD_TOO_LARGE","message":"Request body exceeds 10MB limit","details":{},"request_id":"req_err"}',
                media_type="application/json",
            )

        import uuid

        from sqlmodel import Session

        from app.core.db import engine
        from app.core.rate_limit import check_rate_limit, ensure_rate_limit_table

        api_key = request.headers.get("x-api-key")
        client_ip = request.client.host if request.client else "127.0.0.1"
        key_id = api_key[:32] if api_key else client_ip
        rate_key = f"rl:integration:{key_id}"

        try:
            with Session(engine) as session:
                ensure_rate_limit_table(session)
                allowed, retry_after = check_rate_limit(
                    session, key=rate_key, max_requests=100, window_seconds=60
                )
        except Exception:
            allowed, retry_after = True, 0

        if not allowed:
            headers = {
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(retry_after),
            }
            body = (
                f'{{"code":"RATE_LIMIT_EXCEEDED","message":"Rate limit exceeded. Please retry later.",'
                f'"details":{{"retry_after":{retry_after}}},"request_id":"req_{uuid.uuid4().hex[:12]}"}}'
            ).encode()
            return Response(status_code=429, content=body, media_type="application/json", headers=headers)

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = "100"
        response.headers["X-RateLimit-Remaining"] = "99"
        response.headers["X-RateLimit-Reset"] = "60"
        return response

    res: Response = await call_next(request)
    return res


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
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
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
app.include_router(integration_v1.router)
app.include_router(api_router, prefix=settings.API_V1_STR)


if FRONTEND_DIR.is_dir():
    app.frontend("/", directory=FRONTEND_DIR)
