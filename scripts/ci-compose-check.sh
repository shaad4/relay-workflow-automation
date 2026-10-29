#!/usr/bin/env bash
# Offline config rendering only. No docker build/up, database or provider access.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
if [[ -n "${COMPOSE_BIN:-}" ]]; then
  compose=("$COMPOSE_BIN")
else
  compose=(docker compose)
fi
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
chmod 700 "$tmp"
cp .env.example "$tmp/development.env"
"${compose[@]}" --env-file "$tmp/development.env" -f docker-compose.yml config --quiet
"${compose[@]}" --env-file "$tmp/development.env" -f docker-compose.yml config --format json > "$tmp/development.json"
python scripts/check_deployment.py --compose "$tmp/development.json"
for service in api-gateway auth-service workflow-service integration-service action-service execution-service rag-service; do
  cp "service/$service/.env.example" "$tmp/$service.env"
  chmod 600 "$tmp/$service.env"
done
cp deploy/docker/production.env.example "$tmp/production.env"
printf '\nRELAY_ENV_DIR=%s\nRELAY_PRIVATE_BIND_IP=192.0.2.10\nKAFKA_PRIVATE_HOST=relay-infra.example.internal\n' "$tmp" >> "$tmp/production.env"
"${compose[@]}" --env-file "$tmp/production.env" \
  -f docker-compose.yml -f docker-compose.production.yml config --quiet
"${compose[@]}" --env-file "$tmp/production.env" \
  -f docker-compose.yml -f docker-compose.production.yml config --format json > "$tmp/production.json"
python scripts/check_deployment.py --production-compose "$tmp/production.json"
"${compose[@]}" --env-file "$tmp/production.env" \
  -f docker-compose.yml -f docker-compose.hybrid.yml config --quiet
"${compose[@]}" --env-file "$tmp/production.env" \
  -f docker-compose.yml -f docker-compose.hybrid.yml config --format json > "$tmp/hybrid.json"
python scripts/check_deployment.py --compose "$tmp/hybrid.json"
printf 'Development, production and private hybrid Compose configurations rendered successfully.\n'
