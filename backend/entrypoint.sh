#!/bin/sh
set -e

# Run database migrations before starting the application
alembic upgrade head

# Start uvicorn (exec replaces shell process)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
