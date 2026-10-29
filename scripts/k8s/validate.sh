#!/usr/bin/env bash
# Offline: no kubeconfig, credentials, API server, Docker daemon or live DB needed.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
for overlay in development production bootstrap full-k3s full-k3s-migrations; do
  KUBECONFIG=/dev/null kubectl kustomize "$ROOT/deploy/kubernetes/overlays/$overlay" > "$work/$overlay.yaml"
  python3 "$ROOT/scripts/check_deployment.py" --kubernetes "$work/$overlay.yaml"
done
for stage in migrations initialization/vector initialization/topics; do
  name=${stage//\//-}
  KUBECONFIG=/dev/null kubectl kustomize "$ROOT/deploy/kubernetes/$stage" > "$work/$name.yaml"
done
python3 "$ROOT/scripts/check_full_k3s.py" "$work/full-k3s.yaml"
python3 "$ROOT/scripts/test_full_k3s.py"
for script in "$ROOT"/scripts/k8s/*.sh; do bash -n "$script"; done
: "${KUBECONFORM:=kubeconform}"
"$KUBECONFORM" -strict -kubernetes-version 1.36.0 -summary "$work"/*.yaml
