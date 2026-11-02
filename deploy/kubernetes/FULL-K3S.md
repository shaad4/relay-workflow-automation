# Full K3s on a single Oracle VM

This opt-in mode runs all eleven application/worker Deployments, six PostgreSQL
StatefulSets, Kafka and Redis inside namespace `relay`. Docker Compose is not a
runtime dependency. The existing development/production/bootstrap overlays retain
their hybrid behavior. [Docker Compose](../docker/README.md) remains a complete
self-hosted alternative; see [hybrid instructions](README.md) for external state.

Repository validation is not evidence of a working cluster deployment. These
commands are for an operator to review and run later. No script provisions OCI,
alters firewall/DNS, stops Compose, deletes PVCs, or automatically issues TLS.
Single-node K3s has **no high availability**. local-path data belongs to this VM.

## Capacity and storage gate

| Component | CPU requests | Memory requests | Memory limits |
| --- | ---: | ---: | ---: |
| Six PostgreSQL instances | 150m | 768 MiB | 3072 MiB |
| Kafka, 256–768 MiB Java heap | 25m | 512 MiB | 1536 MiB |
| Redis, 192 MiB dataset ceiling | 25m | 128 MiB | 640 MiB |
| Seven FastAPI services | 400m | 1024 MiB | 3072 MiB |
| Integration worker and Beat | 100m | 224 MiB | 640 MiB |
| RAG worker | 100m | 256 MiB | 1024 MiB |
| Next.js frontend | 100m | 128 MiB | 512 MiB |
| K3s control plane (planning allowance) | 200–400m | 768–1280 MiB | host process |
| Traefik, CoreDNS, metrics, local-path (allowance) | 100–200m | 256–512 MiB | inspect cluster |
| OS, page cache, safety margin (allowance) | remaining | 1.5–2 GiB | host memory |

Actual manifest requests total **900m CPU / 3040 MiB RAM**. Limits total
**10496 MiB**: simultaneous peaks plus the host can exceed 12 GiB. CPU limits are
oversubscribed; two cores will throttle under ingestion/workflow load. Requests
are scheduling floors, not observed consumption. This is suitable only as a
low-traffic evaluation starting point, not a demonstrated production capacity.
One API replica each, one execution process, two active executions and one worker
process per Celery worker are retained. One Beat uses Recreate to avoid overlap.
RAG memory must be measured with real documents; ingestion can OOM at these limits.
Raise requests/limits only after checking host capacity, or reduce admitted load.
Migrations run sequentially before applications to avoid startup peaks.

PVC requests: 6 × 1 GiB Postgres + 2 GiB Kafka + 1 GiB Redis = **9 GiB**.
local-path requests do NOT preallocate or enforce disk quotas. Kafka retains 24h
and 128 MiB per topic partition (four initial partitions; internal topics and
active segments add overhead); retention cleanup is asynchronous. DB WAL, vectors,
Redis AOF rewrites, images, snapshots and logs can all grow beyond PVC requests.

With only 19 GB free, **measure before proceeding**: `df -h`, `docker system df`,
`sudo k3s ctr images ls`, and `sudo du -sh /var/lib/rancher/k3s/*` on the target.
Docker and containerd image stores coexist, and unpacked images need additional
space. Do not assume 19 GB suffices. Stop if importing images and expected data
would leave less than 5 GiB free; provision more free capacity or decline this
installation. Do not delete existing Docker objects to make room automatically.
Running Compose and K3s simultaneously also exceeds the budget; plan a separately
approved Compose stop after backing up anything needed. No script stops it.

Alert on >75% disk use, <5 GiB free, >80% sustained node memory, restarts,
Pending Pods, Kafka lag and Redis rejected writes. Use `scripts/k8s/status.sh`,
`kubectl --context "$KUBE_CONTEXT" top pods -n relay`, host `free -h` and `df -h`.
Configure bounded K3s container log rotation through the host's normal reviewed
operations. Review Kafka retention, database history retention and vector growth.
Remove old image tags/logs/backups only after explicit operator review; never
remove active PVC paths or Kafka metadata. Keep backups on a separate machine.

## 1. Review context and prepare local configuration

