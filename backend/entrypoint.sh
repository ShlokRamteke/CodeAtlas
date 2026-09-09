#!/bin/sh
set -e

echo "Waiting for PostgreSQL database connection..."
python - <<'EOF'
import os
import time
import socket
from urllib.parse import urlparse

db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@postgres:5432/codeatlas")
# Normalize scheme for parsing
clean_url = db_url.replace("postgresql+asyncpg://", "http://").replace("postgresql://", "http://")
parsed = urlparse(clean_url)
host = parsed.hostname or "postgres"
port = parsed.port or 5432

for attempt in range(30):
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"Connected to PostgreSQL at {host}:{port}")
            break
    except (socket.error, ConnectionRefusedError):
        print(f"Waiting for database at {host}:{port}... (attempt {attempt+1}/30)")
        time.sleep(1)
else:
    print("Database connection timed out.")
    exit(1)
EOF

echo "Running Alembic database migrations..."
alembic upgrade head

echo "Starting FastAPI application..."
exec "$@"
