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

ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install uv from official binary
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# Install curl for container healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Create non-root system user
RUN groupadd -g 1001 appgroup && useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Install python dependencies with frozen lockfile
COPY pyproject.toml uv.lock* /app/
COPY backend/pyproject.toml backend/alembic.ini /app/backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package app || uv sync --package app

# Copy backend application source and scripts
COPY backend/app /app/backend/app
COPY backend/scripts /app/backend/scripts

# Copy compiled frontend from frontend stage
COPY --from=frontend-builder /app/backend/app/frontend /app/backend/app/frontend

# Create and grant permissions on data and vault directories
RUN mkdir -p /app/backend/vault && chmod +x /app/backend/scripts/*.sh && chown -R appuser:appgroup /app

WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/utils/health-check/ || exit 1

USER appuser

CMD ["bash", "/app/backend/scripts/start.sh"]