Prerequisites: existing K3s with local-path, Traefik, enforced NetworkPolicy,
amd64 node; kubectl with Kustomize support, Python 3 + PyYAML, Docker for existing
image export, and target-node sudo access for containerd import. Install no paid
cloud services. Confirm the actual Kubernetes version (`kubectl version`); schema
validation is also run against a pinned Kubernetes schema, not a promise about a
future K3s release.

```bash
export KUBE_CONTEXT=your-reviewed-k3s-context
kubectl config get-contexts
bash scripts/k8s/preflight.sh
```

Create a private local customization overlay, ignored by Git:

```bash
mkdir -p deploy/kubernetes/overlays/full-k3s-local
cp deploy/kubernetes/overlays/full-k3s/configmap-patch.yaml deploy/kubernetes/overlays/full-k3s-local/public-config.yaml
```

Create its `kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: relay
resources:
- ../full-k3s
patches:
- path: public-config.yaml
- target:
    kind: Ingress
    name: relay
  patch: |-
    - op: replace
      path: /spec/rules/0/host
      value: YOUR_HOSTNAME
    - op: replace
      path: /spec/tls/0/hosts/0
      value: YOUR_HOSTNAME
```

Edit all public URLs in `public-config.yaml` to your existing HTTPS hostname,
including both OAuth callbacks; set SMTP and optional provider configuration as
needed. Keep `API_GATEWAY_URL=http://api-gateway:8000` internal. Export:

```bash
export FULL_K3S_OVERLAY="$PWD/deploy/kubernetes/overlays/full-k3s-local"
export RELAY_PUBLIC_HOST=your-existing-hostname
kubectl kustomize "$FULL_K3S_OVERLAY" > /tmp/relay-full-k3s-reviewed.yaml
python scripts/check_full_k3s.py /tmp/relay-full-k3s-reviewed.yaml
```

Only the frontend is exposed through Traefik. The existing server-side Next.js
proxy uses `/api/relay` and forwards cookies. Retain size/timeouts suitable for
document uploads (12 MiB body limit, 120s proxy timeout by default). No existing
application WebSocket routes were found in the audit. Traefik supports upgrades,
but the existing Next.js HTTP proxy strips hop-by-hop upgrade headers and is not
a WebSocket tunnel. If a future feature needs WebSockets, implement and test a
dedicated frontend upgrade path before enabling it; ingress alone cannot add it. Use secure
same-origin cookies, register the exact OAuth callback URLs with providers, and
verify redirects and email links. Never expose secrets via `NEXT_PUBLIC_*`.

## 2. Fresh infrastructure credentials, preserved application keys

Copy the existing `secrets/*.yaml.example` files to a **private directory outside
the checkout** (e.g. `$HOME/relay-app-secrets-input`) and populate the existing JWT,
Fernet/BYOK keys, SMTP and optional AI/storage/OAuth credentials. Keep filenames
ending `.yaml`. Their temporary DATABASE_URL and Redis values will be replaced
by the preparation tool. No Compose databases or passwords are reused. Database
names are `auth_db`, `workflow_db`, `integration_db`, `action_db`, `execution_db`,
`rag_db`, each owned by its corresponding `<service>_user`.

```bash
python3 scripts/k8s/create-secrets.py \
  --application-secrets "$HOME/relay-app-secrets-input" \
  --output "$HOME/relay-full-k3s-secrets"
kubectl --context "$KUBE_CONTEXT" apply -f deploy/kubernetes/base/namespace.yaml
kubectl --context "$KUBE_CONTEXT" -n relay apply -f "$HOME/relay-full-k3s-secrets"
```

The tool refuses an existing output directory, creates mode-0600 files under a
mode-0700 directory, prints no values, creates six independent random DB passwords
and a stable KRaft UUID, and preserves application credentials. Review files
privately; never `cat` them into shared logs. Back up the generated files securely.
Reapply the SAME files for repeat setup. Do not regenerate credentials after PVC
initialization: PostgreSQL bootstrap env does not rotate an existing role password.
Use explicit SQL credential rotation and coordinated Secret/application updates.
Do not change Kafka CLUSTER_ID after initialization; startup refuses mismatches.
Kubernetes Secrets are base64 objects, not automatically encrypted backups; restrict
kubeconfig/RBAC and configure cluster encryption at rest separately.

Supply your existing certificate and key (no certificate automation or DNS edits):

