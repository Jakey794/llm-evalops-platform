#!/bin/sh
set -eu

echo "Running database migrations..."
.venv/bin/alembic upgrade head

echo "Starting API on port ${PORT:-8000}..."
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
