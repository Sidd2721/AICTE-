#!/usr/bin/env bash
# AICTE FDR Portal — Production Build Script
set -e

echo "=== [1/3] Building Production Frontend Assets ==="
cd frontend
if command -v bun &> /dev/null; then
    bun install --frozen-lockfile || bun install
    bun run build
elif command -v npm &> /dev/null; then
    npm ci || npm install
    npm run build
else
    echo "Error: Neither bun nor npm found on PATH" >&2
    exit 1
fi
cd ..

echo "=== [2/3] Installing Backend Dependencies ==="
if command -v uv &> /dev/null; then
    uv sync --frozen --no-dev --package app || uv sync --package app
else
    python3 -m pip install -r backend/requirements.txt || python3 -m pip install -e backend
fi

echo "=== [3/3] Build Completed Successfully ==="
ls -lh backend/app/frontend/index.html