```bash
kubectl --context "$KUBE_CONTEXT" -n relay create secret tls relay-tls \
  --cert=/private/path/fullchain.pem --key=/private/path/privkey.pem
```

For renewal, generate a reviewed Secret manifest with `--dry-run=client -o yaml`
and pipe directly to `kubectl --context "$KUBE_CONTEXT" -n relay apply -f -`.

## 3. Import existing images

Reuse the seven existing `relay/*-service:dev` / `relay/api-gateway:dev` images.
Build only missing/stale images, on a machine with enough capacity. Frontend:

```bash
docker build --platform linux/amd64 -t relay/frontend:dev frontend
```

No deployment URL or credentials are build arguments. On the reviewed K3s node:

```bash
export K3S_LOCAL_IMPORT=yes
bash scripts/k8s/import-images.sh
```

The script uses `docker save <all-eight-tags> | sudo k3s ctr images import -` and
checks amd64 images. For a separate build machine, export and securely transfer:

```bash
docker save relay/frontend:dev -o /large-disk/relay-frontend.tar
sudo k3s ctr images import /large-disk/relay-frontend.tar
```

Repeat for the other seven images. Ensure this is the node belonging to the
selected context; local containerd import cannot target a remote context. All
workloads use IfNotPresent. Official stateful images pull normally unless you also
import them. Reusing a mutable `dev` tag can leave stale images; use immutable tags
or image digests for releases. Add matching `images:` overrides for ALL eight app
images in your local overlay and ALL six migration images in a separate local
migration overlay based on `../full-k3s-migrations`; export
`FULL_K3S_MIGRATIONS` to it. `IMAGE_TAG` only selects image exports, not manifests.
No unnecessary application rebuild is performed by deployment scripts.

## 4. Controlled installation

Review each stage's output before running the next. Infrastructure rollout also
installs namespace ConfigMap, service account, internal Services and policies,
but excludes application Deployments and Ingress. It verifies required Secrets
exist. Do not apply the full overlay directly on a fresh database.

```bash
bash scripts/k8s/deploy-infrastructure.sh
bash scripts/k8s/migrate.sh
bash scripts/k8s/init-topics.sh
bash scripts/k8s/deploy-apps.sh
bash scripts/k8s/verify.sh
```

Postgres/Kafka/Redis must become ready first. `migrate.sh` refuses running app
replicas, initializes vector in `rag_db` with a separate explicit Job, then runs
the existing six Alembic Jobs sequentially. No DB startup command runs migrations.
Topics are created with `--if-not-exists` and replication factor 1. Existing PVCs
are reused; Kafka formats only missing metadata on empty log storage and refuses
nonempty storage with missing metadata. PostgreSQL image initialization occurs
only on empty PGDATA. No data reset is part of startup.

Jobs are retained until their configured TTL (migration Jobs: 24h). Completed Jobs
are reused by scripts. A failed/incomplete Job stops the stage. For a deliberate
rerun, inspect `describe job/NAME`, Pod logs and migration state; explicitly delete
ONLY that Job (`kubectl --context "$KUBE_CONTEXT" -n relay delete job NAME`), then
rerun its stage. This does not delete PVCs. A completed vector Job is not evidence
that a later replacement DB has the extension: rerun it after a restore/replacement.
For a new release, explicitly remove reviewed completed migration Jobs to run new
migrations. If TTL has removed Jobs before app startup, rerun migration/topic
stages before `deploy-apps.sh`. Never blindly retry partially applied DDL.

## 5. Verify behavior

`verify.sh` checks StatefulSet and Deployment rollouts, not business correctness.
Also check HTTPS without `-k`, sign in, refresh/logout cookies, OAuth callback,
email links, a full workflow lifecycle (all four Kafka topics), and RAG upload /
retrieval. Test private ports from outside the VM: none should be reachable.
Check `kubectl --context "$KUBE_CONTEXT" -n relay get networkpolicy,endpointslices`.
Validate policies with your actual K3s CNI and Traefik labels; an offline manifest
cannot prove network enforcement. Observe Kafka advertised broker DNS from a Pod.

