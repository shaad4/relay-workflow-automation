#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
wait_infra
for name in api-gateway auth-service workflow-service integration-service action-service execution-service rag-service frontend integration-celery-worker integration-celery-beat rag-celery-worker; do
  "${K[@]}" rollout status "deployment/$name" --timeout=900s
done
"${K[@]}" get pods,pvc,services,ingress
printf 'Pod readiness passed. Separately test public HTTPS, cookies, OAuth, workflow execution and ingestion.\n'
