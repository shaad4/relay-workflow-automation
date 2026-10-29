#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
# Run once, from one operator terminal, after a verified backup.
# Set COMPOSE_FILE and COMPOSE_ENV_FILES for production, as documented.
# The application image is reused; no schema reset/create_all occurs here.
# Check the exact application target before applying ANY service migrations.
# pgvector images install the binary, not the extension in each database.
echo "Checking the RAG database's pgvector prerequisite"
docker compose run --rm --no-deps -T rag-service python - <<'PY'
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


async def check_extension():
    engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
    try:
        async with asyncio.timeout(10):
            async with engine.connect() as connection:
                return await connection.scalar(
                    text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                )
    finally:
        await engine.dispose()


try:
    available = asyncio.run(check_extension())
except Exception:
    raise SystemExit("RAG database preflight failed; verify connectivity with your administrator.") from None
if not available:
    raise SystemExit(
        "RAG database is missing pgvector. Have an administrator run CREATE EXTENSION IF NOT EXISTS vector "
        "in the exact RAG DATABASE_URL database, then retry. No service migrations were started."
    )
print("RAG pgvector prerequisite satisfied")
PY
for service in auth-service workflow-service integration-service action-service execution-service rag-service; do
  echo "Migrating $service"
  docker compose run --rm --no-deps "$service" python -m alembic upgrade head
done
