#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
wait_infra
manifest=$(mktemp)
trap 'rm -f "$manifest"' EXIT
render "$ROOT/deploy/kubernetes/initialization/topics" >"$manifest"
run_jobs "$manifest"
