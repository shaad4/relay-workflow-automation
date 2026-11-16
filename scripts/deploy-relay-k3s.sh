#!/usr/bin/env bash
set -Eeuo pipefail

# Runs on the existing Oracle VM through GitHub Actions SSH.
TAG="${1:?Usage: deploy-relay-k3s.sh sha-<40-char-commit>}"
[[ "$TAG" =~ ^sha-[a-f0-9]{40}$ ]] || {
  echo 'Invalid release tag' >&2
  exit 1
}

NAMESPACE=relay
REGISTRY=ghcr.io/shaad4

# The current Oracle user operates K3s with sudo kubectl.
k() { sudo -n kubectl -n "$NAMESPACE" "$@"; }

# ------------------------------------------------------------
# Ensure required frontend configuration exists.
# ------------------------------------------------------------

# The frontend /ready endpoint checks API Gateway readiness.
# A missing API_GATEWAY_URL causes HTTP 503 and blocks rollout.
k patch configmap relay-config --type=merge \
  -p '{"data":{"API_GATEWAY_URL":"http://api-gateway:8000"}}'

GATEWAY_URL="$(k get configmap relay-config \
  -o jsonpath='{.data.API_GATEWAY_URL}')"

if [[ "$GATEWAY_URL" != "http://api-gateway:8000" ]]; then
  echo "ERROR: API_GATEWAY_URL is incorrectly configured" >&2
  exit 1
fi

echo "API Gateway configuration verified: $GATEWAY_URL"

# ------------------------------------------------------------
# Deployment targets
# Format: deployment:container:image-name
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# MCP persistent storage
# ------------------------------------------------------------

# Provision storage independently of the Pod.
# Never delete or recreate the existing claim.
# This script is streamed over SSH, so it carries the
# storage contract.
k apply -f - <<'MCP_STORAGE'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: relay-mcp-data
  namespace: relay
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 1Gi
MCP_STORAGE

k get secret relay-mcp-secret >/dev/null

# ------------------------------------------------------------
# Update and verify deployments
# ------------------------------------------------------------

for item in "${TARGETS[@]}"; do
  IFS=: read -r deployment container image <<< "$item"

  image_ref="$REGISTRY/relay-$image:$TAG"
  echo "Deploying $deployment → $image_ref"

  if [[ "$deployment" == relay-mcp ]]; then

    # Reconcile persistence together with the release image.
    # An image-only update previously left production using
    # :memory: despite the PVC being Bound.
    k patch deployment relay-mcp \
      --type=strategic --patch-file /dev/stdin <<MCP_PATCH
{
  "spec": {
    "replicas": 1,
    "strategy": {
      "type": "Recreate",
      "rollingUpdate": null
    },
    "template": {
      "spec": {
        "securityContext": {
          "fsGroup": 10001
        },
        "containers": [{
          "name": "relay-mcp",
          "image": "$image_ref",
          "imagePullPolicy": "IfNotPresent",
          "env": [{
            "name": "MCP_CLIENT_DB_PATH",
            "value": "/data/oauth.sqlite",
            "valueFrom": null
          }],
          "volumeMounts": [{
            "name": "oauth-data",
            "mountPath": "/data"
          }]
        }],
        "volumes": [{
          "name": "oauth-data",
          "persistentVolumeClaim": {
            "claimName": "relay-mcp-data"
          }
        }]
      }
    }
  }
}
MCP_PATCH

  else
    k set image \
      "deployment/$deployment" \
      "$container=$image_ref"
  fi

  # Wait until the deployment becomes available.
  k rollout status "deployment/$deployment" --timeout=10m

  # Verify frontend readiness after rollout.
  if [[ "$deployment" == frontend ]]; then
    echo "Verifying frontend readiness..."

    k exec deployment/frontend -- node -e '
      fetch("http://127.0.0.1:3000/ready", {
        signal: AbortSignal.timeout(5000)
      })
        .then(async (response) => {
          if (!response.ok) {
            console.error(
              "Frontend readiness failed:",
              response.status,
              await response.text()
            );
            process.exit(1);
          }

          console.log("Frontend readiness verified");
        })
        .catch((error) => {
          console.error(error);
          process.exit(1);
        });
    '
  fi

  # Verify MCP persistent OAuth storage.
  if [[ "$deployment" == relay-mcp ]]; then
    k exec deployment/relay-mcp -- python -B -c '
import os
import sqlite3

assert os.environ.get("MCP_CLIENT_DB_PATH") == "/data/oauth.sqlite"
assert os.path.ismount("/data"), "OAuth PVC is not mounted"

db = sqlite3.connect(
    "file:/data/oauth.sqlite?mode=ro",
    uri=True
)

tables = {
    row[0]
    for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type = ?",
        ("table",)
    )
}

assert {
    "oauth_clients",
    "oauth_grants",
    "oauth_tokens"
}.issubset(tables)

db.close()
print("MCP persistent OAuth storage verified")
'
  fi
done

# ------------------------------------------------------------
# Verify public application availability
# ------------------------------------------------------------

curl --fail --silent --show-error --location --max-time 20 \
  --output /dev/null https://relay.shaad.site/

echo "Release $TAG deployed successfully."
