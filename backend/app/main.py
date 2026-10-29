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


# In-memory seeding flag (V3): protects /ready until initial demo data completes
_seed_completed: bool = True


def is_seed_completed() -> bool:
    return _seed_completed


def set_seed_completed(val: bool) -> None:
    global _seed_completed
    _seed_completed = val


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    import asyncio
    import logging
    import time

    global _seed_completed
    import os
    is_testing = bool(os.environ.get("PYTEST_CURRENT_TEST"))
    if not is_testing and settings.FASTAPI_ENV in ("development", "demo") and settings.AUTO_SEED:
        _seed_completed = False
    else:
        _seed_completed = True

    t_start = time.perf_counter()
    logger = logging.getLogger("uvicorn.info")

    # Invariant I7: outside development, refuse to start while any rule is DEMO
    names = ["deposit", "timelines", "release_paths"]
    try:
        docs = [load_rule(RULES_DIR, name, today()) for name in names]
        startup_guard(docs, settings.FASTAPI_ENV)
    except Exception as e:
        if settings.FASTAPI_ENV != "development":
            raise RuntimeError(f"Startup guard failed: {e}") from e

    # FT3: Vault key security and directory writability guard
    try:
        from app.domain.vault import check_vault_writable, validate_vault_security

        validate_vault_security(settings.FASTAPI_ENV)
        if not check_vault_writable():
            if settings.FASTAPI_ENV == "production":
                raise PermissionError(
                    "Production startup aborted: Vault directory is not writable."
                )
            logger.warning(
                "[lifespan] Warning: Vault directory is not writable by current user."
            )
    except Exception as e:
        if settings.FASTAPI_ENV == "production":
            raise RuntimeError(f"Vault security check failed: {e}") from e
        logger.warning("[lifespan] Vault initialization notice: %s", e)

    # Ensure Supabase storage bucket exists if configured
    try:
        from app.integration.supabase_storage import ensure_bucket_exists

        ensure_bucket_exists()
    except Exception:
        pass

    def _sync_seed_worker() -> None:
        global _seed_completed
        if settings.FASTAPI_ENV in ("development", "demo") and settings.AUTO_SEED:
            try:
                from sqlmodel import Session, select

                from app.core.db import engine, init_db
                from app.models import User
                from app.seed_rich_synthetic_data import seed_rich_data

                with Session(engine) as session:
                    has_demo = session.exec(
                        select(User.id).where(User.email == "inst.north1@example.com")
                    ).first()
                    if not has_demo:
                        logger.info("[lifespan] Unseeded database detected; seeding initial demo data...")
                        init_db(session)
                        seed_rich_data()
                        logger.info("[lifespan] Initial demo data seeded successfully.")
                    else:
                        logger.info("[lifespan] Database already seeded; skipping redundant seed.")
            except Exception as e:
                logger.warning("[lifespan] Background seed notice: %s", e)
            finally:
                _seed_completed = True
        else:
            _seed_completed = True

    import os
    is_testing = bool(os.environ.get("PYTEST_CURRENT_TEST"))
    seed_task = None
    if not is_testing and settings.FASTAPI_ENV in ("development", "demo") and settings.AUTO_SEED:
        seed_task = asyncio.create_task(asyncio.to_thread(_sync_seed_worker))

    t_ready = time.perf_counter()
    logger.info(
        "[lifespan] Startup initialization complete in %.3fs; listening for traffic.",
        t_ready - t_start,
    )

    yield

    if seed_task is not None:
        try:
            await seed_task
        except Exception:
            pass


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
        from app.core.rate_limit import (
            check_rate_limit,
            ensure_rate_limit_table,
            get_client_ip,
        )

        api_key = request.headers.get("x-api-key")
        client_ip = get_client_ip(request)
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
            return Response(
                status_code=429,
                content=body,
                media_type="application/json",
                headers=headers,
            )

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
        "img-src 'self' data: blob: https:; font-src 'self'; "
        "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:* https://*.onrender.com https://*.supabase.co; "
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
    allow_origins=[
        settings.FRONTEND_HOST,
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"https?://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.PROJECT_NAME}


@app.get("/ready", include_in_schema=False)
@app.get("/api/ready", include_in_schema=False)
def readiness_check() -> Response:
    """Readiness probe checking database connectivity, migration head, and vault writability.

    Returns 200 {"status": "ready", "build": ...} if all systems are ready, or 503 {"status": "unready", "build": ...} otherwise.
    Excluded from public OpenAPI schema to preserve client contract stability.
    """
    import os

    from fastapi.responses import JSONResponse
    from sqlalchemy import text
    from sqlmodel import Session

    from app.core.db import engine
    from app.domain.vault import check_vault_writable

    render_commit = settings.RENDER_GIT_COMMIT or os.environ.get("RENDER_GIT_COMMIT")
    build_val = render_commit[:7] if render_commit and render_commit.strip() else "unknown"

    try:
        with Session(engine) as session:
            db_res = session.execute(text("SELECT 1")).scalar()
            if db_res != 1:
                return JSONResponse(status_code=503, content={"status": "unready", "build": build_val})

            ver_res = session.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ).scalar()
            expected_head = "d812bd6c915d"
            if ver_res != expected_head:
                return JSONResponse(status_code=503, content={"status": "unready", "build": build_val})
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unready", "build": build_val})

    if not check_vault_writable():
        return JSONResponse(status_code=503, content={"status": "unready", "build": build_val})

    if (
        settings.FASTAPI_ENV in ("development", "demo")
        and settings.AUTO_SEED
        and not _seed_completed
    ):
        return JSONResponse(
            status_code=503,
            content={"status": "unready", "reason": "seeding_in_progress", "build": build_val},
        )

    return JSONResponse(status_code=200, content={"status": "ready", "build": build_val})


app.include_router(clock.router)
app.include_router(bank.router)
app.include_router(worker.router)
app.include_router(integration_v1.router)
app.include_router(api_router, prefix=settings.API_V1_STR)


if FRONTEND_DIR.is_dir():
    app.frontend("/", directory=FRONTEND_DIR, fallback="index.html")
