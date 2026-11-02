#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
"${K[@]}" get pods,statefulsets,deployments,jobs,pvc,services,ingress
"${K[@]}" get events --sort-by=.lastTimestamp
"${K[@]}" top pods || true
"${K[@]}" top nodes || true
