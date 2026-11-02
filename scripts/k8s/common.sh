#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
: "${KUBE_CONTEXT:?Set KUBE_CONTEXT to the reviewed target context}"
: "${FULL_K3S_OVERLAY:=$ROOT/deploy/kubernetes/overlays/full-k3s}"
: "${FULL_K3S_MIGRATIONS:=$ROOT/deploy/kubernetes/overlays/full-k3s-migrations}"
K=(kubectl --context "$KUBE_CONTEXT" --namespace relay)
printf 'Kubernetes context: %s; namespace: relay\n' "$KUBE_CONTEXT"
render() { kubectl kustomize "$1"; }
wait_infra() {
  for name in auth-postgres workflow-postgres integration-postgres action-postgres execution-postgres rag-postgres kafka redis; do
    "${K[@]}" rollout status "statefulset/$name" --timeout=900s
  done
}
# Never delete/recreate completed or failed Jobs implicitly. Remove a reviewed Job explicitly to rerun.
run_jobs() {
  local manifest="$1" name names
  names=$(python3 "$ROOT/scripts/k8s/render.py" names "$manifest")
  [[ -n "$names" ]] || { echo "No Jobs found" >&2; return 1; }
  while read -r name; do
    if "${K[@]}" get "job/$name" >/dev/null 2>&1; then
      if [[ $("${K[@]}" get "job/$name" -o jsonpath='{.status.succeeded}') == 1 ]]; then
        printf 'Keeping completed Job %s\n' "$name"
      else
        echo "Existing incomplete Job $name: inspect it; explicit deletion required before retry" >&2; return 1
      fi
    else
      python3 "$ROOT/scripts/k8s/render.py" job "$manifest" "$name" | "${K[@]}" create -f -
    fi
    "${K[@]}" wait --for=condition=complete "job/$name" --timeout=900s
  done <<< "$names"
}