Redis uses logical DB 0 for RAG and DB 1 for Integration. AOF everysec can lose
approximately the latest second on a crash; noeviction rejects new writes at the
memory ceiling instead of silently evicting queued jobs. Monitor failures, retry
publishes and reconcile task status; this is not an exactly-once queue guarantee.
AOF rewrites need memory and disk headroom. No password is configured: default-deny
and namespace-local NetworkPolicies protect this internal broker. Applications and
initialization Jobs labeled as Relay are trusted peers; they can reach all six
DBs, Redis and Kafka. This retains the existing broad intra-Relay trust model,
not per-service authorization. PostgreSQL bootstrap users own only their isolated
instance but are image-created superusers; least-privilege runtime roles require
a separate credential/role rollout. Kafka is internal PLAINTEXT, no public listener.
External HTTP(S) AI/storage/OAuth and SMTP allowances are retained; no cloud IAM,
public gRPC, database service, or Kubernetes API access is added. Review these
limits before treating this deployment as a multi-tenant production boundary.

## Updates, rollback and recovery

For updates, back up first; explicitly scale all eleven app Deployments to zero
and wait for Pods to drain (execution: 180s, RAG worker: 720s). Do not stop the
stateful services. Import reviewed immutable images and update both overlays,
remove only reviewed completed migration Jobs, run migrations, topics and apps.
Use `kubectl --context "$KUBE_CONTEXT" -n relay rollout history deployment/NAME`
and `rollout undo deployment/NAME` for application rollback only when the database
schema is backward compatible. Reapply the previous pinned overlay to keep GitOps
state consistent. No automatic downgrade or database rollback is attempted.
Never scale Beat or execution-service beyond one without concurrency review.

Take consistent logical backups of **all six** databases plus application keys.
For each service, stream to a secure file on another machine (example auth):

```bash
kubectl --context "$KUBE_CONTEXT" -n relay exec auth-postgres-0 -- \
  sh -ec 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > /secure/external/backup/auth.dump
```

Check exit status and periodically restore-test; use `pg_dumpall --globals-only`
for role definitions if adding custom roles. Back up Kafka/Redis by stopping
producers/workers, cleanly stopping their StatefulSets, and taking consistent copies
of entire PVC data directories (including Kafka meta.properties, Redis multipart
AOF files and manifests). Never copy active data directories as a claimed
consistent backup. Use host tooling under a separately reviewed maintenance
procedure; local-path snapshots alone are not off-VM protection. Restart one
replica afterward. Kafka retention is not a backup policy.

Restore into fresh PVCs in an isolated test environment with matching original
credentials and Kafka cluster ID. Start PostgreSQL, initialize pgvector, then
restore dumps with `pg_restore --exit-on-error` targeting the correct DB (do not
restore over running production data). Restore Kafka/Redis directories while
stopped, with correct ownership. Verify extension/schema versions, queues and
Kafka offsets before enabling applications. Do not run fresh migrations blindly
over a dump from an incompatible release. Keep the old environment intact until
restore tests and workflows succeed.

Troubleshooting: Pending PVC → local-path/node disk; Pending Pods → allocatable
requests; CrashLoop/OOMKilled → describe Pod and memory pressure; Kafka restart →
verify log ownership, stable UUID and meta.properties (never reformat to fix);
DB auth failure → compare original Secret and initialized role; migration failure
→ inspect Job logs privately and Alembic version; worker not ready → broker DNS,
NetworkPolicy, Redis memory/AOF errors; frontend 502 → gateway readiness, internal
URL and proxy timeout; login loop → public HTTPS origin, cookie settings and
forwarded headers. Do not paste logs containing URLs/credentials into public issues.

Optional RAG ingestion still uses the existing Supabase storage and embedding
provider contracts. This change adds no paid infrastructure and does not replace
those application integrations; use existing/free allowances or leave those
features unused. Full self-hosted RAG object storage is outside this change.

## Offline validation

Run `KUBECONFIG=/dev/null bash scripts/k8s/validate.sh` (kubectl, Python/PyYAML,
and kubeconform v0.7.0 required). Schema validation downloads public Kubernetes
1.36.0 schemas; no Kubernetes API is contacted. Run `bash scripts/ci-compose-check.sh`
for all three Compose configurations. CI runs these contract/schema checks alongside
the existing backend/frontend/image checks. See [validation evidence](VALIDATION.md).

Design references: [Apache Kafka Docker documentation](https://kafka.apache.org/40/getting-started/docker/)
and [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/).
