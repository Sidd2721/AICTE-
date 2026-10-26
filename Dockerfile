# Multi-stage Dockerfile for AICTE FDR Portal Demo (Sprint 2 Track 2)
# Stage 1: Frontend compilation
FROM oven/bun:1 AS frontend-builder
WORKDIR /app
COPY frontend/package.json frontend/bun.lock* /app/frontend/
WORKDIR /app/frontend
RUN bun install --frozen-lockfile || bun install
COPY frontend/ /app/frontend/
RUN bun run build

# Stage 2: Production Python 3.14 runtime
FROM python:3.14-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install uv from official binary
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# Install curl for container healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml uv.lock* /app/
COPY backend/pyproject.toml backend/alembic.ini /app/backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --package app || uv sync --package app

# Copy backend application source and scripts
COPY backend/app /app/backend/app
COPY backend/scripts /app/backend/scripts

# Copy compiled frontend from frontend stage
COPY --from=frontend-builder /app/backend/app/frontend /app/backend/app/frontend

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
