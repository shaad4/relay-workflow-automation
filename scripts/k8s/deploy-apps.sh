#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
: "${RELAY_PUBLIC_HOST:?Set reviewed public hostname}"
[[ "$RELAY_PUBLIC_HOST" != relay.example.com ]] || { echo 'Replace example hostname' >&2; exit 1; }
manifest=$(mktemp)
trap 'rm -f "$manifest"' EXIT
render "$FULL_K3S_OVERLAY" >"$manifest"
python3 - "$manifest" "$RELAY_PUBLIC_HOST" <<'PY'
import sys,yaml
objects=list(yaml.safe_load_all(open(sys.argv[1]))); host=sys.argv[2]
config=next(o['data'] for o in objects if o['kind']=='ConfigMap' and o['metadata']['name']=='relay-config')
assert config['FRONTEND_URL']=='https://'+host, 'Customize ConfigMap public URL in your local overlay'
assert config['BACKEND_URL']=='https://'+host+'/api/relay'
assert all(r['host']==host for o in objects if o['kind']=='Ingress' for r in o['spec']['rules']), 'Customize ingress hostname'
assert all(h==host for o in objects if o['kind']=='Ingress' for t in o['spec']['tls'] for h in t['hosts']), 'Customize TLS host'
PY
"${K[@]}" get secret relay-tls -o name >/dev/null
for name in rag-vector-init auth-service-migrate workflow-service-migrate integration-service-migrate action-service-migrate execution-service-migrate rag-service-migrate kafka-topics-init; do
  "${K[@]}" wait --for=condition=complete "job/$name" --timeout=5s
done
"${K[@]}" apply -f "$manifest"
bash "$ROOT/scripts/k8s/verify.sh"
