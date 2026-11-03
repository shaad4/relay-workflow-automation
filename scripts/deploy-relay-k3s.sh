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

# Provision storage independently of the Pod; never delete/recreate the claim.
# This script is streamed over SSH, so it carries this small storage contract.
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

for item in "${TARGETS[@]}"; do
  IFS=: read -r deployment container image <<< "$item"
  image_ref="$REGISTRY/relay-$image:$TAG"
  echo "Deploying $deployment → $image_ref"

  if [[ "$deployment" == relay-mcp ]]; then
    # Reconcile persistence together with the release image. An image-only update
    # previously left production using :memory: despite the PVC being Bound.
    k patch deployment relay-mcp --type=strategic --patch-file /dev/stdin <<MCP_PATCH
{
  "spec": {
    "replicas": 1,
    "strategy": {"type": "Recreate", "rollingUpdate": null},
    "template": {
      "spec": {
        "securityContext": {"fsGroup": 10001},
        "containers": [{
          "name": "relay-mcp",
          "image": "$image_ref",
          "imagePullPolicy": "IfNotPresent",
          "env": [{"name": "MCP_CLIENT_DB_PATH", "value": "/data/oauth.sqlite", "valueFrom": null}],
          "volumeMounts": [{"name": "oauth-data", "mountPath": "/data"}]
        }],
        "volumes": [{"name": "oauth-data", "persistentVolumeClaim": {"claimName": "relay-mcp-data"}}]
      }
    }
  }
}
MCP_PATCH
  else
    k set image "deployment/$deployment" "$container=$image_ref"
  fi

  k rollout status "deployment/$deployment" --timeout=10m
  if [[ "$deployment" == relay-mcp ]]; then
    # Read-only runtime verification: fail the release if the active process would
    # use a different path or if the durable schema cannot be read from the mount.
    k exec deployment/relay-mcp -- python -B -c '
import os, sqlite3
assert os.environ.get("MCP_CLIENT_DB_PATH") == "/data/oauth.sqlite"
assert os.path.ismount("/data"), "OAuth PVC is not mounted"
db = sqlite3.connect("file:/data/oauth.sqlite?mode=ro", uri=True)
tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type = ?", ("table",))}
assert {"oauth_clients", "oauth_grants", "oauth_tokens"}.issubset(tables)
db.close()
print("MCP persistent OAuth storage verified")
'
  fi
done

# The public site should remain reachable after the rollout.
curl --fail --silent --show-error --location --max-time 20 \
  --output /dev/null https://relay.shaad.site/

echo "Release $TAG deployed successfully."
