#!/bin/sh
set -e

echo "[db] running alembic migrations"
uv run alembic upgrade head

echo "[api] starting application"
exec "$@"
