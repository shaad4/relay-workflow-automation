#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
# Refuse migrations while any application/worker replica exists. Maintenance is explicit.
"${K[@]}" get deployments -l app.kubernetes.io/part-of=relay -o json | python3 -c 'import json,sys; ds=json.load(sys.stdin)["items"]; assert all(d["spec"].get("replicas",1)==0 and d.get("status",{}).get("replicas",0)==0 for d in ds), "Stop and drain all Relay deployments before migrations"'
wait_infra
manifest=$(mktemp)
trap 'rm -f "$manifest"' EXIT
render "$ROOT/deploy/kubernetes/initialization/vector" >"$manifest"
run_jobs "$manifest"
render "$FULL_K3S_MIGRATIONS" >"$manifest"
run_jobs "$manifest"
