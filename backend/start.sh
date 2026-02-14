#!/bin/sh
set -e

echo "=== Replivo Starting ==="
echo "PORT: $PORT"
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo yes || echo no)"
echo "Running migrations..."

flask db upgrade 2>&1

echo "Migrations complete. Starting gunicorn on port $PORT..."

exec gunicorn wsgi:app \
    --bind "0.0.0.0:${PORT:-8080}" \
    --workers 2 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
