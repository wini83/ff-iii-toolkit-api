#!/bin/sh
set -e

echo "[db] running alembic migrations"
alembic upgrade head

echo "[api] starting application"
exec "$@"
