#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
for name in auth-postgres workflow-postgres integration-postgres action-postgres execution-postgres rag-postgres kafka-kraft relay-jwt relay-auth-service relay-workflow-service relay-integration-service relay-action-service relay-execution-service relay-rag-service; do
  "${K[@]}" get secret "$name" -o name >/dev/null
done
manifest=$(mktemp)
trap 'rm -f "$manifest"' EXIT
render "$FULL_K3S_OVERLAY" >"$manifest"
python3 "$ROOT/scripts/k8s/render.py" infrastructure "$manifest" | "${K[@]}" apply -f -
wait_infra
