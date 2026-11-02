#!/usr/bin/env bash
set -Eeuo pipefail

# Runs on the existing Oracle VM through GitHub Actions SSH.
TAG="${1:?Usage: deploy-relay-k3s.sh sha-<40-char-commit>}"
[[ "$TAG" =~ ^sha-[a-f0-9]{40}$ ]] || { echo 'Invalid release tag' >&2; exit 1; }

NAMESPACE=relay
REGISTRY=ghcr.io/shaad4

# The current Oracle user operates K3s with sudo kubectl.
k() { sudo -n kubectl -n "$NAMESPACE" "$@"; }

# Format: deployment:container:image-name
TARGETS=(
  api-gateway:api-gateway:api-gateway
  auth-service:auth-service:auth-service
  workflow-service:workflow-service:workflow-service
  integration-service:integration-service:integration-service
  action-service:action-service:action-service
  execution-service:execution-service:execution-service
  rag-service:rag-service:rag-service
  frontend:frontend:frontend
  relay-mcp:relay-mcp:mcp
  integration-celery-worker:integration-celery-worker:integration-service
  integration-celery-beat:integration-celery-beat:integration-service
  rag-celery-worker:rag-celery-worker:rag-service
)

# Ensure all Deployment names exist before changing any of them.
for item in "${TARGETS[@]}"; do
  IFS=: read -r deployment container image <<< "$item"
  k get deployment "$deployment" >/dev/null
done

for item in "${TARGETS[@]}"; do
  IFS=: read -r deployment container image <<< "$item"
  image_ref="$REGISTRY/relay-$image:$TAG"
  echo "Deploying $deployment → $image_ref"

  if [[ "$deployment" == relay-mcp ]]; then
    # MCP currently has imagePullPolicy: Never; switch it with the image atomically.
    k patch deployment relay-mcp --type=strategic -p \
      "{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"relay-mcp\",\"image\":\"$image_ref\",\"imagePullPolicy\":\"IfNotPresent\"}]}}}}"
  else
    k set image "deployment/$deployment" "$container=$image_ref"
  fi

  k rollout status "deployment/$deployment" --timeout=10m
done

# The public site should remain reachable after the rollout.
curl --fail --silent --show-error --location --max-time 20 \
  --output /dev/null https://relay.shaad.site/

echo "Release $TAG deployed successfully."