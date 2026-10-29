#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
# Development only. No host networking/firewall changes, data resets or migrations.
# The root .env configures Compose; existing service .env files retain precedence.
if [[ ! -f .env ]]; then
  (umask 077; cp .env.example .env)
  echo "Created local-development .env; review it before using real data."
fi
docker compose config --quiet
docker compose build
docker compose up -d --wait --wait-timeout 180 auth-postgres workflow-postgres integration-postgres action-postgres execution-postgres rag-postgres rag-redis kafka
docker compose up -d kafka-init
docker compose wait kafka-init
echo "Infrastructure started. Run explicit migrations for a new database:"
echo "  ./scripts/migrate.sh"
echo "Then start apps: docker compose up -d --wait --wait-timeout 180"
echo "Frontend: cd frontend && npm ci && npm run dev (or add --profile frontend)"
