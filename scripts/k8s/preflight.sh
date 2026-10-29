#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
command -v python3 >/dev/null
python3 -c 'import yaml'
"${K[@]}" cluster-info
"${K[@]}" get nodes -o wide
"${K[@]}" get storageclass local-path
"${K[@]}" get nodes -o json | python3 -c 'import json,sys; nodes=json.load(sys.stdin)["items"]; assert len(nodes)==1, "Review single-node assumptions"; assert nodes[0]["status"]["nodeInfo"]["architecture"]=="amd64"'
render "$FULL_K3S_OVERLAY" >/dev/null
render "$FULL_K3S_MIGRATIONS" >/dev/null
printf 'Review allocatable CPU/memory, host df -h, image sizes, ingress hostname and TLS before proceeding. No changes made.\n'
