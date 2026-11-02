# Configuration Fix Status — 2026-11-02 21:01 IST

This update supersedes the historical audit's access limitation. Subsequently authorized `sudo -n kubectl` access worked. **Configuration files are reconciled; the live RAG database correction awaits explicit approval under Phase 3 of the fix request. No production mutations have been made.**

| Service | Problem | Confirmed root cause | Proposed/applied fix | Status |
|---|---|---|---|---|
| RAG API | 0/1; readiness 503 | Current DATABASE_URL raises InvalidPasswordError | Use existing generated credentials; authenticated SELECT 1 and current Alembic revision verified | Files prepared; live patch awaiting approval |
| RAG worker | 1/1 but DB unavailable | Process retains an older URL that fails DNS; broker-only readiness hides it | Refresh environment after the same Secret correction | Proposed URL also passes SELECT 1 from worker; restart pending |
| RAG Redis | Duplicate private broker entries | Conflicting CELERY_BROKER_URL mapping keys | Keep one existing working redis:6379 DB 0 value | Private files fixed; live broker unchanged |
| RAG Supabase | Clean production checkout lacked URL | Value was in live ConfigMap and a local base edit | Move existing public URL to full-k3s production patch | Render matches live; bucket metadata reads pass from API and worker |
| Private Secret copies | DB/broker/provider drift | Stale input files and generated RAG OpenAI value | Preserve current live credentials except verified proposed RAG DB correction | Sources synchronized; no credential rotation |
| Other services | Check for similar failures | No other DB authentication/readiness failures found | No production changes needed | Other 11 application Deployments and all eight StatefulSets ready |

## Files changed

Repository:
- `deploy/kubernetes/overlays/full-k3s/configmap-patch.yaml`: contains the existing Supabase URL. The base file returns to its committed empty development default; the effective production value remains unchanged.
- `deploy/kubernetes/FULL-K3S.md`: documents the authoritative private source, prohibition on regenerating initialized production credentials, and scoped approval/rollback process. No new pipeline or application logic.
- This existing report: records live findings and the pending change without credentials.

Private files under `/home/ubuntu/relay-k8s-private/`:
- `application-secrets/action-service.yaml`: DB and Google OAuth settings match current live values.
- `application-secrets/auth-service.yaml`, `execution-service.yaml`, and `workflow-service.yaml`: DB settings match current live values; encryption/JWT material unchanged.
- `application-secrets/integration-service.yaml`: DB and Redis DB 1 broker match current live values.
- `application-secrets/rag-service.yaml`: verified existing DB credentials and exactly one working Redis DB 0 broker; live provider keys retained.
- `generated/relay-rag-service.yaml`: existing valid database URL retained; OpenAI key synchronized to current live value. Credential validity was not tested through a paid request.

## Prepared production change — not applied

Change only **Secret `relay/relay-rag-service`, key `DATABASE_URL`**, to the existing valid generated connection. The host remains `rag-postgres:5432`; existing initialized database/user/password are reused. No database role, password, PVC, table, document or vector changes are needed.

Then restart only **Deployments `rag-service` and `rag-celery-worker`** to load the corrected URL. The worker needs this despite reporting 1/1 because its actual DB connection fails. Preserve its working Redis/Supabase configuration. Verify both are 1/1, API readiness is 200, both actual Pod environments pass authenticated read-only SELECT 1, and Redis/Supabase remain accessible. Do not rebuild images, run CD, migrate or restart unrelated services.

Protected preparation directory: `/home/ubuntu/relay-k8s-private/changes/rag-database-20261102T152803Z/`.
- `patch.json`: tests the observed Secret resourceVersion, then replaces only the database key.
- `rollback.json`: tests the proposed database key, then restores only the prior key. This restores the known failing configuration, not a healthy alternative; database contents remain untouched.
- `original-files/`: protected original copies of changed private files.
- `summary.json`: nonsecret plan and changed key names.

Files are 0600 and directories 0700. Never print patch/backup contents. If the Secret changes before application, revalidate rather than bypassing the guard. If rollback is necessary, reconcile private copies and refresh only the two affected consumers.

## Actual validation before approval

- 11/12 application Deployments ready; RAG API 0/1, RAG worker 1/1. All six PostgreSQL StatefulSets, Kafka and Redis ready. Inspected running application containers have zero restarts.
- All five other DB-backed APIs authenticate with SELECT 1 and have expected deployed Alembic revisions. Gateway, those APIs, and frontend return readiness 200. RAG liveness is 200 and readiness 503; its current credentials fail with InvalidPasswordError.
- The proposed RAG URL passes read-only SELECT 1 from **both** API and worker Pods. Its deployed Alembic revision matches repository head `9c532f7c05c1`. No schema/data writes performed.
- RAG worker's current DATABASE_URL differs from the live Secret and fails DNS resolution. Its Redis PING succeeds, explaining its misleading readiness.
- Redis PING succeeds for integration API/worker/Beat and RAG API/worker. Kafka TCP checks pass and read-only topic listing confirms all four required workflow topics. No tasks/messages published.
- Internal Service ports align with declared HTTP/gRPC targets. Five healthy gRPC Services accept TCP; RAG's Service has zero ready endpoints and TCP connections fail until readiness recovers. TCP acceptance is not a complete RPC test.
- RAG API and worker have nonempty Supabase URL/key/bucket and OpenAI key. Authenticated non-mutating Supabase bucket metadata reads succeed in both. No document upload, email, workflow trigger or paid AI call performed.
- Other workloads' shared ConfigMap env drift is confined to unused SUPABASE_URL snapshots; no restart is needed for those consumers. MCP environment matches its references.
- Both rendered ConfigMaps match live after the repository correction. All 21 active private source files pass duplicate-key, nonempty-value, DB/broker-address and 0600 permission checks. Only the proposed RAG DATABASE_URL intentionally differs from live Secrets. Historical rollback copies intentionally retain the old values.
- Existing full-K3s offline contract checks and whitespace checks pass. Configuration-only changes need no application build.
- Public frontend readiness and MCP OAuth discovery return HTTP 200 with verified TLS.
- Recent RAG API logs contain readiness 503 responses. Warning events include its failing probe and older replaced worker Pods; the current worker is ready with zero restarts.

## Remaining issues

**Blocking:** explicit approval to apply the prepared one-key Secret correction and refresh the two RAG consumers. Until then, the RAG API remains unready and the worker cannot access its database.

**Optional and outside this minimal configuration repair:** MCP probes, frontend MCP origin UI configuration, network-policy hardening and pipeline changes. The existing image-only CD remains separate from configuration updates. Authoritative private-source ownership is documented; no new deployment framework, validator package, or business logic was introduced.

---

# Relay Production Configuration Audit

## 1. Executive Summary

**Verdict: production readiness is not established. The live Kubernetes audit is blocked by kubeconfig permissions. Public endpoints are reachable, and local configuration defects and drift are confirmed, but the reported RAG readiness failure cannot be diagnosed conclusively without live evidence.**

This is a read-only audit of available repository code, rendered Kubernetes configuration, private manifests, and four public HTTPS endpoints. It is **not a completed audit of the running cluster**. No fixes were implemented.

Audit timestamp: 2026-11-02 15:11 UTC. Repository HEAD: `ddcc36a62efc85128f39a31c98f28b135faac371`. Namespace requested: `relay`. Production topology: Oracle single-node full K3s. Existing user modification preserved: `deploy/kubernetes/base/configmap.yaml`, key `SUPABASE_URL`.

| Measure | Result |
| --- | --- |
| Application workload definitions inspected | 12: seven FastAPI services, frontend, MCP, two Celery workers, one Beat |
| Infrastructure workload definitions inspected | 8 StatefulSets: six PostgreSQL, Kafka, Redis; 20 workload definitions in total |
| Live workloads inspected | 0; direct API access blocked before any resource could be read |
| ConfigMaps checked | 2 rendered definitions: relay-config and kafka-config; referenced relay-mcp-config unavailable in supplied files |
| Private Secrets checked | 21 files representing 14 distinct Secret names: 7 input copies and 14 generated copies; no live Secrets read |
| Confirmed configuration errors | 3 grouped source-level errors: C01 duplicate conflicting broker key; C02 empty committed Supabase URL; D01 stale/placeholder input DB and broker settings unsuitable for direct full-K3s deployment. No live configuration error count can be established |
| Additional confirmed omissions | C03 missing frontend MCP origin; C04 missing MCP probes |
| Suspected live mismatches | 4 investigation groups S01–S04 below; none claimed as proven live drift |
| Readiness failures | Unknown. RAG failure reported in task, not independently observed; 0/1 cause unverified |
| Public checks | 4/4 returned HTTP 200 with TLS verification; no credentials sent |
| Changes made | Only this report; pre-existing ConfigMap edit preserved; no packages, temp files, deployments, migrations, database writes, tasks, commits, or restarts |

### Access and evidence boundaries

The narrowly scoped `kubectl get pods -n relay ... --request-timeout=10s` failed with permission denied reading `/etc/rancher/k3s/k3s.yaml`. No user kubeconfig or `KUBECONFIG` override was available. The operator did not know an alternative connection. Per the audit instruction, no `sudo`, kubeconfig permission change, credential copying, or other privileged workaround was attempted. The deployment script's use of `sudo` is not authorization to bypass this boundary.

Offline Kustomize rendering succeeded with `KUBECONFIG=/dev/null`; rendered data stayed in memory. Private files were parsed in memory and only key names, presence, format checks and equality results were emitted. No raw secrets, encoded secrets or secret hashes appear here. Actual private connection strings, usernames, database names, passwords and provider values are withheld; expected names below come from repository contracts.

Public requests initially failed DNS in the sandbox. An approved network-only retry succeeded; it did not grant Kubernetes access. No external paid APIs, SMTP send, login, workflow trigger, task publication, Redis mutation, or Kafka publication was attempted.

### Inventory: definitions versus live resources

| Workload | Kind | Declared replicas | Repository image (not live) | Configuration references | Live ready/image |
| --- | --- | --- | --- | --- | --- |
| action-postgres | StatefulSet | 1 | postgres:16 | secretRef:action-postgres | Unverified |
| action-service | Deployment | 1 | relay/action-service:dev | configMapRef:relay-config; secretRef:relay-action-service | Unverified |
| api-gateway | Deployment | 1 | relay/api-gateway:dev | configMapRef:relay-config; secretKeyRef:relay-jwt/JWT_SECRET_KEY | Unverified |
| auth-postgres | StatefulSet | 1 | postgres:16 | secretRef:auth-postgres | Unverified |
| auth-service | Deployment | 1 | relay/auth-service:dev | configMapRef:relay-config; secretRef:relay-auth-service; secretKeyRef:relay-jwt/JWT_SECRET_KEY | Unverified |
| execution-postgres | StatefulSet | 1 | postgres:16 | secretRef:execution-postgres | Unverified |
| execution-service | Deployment | 1 | relay/execution-service:dev | configMapRef:relay-config; secretRef:relay-execution-service | Unverified |
| frontend | Deployment | 1 | relay/frontend:dev | configMapRef:relay-config | Unverified |
| integration-celery-beat | Deployment | 1 | relay/integration-service:dev | configMapRef:relay-config; secretRef:relay-integration-service | Unverified |
| integration-celery-worker | Deployment | 1 | relay/integration-service:dev | configMapRef:relay-config; secretRef:relay-integration-service | Unverified |
| integration-postgres | StatefulSet | 1 | postgres:16 | secretRef:integration-postgres | Unverified |
| integration-service | Deployment | 1 | relay/integration-service:dev | configMapRef:relay-config; secretRef:relay-integration-service | Unverified |
| kafka | StatefulSet | 1 | apache/kafka:4.0.1 | secretKeyRef:kafka-kraft/CLUSTER_ID; volume ConfigMap:kafka-config | Unverified |
| rag-celery-worker | Deployment | 1 | relay/rag-service:dev | configMapRef:relay-config; secretRef:relay-rag-service | Unverified |
| rag-postgres | StatefulSet | 1 | pgvector/pgvector:pg16 | secretRef:rag-postgres | Unverified |
| rag-service | Deployment | 1 | relay/rag-service:dev | configMapRef:relay-config; secretRef:relay-rag-service | Unverified |
| redis | StatefulSet | 1 | redis:7-alpine | none | Unverified |
| relay-mcp | Deployment | 1 | relay-mcp:dev | secretKeyRef:relay-mcp-secret/MCP_SESSION_SECRET; configMapKeyRef:relay-mcp-config/MCP_TRUSTED_PROXY_IPS | Unverified |
| workflow-postgres | StatefulSet | 1 | postgres:16 | secretRef:workflow-postgres | Unverified |
| workflow-service | Deployment | 1 | relay/workflow-service:dev | configMapRef:relay-config; secretRef:relay-workflow-service | Unverified |

CD intends immutable `ghcr.io/shaad4/relay-<component>:sha-<40-character-commit>` references for all 12 application workloads (`mcp` is the MCP component name). Live tags/digests and rollout revisions are unknown. The bare full-K3s overlay still renders development image tags; the MCP standalone file uses `relay-mcp:dev` with `imagePullPolicy: Never`. These are bootstrap definitions, not evidence that production runs development images.

The combined definitions have 17 Services (eight application HTTP Services, six PostgreSQL, Kafka, Redis, MCP), two Ingresses, seven NetworkPolicies, and `relay-app` ServiceAccount. All 16 full-K3s Service selectors match their declared workload labels; the separate MCP selector matches `app: relay-mcp`. Target HTTP/gRPC named ports match declared container ports. This does not establish ready endpoints.

There are eight `local-path` volume claim templates: `data-<statefulset>-0`, 1 GiB each except Kafka at 2 GiB. No independently declared PVC objects are in the overlay. Binding, capacity, free space, node affinity, and actual PVC contents are unverified.

Separate definitions exist for six `<service>-service-migrate` Jobs, `rag-vector-init`, and `kafka-topics-init`; they are not included in the ordinary full-K3s application render. No CronJob or Role/RoleBinding definitions were found in the audited manifests. Live Jobs, CronJobs, Pods, EndpointSlices/Endpoints, ConfigMaps, Secrets, RBAC bindings and resource counts remain unverified. An absent definition is not evidence that the live resource is absent.

## 2. Critical Findings

Severity below describes a remediation priority or risk, not an assertion of an active outage.

| ID / Severity | Service | Problem | Evidence | Impact | Recommended Fix |
| --- | --- | --- | --- | --- | --- |
| C01 / P1 | RAG API/worker | Conflicting duplicate CELERY_BROKER_URL in private input YAML | application-secrets/rag-service.yaml lines 9 and 12 have the same mapping key and different scalar values; node-level YAML inspection | Parser-dependent selection or validation rejection; safe_load currently keeps the later value | Keep one reviewed broker value in the authoritative private input; compare live before applying anything |
| C02 / P1 | RAG API/worker | Committed SUPABASE_URL is empty | HEAD deploy/kubernetes/base/configmap.yaml:42; neither full-k3s patch nor generated RAG Secret supplies it. Existing working-tree edit supplies a valid HTTPS URL | A clean render from committed files lacks required storage configuration; document operations construct SupabaseStorage even for listing. Does not explain DB-only /ready 503 | Persist the reviewed public setting in the production configuration source; confirm live source and restart needs under separate approval |
| C03 / P3 | Frontend | MCP_PUBLIC_ORIGIN is not injected into frontend | frontend/src/app/integrations/page.js:12 and dashboard/page.js:19 read it; full-k3s relay-config and frontend env omit it | Rendered frontend configuration disables MCP integration affordances; server can still operate | Add the reviewed public MCP origin to frontend configuration if the integration UI is intended |
| C04 / P2 | MCP | No startup, readiness, or liveness probes | deploy/kubernetes/mcp/deployment.yaml contains none | Running container can become a ready backend without an application-level health check; stalled process detection absent | Design compatible probes that account for trusted-ingress middleware; do not use a naive localhost HTTP probe that will receive 403 |
| D01 / P1 | Six DB clients / integration broker | Private input and generated DB/broker settings diverge | Boolean comparisons in sections 4 and 7; five input DB hosts remain placeholders with host-mapped ports; RAG input targets correct host but different DB/user/password | Applying input copies directly can replace working generated credentials and endpoints; live source unknown | Document generated deployed files as authoritative until live/PVC verification; quarantine stale input usage without regenerating production credentials |
| D02 / P1 | RAG embeddings / Gmail OAuth | Provider credentials differ between input and generated copies | OPENAI_API_KEY differs for RAG; GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET differ for action-service; values withheld | Regenerating or applying stale source may revert provider configuration; validity of either copy unknown | Reconcile through approved secret-management process after identifying live and intended provider configuration |
| R01 / P2 | All applications | Image-only CD does not reconcile configuration or validate schema versions | scripts/deploy-relay-k3s.sh: image updates, one MCP image-policy patch, rollout waits and public homepage check only | Config/Secret drift persists; successful image rollout does not prove schema compatibility or provider functionality | Add a reviewed configuration/schema validation gate and explicit configuration release process, without automatically running migrations |
| R02 / P2 | Internal infrastructure | Unauthenticated Redis and broad Relay-label infrastructure access | redis/resources.yaml disables protected mode with no password/ACL; infrastructure/network-policies.yaml permits all Relay-labelled pods to DB/Redis/Kafka ports | A compromised labelled workload can reach unauthenticated Redis; TCP reachability exceeds service-specific needs | Evaluate narrower per-client policies and coordinated Redis authentication; preserve working broker/probe compatibility |
| R03 / P2 | Beat / workers / databases | Readiness has functional blind spots | Beat checks PID only; workers ping broker; DB-based API probes run SELECT 1; details in section 8 | Ready Pods do not prove schedule delivery, provider access, schema version, or complete workflow execution | Add non-mutating operational checks/alerts for uncovered dependencies; keep liveness bounded and avoid task-producing audit probes |

**Suspected live mismatch groups:** S01 RAG live database configuration/PVC role mismatch; S02 committed/working-tree/live Supabase setting mismatch; S03 live provider credentials versus private copies; S04 live MCP referenced resources, trusted proxy peers, probe/image settings versus files. These are investigation targets, not four diagnosed failures.

## 3. Service-by-Service Configuration Matrix

`Correct` below means the **local declared source and/or default** satisfies the inspected contract. It does not mean a live environment variable or provider credential was verified. Every live source/presence column is `Unverified`. Required credentials are checked for presence and nonempty content only, with structural checks where meaningful. Optional variables using valid defaults are not reported as missing.

Source shorthand: `CM` = ConfigMap; `Secret` = private generated manifest paired with a repository reference; `env` = explicit Deployment field; `image` = Dockerfile ENV. The candidate full-K3s configuration uses the existing working-tree change; the clean committed configuration differs at SUPABASE_URL. `Unverified` on credentials preserves the distinction between nonempty and valid.

### Shared settings and precedence

All 11 base application Deployments receive `relay-config` through `envFrom`. Auth and gateway receive only the shared JWT key through an explicit `secretKeyRef`; each database-backed service receives its own service Secret. Integration API, worker and Beat share `relay-integration-service`; RAG API and worker share `relay-rag-service`. Frontend and gateway do not receive database/provider Secrets. MCP uses narrowly scoped explicit references.

The only observed shared ConfigMap/service-Secret collision is `GOOGLE_CLIENT_ID` for auth and action. Its ConfigMap value is empty, and the later Secret `envFrom` supplies a nonempty value in both workloads: **Correct, intentional precedence**, not an empty effective Google client ID. No other collisions between generated service Secret keys and the effective ConfigMap were found. Explicit `env` has precedence over `envFrom`; no conflicting explicit override was found. Duplicate YAML mapping keys are a separate issue (C01).

Core defaults: RELAY_ENV defaults to development but the full-K3s overlay sets production; DB pool defaults are 5/5/30/1800 and the overlay inherits 2/2/30/1800; concurrency overrides are execution=2, HTTP=2, AI=2, Celery worker=1. Full-K3s public URLs and Google callback paths use relay.shaad.site; COOKIE_SECURE=true and COOKIE_SAMESITE=lax. The unpatched base and generic production overlay contain deployment templates; do not mistake them for the effective full-K3s configuration.

### api-gateway

| Variable | Requirement / default | Expected source | Declared source | Local status | Actual live source/presence | Code evidence |
| --- | --- | --- | --- | --- | --- | --- |
| ACTION_SERVICE_URL | Optional; default 'http://action-service:8000' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/api-gateway/app/config.py:81` |
| AUTH_SERVICE_URL | Optional; default 'http://auth-service:8000' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/api-gateway/app/config.py:78` |
| CORS_ALLOWED_ORIGINS | Optional; default '' | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/api-gateway/app/config.py:54` |
| EXECUTION_SERVICE_URL | Optional; default 'http://execution-service:8000' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/api-gateway/app/config.py:82` |
| FRONTEND_URL | Optional; default 'http://localhost:3000' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/api-gateway/app/config.py:52` |
| INTEGRATION_SERVICE_URL | Optional; default 'http://integration-service:8000' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/api-gateway/app/config.py:80` |
| JWT_ALGORITHM | Optional; default 'HS256' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/api-gateway/app/core/security.py:9` |
| JWT_SECRET_KEY | Required; no default | Secret | Secret relay-jwt | Correct (nonempty; credential validity Unverified) | Unverified | `service/api-gateway/app/config.py:87` |
| RAG_SERVICE_URL | Optional; default 'http://rag-service:8000' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/api-gateway/app/config.py:83` |
| RELAY_ENV | Optional; default 'development' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/api-gateway/app/config.py:33` |
| WORKFLOW_SERVICE_URL | Optional; default 'http://workflow-service:8000' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/api-gateway/app/config.py:79` |

### auth-service

| Variable | Requirement / default | Expected source | Declared source | Local status | Actual live source/presence | Code evidence |
| --- | --- | --- | --- | --- | --- | --- |
| ACCESS_TOKEN_EXPIRE_MINUTES | Optional; default 30 | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/auth-service/app/core/jwt.py:13` |
| BACKEND_URL | Optional; default 'http://localhost:8001' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/config.py:139` |
| COOKIE_SAMESITE | Optional; default 'lax' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/config.py:142` |
| COOKIE_SECURE | Optional; default 'true' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/config.py:141` |
| CORS_ALLOWED_ORIGINS | Optional; default '' | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/auth-service/app/config.py:54` |
| DATABASE_URL | Required; no default | Secret | Secret relay-auth-service | Correct (generated pair; live DB Unverified) | Unverified | `service/auth-service/alembic/env.py:18` |
| DB_MAX_OVERFLOW | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/config.py:103` |
| DB_POOL_RECYCLE | Optional; default 1800 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/config.py:105` |
| DB_POOL_SIZE | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/config.py:102` |
| DB_POOL_TIMEOUT | Optional; default 30 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/config.py:104` |
| FRONTEND_URL | Optional; default 'http://localhost:3000' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/config.py:52` |
| GOOGLE_CLIENT_ID | Required for feature; no default | Secret or CM | Secret relay-auth-service | Correct (Secret overrides empty CM) | Unverified | `service/auth-service/app/services/google_oauth.py:20` |
| GOOGLE_CLIENT_SECRET | Required for feature; no default | Secret | Secret relay-auth-service | Correct (nonempty; credential validity Unverified) | Unverified | `service/auth-service/app/services/google_oauth.py:48` |
| GOOGLE_REDIRECT_URI | Required for feature; no default | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/services/google_oauth.py:21` |
| GRPC_BIND_ADDRESS | Optional; default f'[::]:{port}' | CM/env or documented default | env | Correct | Unverified | `service/auth-service/app/config.py:117` |
| JWT_ALGORITHM | Optional; default 'HS256' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/core/jwt.py:12` |
| JWT_SECRET_KEY | Required; no default | Secret | Secret relay-jwt | Correct (nonempty; credential validity Unverified) | Unverified | `service/auth-service/app/config.py:130` |
| PASSWORD_RESET_TOKEN_EXPIRE_MINUTES | Optional; default 30 | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/auth-service/app/services/password_reset_service.py:14` |
| REFRESH_TOKEN_EXPIRE_DAYS | Optional; default 7 | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/auth-service/app/core/jwt.py:14` |
| RELAY_ENV | Optional; default 'development' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/config.py:33` |
| SMTP_FROM_EMAIL | Required for feature; no default | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/services/email_service.py:20` |
| SMTP_FROM_NAME | Optional; default 'Relay' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/services/email_service.py:21` |
| SMTP_HOST | Required for feature; no default | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/services/email_service.py:16` |
| SMTP_PASSWORD | Required for feature; no default | Secret | Secret relay-auth-service | Correct (nonempty; credential validity Unverified) | Unverified | `service/auth-service/app/services/email_service.py:19` |
| SMTP_PORT | Optional; default 587 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/auth-service/app/services/email_service.py:17` |
| SMTP_USERNAME | Required for feature; no default | Secret | Secret relay-auth-service | Correct (nonempty; credential validity Unverified) | Unverified | `service/auth-service/app/services/email_service.py:18` |
| VERIFICATION_TOKEN_EXPIRE_MINUTES | Optional; default 30 | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/auth-service/app/services/email_verification_service.py:14` |

### workflow-service

| Variable | Requirement / default | Expected source | Declared source | Local status | Actual live source/presence | Code evidence |
| --- | --- | --- | --- | --- | --- | --- |
| AUTH_GRPC_TARGET | fallback only when AUTH_GRPC_URL absent | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/workflow-service/app/grpc/auth_client.py:6` |
| AUTH_GRPC_URL | Optional; default 'auth-service:50051' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/workflow-service/app/grpc/auth_client.py:6` |
| CORS_ALLOWED_ORIGINS | Optional; default '' | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/workflow-service/app/config.py:54` |
| DATABASE_URL | Required; no default | Secret | Secret relay-workflow-service | Correct (generated pair; live DB Unverified) | Unverified | `service/workflow-service/alembic/env.py:16` |
| DB_MAX_OVERFLOW | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/workflow-service/app/config.py:103` |
| DB_POOL_RECYCLE | Optional; default 1800 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/workflow-service/app/config.py:105` |
| DB_POOL_SIZE | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/workflow-service/app/config.py:102` |
| DB_POOL_TIMEOUT | Optional; default 30 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/workflow-service/app/config.py:104` |
| EXECUTION_GRPC_URL | Optional; default 'execution-service:50055' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/workflow-service/app/grpc/execution_client.py:8` |
| FRONTEND_URL | Optional; default 'http://localhost:3000' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/workflow-service/app/config.py:52` |
| GRPC_BIND_ADDRESS | Optional; default f'[::]:{port}' | CM/env or documented default | env | Correct | Unverified | `service/workflow-service/app/config.py:117` |
| INTEGRATION_GRPC_URL | Optional; default 'integration-service:50053' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/workflow-service/app/grpc/integration_client.py:8` |
| RELAY_ENV | Optional; default 'development' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/workflow-service/app/config.py:33` |

### integration-service

| Variable | Requirement / default | Expected source | Declared source | Local status | Actual live source/presence | Code evidence |
| --- | --- | --- | --- | --- | --- | --- |
| AUTH_GRPC_TARGET | fallback only when AUTH_GRPC_URL absent | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/integration-service/app/grpc/auth_client.py:6` |
| AUTH_GRPC_URL | Optional; default 'auth-service:50051' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/integration-service/app/grpc/auth_client.py:6` |
| CELERY_BROKER_URL | Optional; default 'redis://rag-redis:6379/1' | Secret | Secret relay-integration-service | Correct (nonempty; credential validity Unverified) | Unverified | `service/integration-service/app/celery_app.py:9` |
| CELERY_WORKER | Optional unless relevant code path enabled | CM/env or documented default | Not set in manifests | Correct (optional unset) | Unverified | `service/integration-service/app/db/database.py:20` |
| DATABASE_URL | Required; no default | Secret | Secret relay-integration-service | Correct (generated pair; live DB Unverified) | Unverified | `service/integration-service/alembic/env.py:19` |
| DB_MAX_OVERFLOW | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/integration-service/app/config.py:61` |
| DB_POOL_RECYCLE | Optional; default 1800 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/integration-service/app/config.py:63` |
| DB_POOL_SIZE | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/integration-service/app/config.py:60` |
| DB_POOL_TIMEOUT | Optional; default 30 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/integration-service/app/config.py:62` |
| GRPC_BIND_ADDRESS | Optional; default f'[::]:{port}' | CM/env or documented default | env | Correct | Unverified | `service/integration-service/app/config.py:75` |
| KAFKA_BOOTSTRAP_SERVERS | Optional; default 'kafka:9092' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/integration-service/app/kafka/producer.py:8` |
| RELAY_ENV | Optional; default 'development' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/integration-service/app/config.py:33` |
| WORKFLOW_GRPC_URL | Optional; default 'workflow-service:50052' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/integration-service/app/grpc/workflow_client.py:6` |

### action-service

| Variable | Requirement / default | Expected source | Declared source | Local status | Actual live source/presence | Code evidence |
| --- | --- | --- | --- | --- | --- | --- |
| ACTION_CREDENTIAL_ENCRYPTION_KEY | Required in production; Fernet format | Secret | Secret relay-action-service | Correct (nonempty; credential validity Unverified) | Unverified | `service/action-service/app/config.py:88` |
| AUTH_GRPC_TARGET | fallback only when AUTH_GRPC_URL absent | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/action-service/app/grpc/auth_client.py:6` |
| AUTH_GRPC_URL | Optional; default 'auth-service:50051' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/action-service/app/grpc/auth_client.py:6` |
| DATABASE_URL | Required; no default | Secret | Secret relay-action-service | Correct (generated pair; live DB Unverified) | Unverified | `service/action-service/alembic/env.py:17` |
| DB_MAX_OVERFLOW | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/action-service/app/config.py:61` |
| DB_POOL_RECYCLE | Optional; default 1800 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/action-service/app/config.py:63` |
| DB_POOL_SIZE | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/action-service/app/config.py:60` |
| DB_POOL_TIMEOUT | Optional; default 30 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/action-service/app/config.py:62` |
| GOOGLE_CLIENT_ID | Required for feature; no default | Secret or CM | Secret relay-action-service | Correct (Secret overrides empty CM) | Unverified | `service/action-service/app/routes/gmail_oauth.py:29` |
| GOOGLE_CLIENT_SECRET | Required for feature; no default | Secret | Secret relay-action-service | Correct (nonempty; credential validity Unverified) | Unverified | `service/action-service/app/routes/gmail_oauth.py:30` |
| GOOGLE_GMAIL_REDIRECT_URI | Required for feature; no default | CM/env or documented default | CM relay-config | Correct | Unverified | `service/action-service/app/routes/gmail_oauth.py:31` |
| GRPC_BIND_ADDRESS | Optional; default f'[::]:{port}' | CM/env or documented default | env | Correct | Unverified | `service/action-service/app/config.py:75` |
| MAX_CONCURRENT_HTTP_REQUESTS | Optional; default 10 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/action-service/app/config.py:97` |
| RELAY_ENV | Optional; default 'development' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/action-service/app/config.py:33` |

### execution-service

| Variable | Requirement / default | Expected source | Declared source | Local status | Actual live source/presence | Code evidence |
| --- | --- | --- | --- | --- | --- | --- |
| ACTION_GRPC_URL | Optional; default 'action-service:50054' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/grpc/action_client.py:6` |
| AI_CREDENTIAL_ENCRYPTION_KEY | Required in production; Fernet format | Secret | Secret relay-execution-service | Correct (nonempty; credential validity Unverified) | Unverified | `service/execution-service/app/config.py:88` |
| AI_REQUEST_TIMEOUT_SECONDS | Optional; default 60 | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/execution-service/app/config.py:97` |
| AUTH_GRPC_TARGET | fallback only when AUTH_GRPC_URL absent | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/execution-service/app/grpc/auth_client.py:6` |
| AUTH_GRPC_URL | Optional; default 'auth-service:50051' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/grpc/auth_client.py:6` |
| DATABASE_URL | Required; no default | Secret | Secret relay-execution-service | Correct (generated pair; live DB Unverified) | Unverified | `service/execution-service/alembic/env.py:15` |
| DB_MAX_OVERFLOW | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/config.py:61` |
| DB_POOL_RECYCLE | Optional; default 1800 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/config.py:63` |
| DB_POOL_SIZE | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/config.py:60` |
| DB_POOL_TIMEOUT | Optional; default 30 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/config.py:62` |
| EXECUTION_MAX_CONCURRENCY | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/config.py:95` |
| GRPC_BIND_ADDRESS | Optional; default f'[::]:{port}' | CM/env or documented default | env | Correct | Unverified | `service/execution-service/app/config.py:75` |
| KAFKA_BOOTSTRAP_SERVERS | Optional; default 'kafka:9092' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/kafka/lifecycle_producer.py:8` |
| KAFKA_CONSUMER_GROUP_ID | Optional; default 'execution-service' | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/execution-service/app/kafka/consumer.py:17` |
| MAX_CONCURRENT_AI_REQUESTS | Optional; default 10 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/config.py:96` |
| RAG_GRPC_ADDRESS | fallback only when RAG_GRPC_URL absent | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/execution-service/app/grpc/rag_client.py:6` |
| RAG_GRPC_URL | Optional; default 'rag-service:50056' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/grpc/rag_client.py:6` |
| RELAY_ENV | Optional; default 'development' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/config.py:33` |
| WORKFLOW_GRPC_URL | Optional; default 'workflow-service:50052' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/execution-service/app/grpc/workflow_client.py:6` |

### rag-service

| Variable | Requirement / default | Expected source | Declared source | Local status | Actual live source/presence | Code evidence |
| --- | --- | --- | --- | --- | --- | --- |
| AUTH_GRPC_TARGET | fallback only when AUTH_GRPC_URL absent | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/rag-service/app/grpc/auth_client.py:6` |
| AUTH_GRPC_URL | Optional; default 'auth-service:50051' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/rag-service/app/grpc/auth_client.py:6` |
| CELERY_BROKER_URL | Optional; default 'redis://rag-redis:6379/0' | Secret | Secret relay-rag-service | Correct (nonempty; credential validity Unverified) | Unverified | `service/rag-service/app/celery_app.py:9` |
| DATABASE_URL | Required; no default | Secret | Secret relay-rag-service | Correct (generated pair; live DB Unverified) | Unverified | `service/rag-service/alembic/env.py:25` |
| DB_MAX_OVERFLOW | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/rag-service/app/config.py:57` |
| DB_POOL_RECYCLE | Optional; default 1800 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/rag-service/app/config.py:59` |
| DB_POOL_SIZE | Optional; default 5 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/rag-service/app/config.py:56` |
| DB_POOL_TIMEOUT | Optional; default 30 | CM/env or documented default | CM relay-config | Correct | Unverified | `service/rag-service/app/config.py:58` |
| EMBEDDING_MODEL | Optional; default 'text-embedding-3-small' | CM/env or documented default | Code default / alias unused | Correct (optional unset) | Unverified | `service/rag-service/app/embeddings/provider.py:14` |
| GRPC_BIND_ADDRESS | Optional; default f'[::]:{port}' | CM/env or documented default | env | Correct | Unverified | `service/rag-service/app/config.py:71` |
| OPENAI_API_KEY | Required for feature; no default | Secret | Secret relay-rag-service | Correct (nonempty; credential validity Unverified) | Unverified | `service/rag-service/app/embeddings/provider.py:9` |
| RELAY_ENV | Optional; default 'development' | CM/env or documented default | CM relay-config | Correct | Unverified | `service/rag-service/app/config.py:29` |
| SUPABASE_SECRET_KEY | Required for feature; no default | Secret | Secret relay-rag-service | Correct (nonempty; credential validity Unverified) | Unverified | `service/rag-service/app/storage/supabase_storage.py:12` |
| SUPABASE_STORAGE_BUCKET | Required for feature; no default | CM/env or documented default | CM relay-config | Correct | Unverified | `service/rag-service/app/storage/supabase_storage.py:8` |
| SUPABASE_URL | Required for feature; no default | CM/env or documented default | CM relay-config | Correct in working tree; Empty at HEAD (C02) | Unverified | `service/rag-service/app/storage/supabase_storage.py:11` |

### Integration Celery Worker, Integration Celery Beat, and RAG Celery Worker

Integration API, worker and Beat share one service Secret; RAG API and worker share their own. All inherit the common ConfigMap. The following covers their consumed broker/DB/runtime settings; HTTP/gRPC bind settings injected by the shared ConfigMap are not Celery listeners.

| Service | Variable | Requirement | Declared source | Local status | Actual live source/presence |
| --- | --- | --- | --- | --- | --- |
| integration-celery-worker | RELAY_ENV | Production | CM relay-config | Correct (declared/private generated) | Unverified |
| integration-celery-worker | DATABASE_URL | Required | Secret relay-integration-service | Correct (declared/private generated) | Unverified |
| integration-celery-worker | DB_POOL_SIZE | Optional; default 5 | CM relay-config | Correct (declared/private generated) | Unverified |
| integration-celery-worker | DB_MAX_OVERFLOW | Optional; default 5 | CM relay-config | Correct (declared/private generated) | Unverified |
| integration-celery-worker | DB_POOL_TIMEOUT | Optional; default 30 | CM relay-config | Correct (declared/private generated) | Unverified |
| integration-celery-worker | DB_POOL_RECYCLE | Optional; default 1800 | CM relay-config | Correct (declared/private generated) | Unverified |
| integration-celery-worker | CELERY_BROKER_URL | Optional in code; explicit full-K3s value required to avoid rag-redis fallback | Secret relay-integration-service | Correct (declared/private generated) | Unverified |
| integration-celery-worker | KAFKA_BOOTSTRAP_SERVERS | Required by scheduled task path | CM relay-config | Correct (declared) | Unverified |
| integration-celery-worker | WORKFLOW_GRPC_URL | Required by scheduled task path | CM relay-config | Correct (declared) | Unverified |
| integration-celery-worker | AUTH_GRPC_URL / AUTH_GRPC_TARGET | Optional client target / compatibility alias | CM / alias unset | Correct; not used by Beat PID probe | Unverified |
| integration-celery-worker | CELERY_WORKER | Worker runtime | env | Correct (true / 1) | Unverified |
| integration-celery-worker | CELERY_WORKER_CONCURRENCY | Worker runtime | CM relay-config | Correct (true / 1) | Unverified |
| integration-celery-beat | RELAY_ENV | Production | CM relay-config | Correct (declared/private generated) | Unverified |
| integration-celery-beat | DATABASE_URL | Required | Secret relay-integration-service | Correct (declared/private generated) | Unverified |
| integration-celery-beat | DB_POOL_SIZE | Optional; default 5 | CM relay-config | Correct (declared/private generated) | Unverified |
| integration-celery-beat | DB_MAX_OVERFLOW | Optional; default 5 | CM relay-config | Correct (declared/private generated) | Unverified |
| integration-celery-beat | DB_POOL_TIMEOUT | Optional; default 30 | CM relay-config | Correct (declared/private generated) | Unverified |
| integration-celery-beat | DB_POOL_RECYCLE | Optional; default 1800 | CM relay-config | Correct (declared/private generated) | Unverified |
| integration-celery-beat | CELERY_BROKER_URL | Optional in code; explicit full-K3s value required to avoid rag-redis fallback | Secret relay-integration-service | Correct (declared/private generated) | Unverified |
| integration-celery-beat | KAFKA_BOOTSTRAP_SERVERS | Required by scheduled task path | CM relay-config | Correct (declared) | Unverified |
| integration-celery-beat | WORKFLOW_GRPC_URL | Required by scheduled task path | CM relay-config | Correct (declared) | Unverified |
| integration-celery-beat | AUTH_GRPC_URL / AUTH_GRPC_TARGET | Optional client target / compatibility alias | CM / alias unset | Correct; not used by Beat PID probe | Unverified |
| rag-celery-worker | RELAY_ENV | Production | CM relay-config | Correct (declared/private generated) | Unverified |
| rag-celery-worker | DATABASE_URL | Required | Secret relay-rag-service | Correct (declared/private generated) | Unverified |
| rag-celery-worker | DB_POOL_SIZE | Optional; default 5 | CM relay-config | Correct (declared/private generated) | Unverified |
| rag-celery-worker | DB_MAX_OVERFLOW | Optional; default 5 | CM relay-config | Correct (declared/private generated) | Unverified |
| rag-celery-worker | DB_POOL_TIMEOUT | Optional; default 30 | CM relay-config | Correct (declared/private generated) | Unverified |
| rag-celery-worker | DB_POOL_RECYCLE | Optional; default 1800 | CM relay-config | Correct (declared/private generated) | Unverified |
| rag-celery-worker | CELERY_BROKER_URL | Optional in code; explicit full-K3s value required to avoid rag-redis fallback | Secret relay-rag-service | Correct (declared/private generated) | Unverified |
| rag-celery-worker | CELERY_WORKER | Worker runtime | env | Correct (true / 1) | Unverified |
| rag-celery-worker | CELERY_WORKER_CONCURRENCY | Worker runtime | CM relay-config | Correct (true / 1) | Unverified |
| rag-celery-worker | SUPABASE_URL | Required for ingestion; model optional | CM relay-config | Correct in working tree; HEAD empty (C02) | Unverified |
| rag-celery-worker | SUPABASE_STORAGE_BUCKET | Required for ingestion; model optional | CM relay-config | Correct (presence/default only; provider validity Unverified) | Unverified |
| rag-celery-worker | SUPABASE_SECRET_KEY | Required for ingestion; model optional | Secret relay-rag-service | Correct (presence/default only; provider validity Unverified) | Unverified |
| rag-celery-worker | OPENAI_API_KEY | Required for ingestion; model optional | Secret relay-rag-service | Correct (presence/default only; provider validity Unverified) | Unverified |
| rag-celery-worker | EMBEDDING_MODEL | Required for ingestion; model optional | default text-embedding-3-small | Correct (presence/default only; provider validity Unverified) | Unverified |

### MCP Server

`RELAY_EMAIL` and `RELAY_PASSWORD` belong to the local stdio session (`relay_session.py`), not the production remote OAuth flow. Their absence from the remote Deployment is correct. Remote API credentials are obtained per user at login, not from a shared runtime password. Arbitrary library defaults are not treated as required application secrets.

| Variable | Requirement / default | Expected source | Declared source | Local status | Actual live source/presence |
| --- | --- | --- | --- | --- | --- |
| MCP_DEPLOYMENT_MODE | Default local; production requires k3s | env | env: k3s | Correct | Unverified |
| MCP_PORT | Default 8001; 1–65535 | env/default | env: 8001 | Correct; Service and container agree | Unverified |
| MCP_PUBLIC_ORIGIN | Exact K3s HTTPS origin enforced by code | env/CM | env: https://mcp.relay.shaad.site | Correct | Unverified |
| RELAY_API_URL | Required when remote login/API calls occur | env/CM | env: https://relay.shaad.site/api/relay | Correct URL syntax; public API path | Unverified |
| MCP_SESSION_SECRET | At least 32 random characters; no safe default | Secret | relay-mcp-secret/MCP_SESSION_SECRET | Unverified: resource absent from supplied files | Unverified |
| MCP_TRUSTED_PROXY_IPS | Required valid IP/CIDR entries; /0 rejected | CM | relay-mcp-config/MCP_TRUSTED_PROXY_IPS | Unverified: resource absent from supplied files | Unverified |
| RELAY_EMAIL | Required for stdio only | Local env, not production remote | Unset | Correct (not required remotely) | Unverified |
| RELAY_PASSWORD | Required for stdio only | Local env, not production remote | Unset | Correct (not required remotely) | Unverified |
| FORWARDED_ALLOW_IPS | Deliberately not inherited by trusted ingress validation | None | Unset; proxy_headers=False | Correct; explicit peer allowlist used | Unverified |

Evidence: `service/mcp-server/remote_server.py:48` and `:187`, `oauth/app.py:32`, `oauth/login.py:34`; deployment references at `deploy/kubernetes/mcp/deployment.yaml:41–63`. The K3s runner explicitly binds 0.0.0.0, one Uvicorn worker, and disables generic proxy header/access-log handling. OAuth provider session/token state is in memory; a stable signing secret does not persist issued grants across restarts.

### Frontend

| Variable | Requirement / default | Expected source | Declared source | Local status | Actual live source/presence |
| --- | --- | --- | --- | --- | --- |
| API_GATEWAY_URL | Required with NODE_ENV=production; dev fallback localhost:8001 | CM | relay-config; http://api-gateway:8000 | Correct | Unverified |
| FRONTEND_URL | Required in production; dev fallback localhost:3000 | CM | relay-config; public HTTPS origin | Correct | Unverified |
| API_PROXY_TIMEOUT_SECONDS | Optional; default 120, range 1–600 | CM/default | Code default | Correct (optional unset) | Unverified |
| API_PROXY_MAX_BODY_BYTES | Optional; default 12582912, range 1–104857600 | CM/default | Code default | Correct (optional unset) | Unverified |
| MCP_PUBLIC_ORIGIN | Optional; absent/invalid disables integration UI | CM/env | Not supplied to frontend | Missing (optional feature configuration, C03) | Unverified |
| NEXT_PUBLIC_AUTH_API_URL | Optional build-time browser override; default /api/relay | Build env or default | Unset in build workflow/Dockerfile | Correct (same-origin default) | Unverified built bundle |
| NODE_ENV | Production runtime | image | Dockerfile: production | Correct | Unverified |
| PORT | Listener 3000 | image | Dockerfile: 3000 | Correct; Service target agrees | Unverified |
| HOSTNAME | Bind address | image | Dockerfile: 0.0.0.0 | Correct | Unverified |
| NEXT_TELEMETRY_DISABLED | Optional build/runtime preference | image | Dockerfile: 1 | Correct | Unverified |

Evidence: `frontend/src/lib/server/apiProxy.js:35`, `frontend/src/lib/api.js:3`, `frontend/src/lib/integrations.js:2`, `frontend/Dockerfile:14`. Frontend also receives unused keys from the shared ConfigMap; these are nonsecret and not all are frontend requirements.

### Library, command-line, and infrastructure environment

Python service images set `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1` and their virtualenv `PATH`; pip build settings are not runtime secret requirements. Backend entrypoints explicitly supply Uvicorn host 0.0.0.0, HTTP port 8000 and workers=1. MCP supplies its bind/worker options in code. No additional application BaseSettings/env-prefix classes were found. gRPC compatibility aliases `AUTH_GRPC_TARGET` and `RAG_GRPC_ADDRESS` were included above; canonical configured names take precedence.

Celery command-line queue flags and configuration are inspected in section 5. Dependency-level environment injection (proxy variables, certificate overrides, SDK base URL/project overrides, dotenv files inside deployed images) cannot be exhaustively excluded without live container/image inspection. No wholesale environment dump was performed. Source Docker ignore rules exclude real .env files; dotenv calls do not by themselves prove that a file exists in the image.

| Workload | Variable | Requirement | Declared source | Local status | Actual live source/presence |
| --- | --- | --- | --- | --- | --- |
| auth-postgres | POSTGRES_USER | Required initialization contract | Secret auth-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| auth-postgres | POSTGRES_DB | Required initialization contract | Secret auth-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| auth-postgres | POSTGRES_PASSWORD | Required initialization contract | Secret auth-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| auth-postgres | PGDATA | Explicit data path | env | Correct; mounted beneath persistent data directory | Unverified |
| workflow-postgres | POSTGRES_USER | Required initialization contract | Secret workflow-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| workflow-postgres | POSTGRES_DB | Required initialization contract | Secret workflow-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| workflow-postgres | POSTGRES_PASSWORD | Required initialization contract | Secret workflow-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| workflow-postgres | PGDATA | Explicit data path | env | Correct; mounted beneath persistent data directory | Unverified |
| integration-postgres | POSTGRES_USER | Required initialization contract | Secret integration-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| integration-postgres | POSTGRES_DB | Required initialization contract | Secret integration-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| integration-postgres | POSTGRES_PASSWORD | Required initialization contract | Secret integration-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| integration-postgres | PGDATA | Explicit data path | env | Correct; mounted beneath persistent data directory | Unverified |
| action-postgres | POSTGRES_USER | Required initialization contract | Secret action-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| action-postgres | POSTGRES_DB | Required initialization contract | Secret action-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| action-postgres | POSTGRES_PASSWORD | Required initialization contract | Secret action-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| action-postgres | PGDATA | Explicit data path | env | Correct; mounted beneath persistent data directory | Unverified |
| execution-postgres | POSTGRES_USER | Required initialization contract | Secret execution-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| execution-postgres | POSTGRES_DB | Required initialization contract | Secret execution-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| execution-postgres | POSTGRES_PASSWORD | Required initialization contract | Secret execution-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| execution-postgres | PGDATA | Explicit data path | env | Correct; mounted beneath persistent data directory | Unverified |
| rag-postgres | POSTGRES_USER | Required initialization contract | Secret rag-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| rag-postgres | POSTGRES_DB | Required initialization contract | Secret rag-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| rag-postgres | POSTGRES_PASSWORD | Required initialization contract | Secret rag-postgres | Correct (nonempty; paired with generated app URL) | Unverified |
| rag-postgres | PGDATA | Explicit data path | env | Correct; mounted beneath persistent data directory | Unverified |
| kafka | CLUSTER_ID | Required immutable storage identity | Secret kafka-kraft | Correct (nonempty); stored metadata equality Unverified | Unverified |
| kafka | KAFKA_HEAP_OPTS | JVM memory options | env | Correct (256 MiB initial / 768 MiB maximum; 1536 MiB container limit) | Unverified |
| redis | Authentication environment | No authentication configured | None; command-line args | Correct against unauthenticated client URLs; security risk R02 | Unverified |

## 4. Database Connectivity Findings

All six generated application `DATABASE_URL` values use the expected asyncpg scheme, expected in-cluster Service host, and port 5432. Their decoded username, database name and password match their corresponding generated PostgreSQL Secret, using in-memory boolean comparisons. **This establishes file consistency only**: PostgreSQL initialization settings do not update existing PVC role passwords, and matching manifests cannot prove login works.

For privacy, unexpected private hostnames and actual user/database values are not reproduced. Expected database/user names are the generator contract `<service>_db` / `<service>_user`. Input copies are not presumed to be the deployed source.

| Service | Expected Service:port | Generated private URL check | Input private URL check | Live host/endpoints | Read-only SQL / live Alembic | Repository Alembic head |
| --- | --- | --- | --- | --- | --- | --- |
| auth | auth-postgres:5432 | Expected host matches; port 5432; DB/user/password pair matches | Placeholder host; port 5434; DB/user/password do not match generated PostgreSQL | Unverified | Unverified | 5d94cb170f2a |
| workflow | workflow-postgres:5432 | Expected host matches; port 5432; DB/user/password pair matches | Placeholder host; port 5433; DB/user/password do not match generated PostgreSQL | Unverified | Unverified | b63e801ac219 |
| integration | integration-postgres:5432 | Expected host matches; port 5432; DB/user/password pair matches | Placeholder host; port 5435; DB/user/password do not match generated PostgreSQL | Unverified | Unverified | 38cc2e1f842b |
| action | action-postgres:5432 | Expected host matches; port 5432; DB/user/password pair matches | Placeholder host; port 5436; DB/user/password do not match generated PostgreSQL | Unverified | Unverified | 057ec9aecebf |
| execution | execution-postgres:5432 | Expected host matches; port 5432; DB/user/password pair matches | Placeholder host; port 5437; DB/user/password do not match generated PostgreSQL | Unverified | Unverified | 1f0d1b386402 |
| rag | rag-postgres:5432 | Expected host matches; port 5432; DB/user/password pair matches | Host matches; port 5432; DB/user/password do not match generated PostgreSQL | Unverified | Unverified | 9c532f7c05c1 |

Input passwords for auth/workflow/integration/action/execution match the public example-template placeholder; they are not usable reviewed production credentials. RAG input credentials also differ from generated PostgreSQL, and its password is a generic placeholder. The actual value is withheld. None of these input database credentials should be treated as reviewed production credentials.

Expected Service definitions are in `deploy/kubernetes/infrastructure/postgres/resources.yaml`. HTTP client/gRPC traffic does not use the Compose host-mapped DB ports. All generated PostgreSQL pairs pass local host/port checks; no evidence supports changing generated RAG to port 5438.

The six Alembic chains contain 35 migration files. Only source ASTs were read; no Alembic command, application import or migration was run. A future read-only check must compare `SELECT version_num FROM alembic_version` to the **deployed image's** revision graph as well as the checkout above. Use an explicit read-only transaction for connection/schema inspection and suppress exception strings containing URLs. `SELECT 1` does not establish pgvector extension availability or schema alignment.

For RAG, inspect the running Pod's effective DATABASE_URL, the live relay-rag-service Secret, rag-postgres Service/ready EndpointSlices, and authenticated DB connectivity first. Determine whether failure is DNS, connection refusal, authentication, missing database, resource exhaustion, or timeout. A 503 from the current `/ready` handler specifically means the DB check failed or exceeded its 3-second budget. A failed HTTP startup before readiness may have a different cause. Do not infer the cause from a deployment's 0/1 count alone.

## 5. Kafka, Redis, and Celery Findings

| Component | Expected / declared configuration | Local result | Live connectivity |
| --- | --- | --- | --- |
| Kafka clients | KAFKA_BOOTSTRAP_SERVERS=kafka:9092 in full-k3s; integration producer and execution consumer/lifecycle producer use it | Correct rendered host/port; base placeholder is overridden | Unverified DNS, TCP, broker metadata and topic availability |
| Kafka broker | Headless Service kafka:9092; broker advertises kafka-0.kafka.relay.svc.cluster.local:9092; controller 9093 | Names align with StatefulSet serviceName/namespace; assumes cluster.local DNS domain | Unverified actual cluster domain, endpoints and advertised listener reachability |
| Kafka security/durability | PLAINTEXT, one broker/controller, replication factor 1; KRaft ID Secret | Intentional single-node design; no cross-node durability or transport authentication | Unverified live settings/storage ID |
| Redis | Service redis:6379; append-only file, noeviction, no configured password | Both generated broker URLs use Redis with no user/password, compatible with manifest | Unverified DNS, TCP, PING and live authentication |
| Integration worker | Redis DB 1; queue integration; concurrency 1; hostname relay@%h | Command queue agrees with task_default_queue; required DB and Kafka settings present | Unverified worker consumption and broker readiness |
| Integration Beat | Same Redis DB 1; one replica; Recreate strategy; UTC 60-second check-due schedule | Schedule and worker queue agree; ephemeral /tmp Beat state; PID-only readiness | Unverified singleton/process, broker connectivity or schedule delivery |
| RAG worker | Redis DB 0; queue rag_ingestion; concurrency 1; late ack; prefetch 1 | Command queue agrees with task_default_queue; no result backend requirement | Unverified broker, DB and external provider connectivity |

Code defaults for both Celery applications refer to `rag-redis:6379`, while full K3s declares only `redis`. This is not an active mismatch in the generated private files, because both explicitly set correct broker URLs. Losing/omitting those keys would activate a bad fallback for this topology. Integration input still has a placeholder broker host; RAG input has conflicting duplicate broker entries. Reconcile the authoritative source rather than changing a working Secret based only on defaults.

`kafka-config` disables topic auto-creation. A separate `kafka-topics-init` Job defines workflow.triggered, workflow.started, workflow.completed and workflow.failed. Presence/configuration of those live topics is unverified. Topic initialization was not executed. Kafka readiness lists topics; this does not prove the required four exist.

Worker startup/readiness invokes `celery_app.control.ping`, which is a broker control-message exchange, not a workflow task. It was **not executed by this audit**, because it can create broker traffic/temporary reply queues and the request prohibits Redis mutation/task publication. A future audit can inspect broker connectivity without publishing tasks. Worker probes do not validate DB credentials, Supabase, OpenAI, or scheduled-task success. RAG CELERY_WORKER is injected but its current DB module does not branch on it; ingestion uses its own NullPool engine.

## 6. External Integration Findings

| Integration | Presence / syntax / consistency | Credential validity / functionality |
| --- | --- | --- |
| Supabase URL | Working-tree full-k3s value is nonempty HTTPS with a valid hostname; committed value empty (C02). Private generated RAG Secret does not override it | Project reachability and key/project pairing Unverified |
| Supabase key | SUPABASE_SECRET_KEY exists and is nonempty in input/generated; equality true | Unverified; no storage API call, upload, deletion or bucket listing |
| Supabase bucket | SUPABASE_STORAGE_BUCKET=relay-documents from repository ConfigMap | Bucket existence/policy and key permissions Unverified |
| OpenAI embeddings | OPENAI_API_KEY present/nonempty in both private RAG copies, but values differ. Default model text-embedding-3-small; code expects 1536 dimensions | Unverified; no embedding generation or paid request |
| SMTP | Production overlay configures SMTP host/from and port 587; auth Secret username/password nonempty; implementation uses STARTTLS | Credentials, sender authorization, delivery and live TCP connectivity Unverified; no email sent |
| Google sign-in | Auth client ID/secret nonempty; production redirect /api/relay/auth/google/callback syntactically matches configured public origin | OAuth console redirect registration and credential validity Unverified; no login/token exchange |
| Google Gmail | Action credentials nonempty; /api/relay/connections/gmail/oauth/callback configured; generated auth/action pairs equal, input pairs differ | Separate OAuth clients may be intentional; equality is not a requirement. Which action copy is intended is Unverified |
| MCP OAuth | Public discovery returns 200; exact public origin configured; session/proxy source resources not available locally | Live session-secret length, trusted peers, OAuth issuance and Relay login flow Unverified |
| Workflow AI/action providers | Execution OpenAI/Anthropic/Gemini and action connectors obtain provider credentials from application connection data; encryption keys are nonempty and valid Fernet lengths | Absence of global provider env keys is not a missing production setting for these paths; DB-held credentials not accessed |

Public HTTPS observations (unauthenticated GET, verified TLS, 10-second timeout, response bodies and headers not logged):

| URL | Observed status | What it proves |
| --- | --- | --- |
| https://relay.shaad.site/health | 200 | Public route/TLS and frontend health handler reachable |
| https://relay.shaad.site/ready | 200 | Frontend readiness passed its gateway request at observation time |
| https://relay.shaad.site/api/relay/ready | 200 | Public proxy could reach gateway readiness |
| https://mcp.relay.shaad.site/.well-known/oauth-authorization-server | 200 | Public MCP discovery route reachable through TLS/ingress |

These requests cannot identify the backing Pod, image, live ConfigMap or TLS Secret. Gateway readiness returns ready without checking downstream services. Thus public 200 responses do not disprove the reported RAG failure. No claim is made that populated provider keys are valid.

## 7. ConfigMap and Secret Drift

### A. Repository, working tree, and effective overlays

The committed base leaves SUPABASE_URL empty. The pre-existing working-tree edit supplies it, and full-k3s inherits it. All other base keys are unchanged. The full-k3s patch correctly replaces development RELAY_ENV/cookies/public URLs and the hybrid Kafka placeholder. The generic production overlay still needs operator-specific values; it is not the full-k3s overlay used for this analysis. The effective working-tree full-k3s ConfigMap contains no placeholder endpoints. Its only empty key is GOOGLE_CLIENT_ID, overridden for both actual consumers by their service Secrets.

### B. Private input versus generated manifests

All seven application/JWT Secret names and key sets match across the two directories. There are no additional/missing logical keys between those corresponding copies, and all effective values are nonempty. The RAG duplicate is visible only at YAML-node level; a normal mapping parser hides it.

| Secret | Keys with unequal private values (values withheld) | Corresponding key sets | Live versus either private copy |
| --- | --- | --- | --- |
| relay-action-service | DATABASE_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET | Equal | Unverified |
| relay-auth-service | DATABASE_URL | Equal | Unverified |
| relay-execution-service | DATABASE_URL | Equal | Unverified |
| relay-integration-service | CELERY_BROKER_URL, DATABASE_URL | Equal | Unverified |
| relay-jwt | none | Equal | Unverified |
| relay-rag-service | DATABASE_URL, OPENAI_API_KEY | Equal | Unverified |
| relay-workflow-service | DATABASE_URL | Equal | Unverified |

The generated directory additionally contains six PostgreSQL initialization Secrets and kafka-kraft. All six generated application URLs pair correctly with them. Action and execution encryption keys, the JWT key, Supabase key and auth SMTP/Google values are equal between their corresponding input/generated copies. Provider drift for action Google credentials and RAG OpenAI cannot be explained by the generator's normal DB/broker rewriting: the generator copies those provider settings unchanged. It proves divergence between the private copies, not who changed them or which one is live.

`relay-mcp-secret`, `relay-mcp-config`, `relay-tls` and `relay-mcp-tls` are referenced by repository manifests but have no definitions in either supplied private directory or the audited YAML definitions. These resources may be provisioned elsewhere; public TLS/discovery success is encouraging but does not establish their live names/contents. Do not recreate or rotate them based on their absence from the local inventory.

### C. Live resources

Live key sets, values, env snapshots, managedFields, rollout timestamps, resource versions and Secret/ConfigMap precedence remain **Unverified**. No claim can be made about keys missing from live Secrets or manual kubectl patch/edit drift. ConfigMap/Secret updates alone do not alter environment variables in existing processes; any later verification must compare effective Pod environments to resource values, not just file-to-resource equality.

### Which source should be corrected

Preserve the current production encryption keys, JWT signing key, PostgreSQL credentials and Kafka storage identity. Establish whether `generated/` matches the initialized production state before changing it. Fix the duplicate and stale provider-input drift without rerunning the bootstrap generator against initialized storage. Persist the reviewed Supabase/public frontend settings in the production configuration source. Document the separate MCP resources and TLS ownership securely. The current image-only CD will neither apply a corrected ConfigMap nor reconcile private Secrets automatically.

## 8. Kubernetes Readiness and Health

| Workload | Startup | Liveness | Readiness coverage | Current Pod readiness |
| --- | --- | --- | --- | --- |
| API Gateway | /health/live, 5s × 60 | /health/live, 20s × 3 | /ready returns ready after startup config validation; does not check upstreams | Unverified; public gateway /ready 200 |
| Auth | /health/live, 5s × 60 | /health/live, 20s × 3 | DB SELECT 1 bounded to 3s; no SMTP/OAuth or Alembic check | Unverified |
| Workflow | /health/live, 5s × 60 | /health/live, 20s × 3 | DB SELECT 1 bounded to 3s; no gRPC dependencies/schema check | Unverified |
| Integration API | /health/live, 5s × 60 | /health/live, 20s × 3 | DB SELECT 1; no Kafka/Redis/Beat check | Unverified |
| Action | /health/live, 5s × 60 | /health/live, 20s × 3 | DB SELECT 1; no Gmail/provider or gRPC check | Unverified |
| Execution | /health/live, 5s × 60 | /health, 20s × 3 | Background consumer/dispatcher tasks must be alive, then DB SELECT 1 | Unverified |
| RAG | /health/live, 5s × 60 | /health/live, 20s × 3 | DB SELECT 1 only; Supabase/OpenAI intentionally outside probe | Unverified; reported failure cannot be confirmed |
| Frontend | /health, 5s × 60 | /health, 20s × 3 | Configuration plus gateway /ready request bounded to 3s | Unverified Pod; public /ready 200 |
| Integration worker | Broker control ping, 30s × 20 | Absent | Broker control ping, 30s; timeout 10s | Unverified |
| RAG worker | Broker control ping, 30s × 20 | Absent | Broker control ping; providers and DB not exercised | Unverified |
| Integration Beat | PID existence, 20s × 30 | Absent | PID exists; no broker/DB/schedule check | Unverified |
| MCP | Absent | Absent | Absent | Unverified; public OAuth discovery 200 |
| Six PostgreSQL | pg_isready, 10s × 60 | Absent | pg_isready; server accepting connections, not app password/schema verification | Unverified |
| Kafka | TCP 9092, 10s × 60 | Absent | Topic list through localhost broker, timeout 15s | Unverified |
| Redis | redis-cli ping, 10s × 60 | redis-cli ping, 10s × 6 | PING, timeout 5s | Unverified |

Backend HTTP readiness periods are 10 seconds with a 5-second kubelet timeout and failure threshold 3; their 3-second DB check fits that budget. Execution deliberately uses a stronger `/health` for liveness than its startup `/health/live`; it can restart when background tasks terminate. A dependency outage that kills those tasks can therefore affect restarts; actual events are required to assess it.

The reported RAG 0/1 could also result from image pull, missing Secret, startup crash, scheduling/memory pressure or failed probe transport; no Pod status, events, logs or termination state was accessible. The leading configuration hypothesis is S01 only **if** the live Pod inherited the mismatched input database credentials. Generated manifests are internally consistent and cannot prove or exclude a mismatch with an existing PostgreSQL PVC. Empty Supabase config can break document operations while DB readiness remains green.

No recent Pod logs/events were available, and no complete Pod description was printed. A future investigation should extract only readiness conditions, reason codes, restart counts, image references and redacted error categories. Treat these as distinct states: process running → container probe passes → Pod Ready → Service has a ready endpoint → dependency connectivity → requested application feature works. Evidence at one step does not prove the next.

## 9. Security Findings

- **Private permissions pass locally:** `/home/ubuntu/relay-k8s-private` and both subdirectories are mode 0700; all 21 manifest files are mode 0600. Ownership and wider host administrator access are not audited. The private directory is outside the checkout and Docker build contexts.
- **Current tracked-file exposure check:** only `.env.example` files are tracked. No tracked path contains relay-k8s-private. Comparing known private sensitive values against current tracked file contents found only the deliberately public DB placeholder present in five stale input copies and example templates; no nonplaceholder private credential matches were found in the checked strings of at least 12 characters. The separate RAG input password is also a generic placeholder. Report redaction checks verified that no standalone secret values or complete private database URLs are included. This is not a complete Git-history or image-layer secret scan.
- **Image source checks:** all nine application build contexts have Docker ignore rules excluding real .env files and key material. Python/MCP Dockerfiles copy explicit application paths; frontend copies its filtered context. CD uses per-component contexts and supplies no application runtime secrets as build args. Actual deployed image layers/history are Unverified.
- **Secret scope:** frontend gets no application Secrets; gateway gets only JWT. Each service gets its own Secret; worker sharing follows its service. Shared CM contains public settings, not credentials, in audited files. GOOGLE_CLIENT_ID is public identity material, and its Secret override is intentional.
- **ServiceAccount/RBAC:** app manifests use relay-app with token automount false. Infrastructure likewise disables token automount; MCP uses relay-app. No application Role/RoleBinding definitions were found. Cluster-wide bindings, default-SA rights, Secret API access, at-rest encryption and live service-account overrides are Unverified.
- **TLS:** repository ingress references relay-tls and relay-mcp-tls with appropriate public hostnames and frontend/MCP Service ports. Public requests verify usable TLS for both hosts. Actual Secret names, certificate expiry, chain storage and private key permissions inside the cluster are Unverified.
- **Internal network:** default-deny plus explicit DNS/HTTP/gRPC/infrastructure/provider policies is present. Full-k3s removes the hybrid external-infrastructure policy. The cluster infrastructure rule trusts all `app.kubernetes.io/part-of=relay` peers, including frontend; Redis has no auth and Kafka uses plaintext. Narrower access is a hardening opportunity, not proof of an active compromise. Actual network-policy enforcement, Traefik labels/peer CIDRs and DNS domain remain Unverified.
- **MCP proxy security:** explicit trusted IP/CIDR allowlist rejects trust-all networks; generic proxy headers are disabled. MCP network policy allows DNS and port 443 egress; Relay API access uses the public HTTPS route. Public discovery works, but live allowlist breadth and ingress NAT behavior cannot be assessed without cluster data.
- **Single-node limitations:** local-path storage and one replica do not tolerate node loss. Most app rollouts use maxSurge=0/maxUnavailable=1; workers, Beat and MCP use Recreate. These trade availability for capacity. Avoid claiming zero-downtime deployment. Eight declared PVCs total 9 GiB requested; actual utilization/backups unverified.
- **PostgreSQL roles:** application URLs use the same identity as POSTGRES_USER initialization. Review live role privileges and separation between migration/runtime roles; no live role query was executed. Do not infer actual privileges solely from present environment values.

## 10. Prioritized Remediation Plan

**No change below is authorized by this report.** Approval should follow a concrete reviewed diff or secure Secret-management plan. Do not rotate/recreate databases, encryption keys, JWT or Kafka identity as a troubleshooting shortcut.

### P0 — Investigate reported active failure before selecting a fix

| Action / exact resources | Affected service | Validation procedure | Rollback / approval consideration |
| --- | --- | --- | --- |
| Obtain an operator-provided least-privilege read-only kubeconfig; inspect namespace relay | All; prioritize Deployment/rag-service and StatefulSet/rag-postgres | Read selected statuses/EndpointSlices; compare env/Secret presence in memory; read redacted events/errors. Any pods/exec access needs explicit approval under this privileged-access restriction | Access arrangement only; no workload modification. Do not chmod/copy the administrator kubeconfig |
| Resolve S01: Secret/relay-rag-service, Secret/rag-postgres, Service/rag-postgres and existing PostgreSQL role/database | RAG API and worker | Compare actual URL host/port/pair to initialized database; connect with SELECT 1 in a read-only transaction; check alembic_version and vector extension without migrations | No proposed password change until root cause established. If a later Secret correction is approved, securely retain the prior version and account for Pod env refresh; Secret rollback does not change initialized DB role passwords |

There is no confirmed active P0 configuration fix from the evidence collected. Diagnose the reported RAG failure first; do not apply generated credentials merely because their files match.

### P1 — Correct configuration and source drift

| Exact source / resource | Affected service | Proposed change | Validation | Rollback consideration |
| --- | --- | --- | --- | --- |
| Private application-secrets/rag-service.yaml → relay-rag-service | RAG API/worker | Remove conflicting duplicate broker key after choosing verified intended source | Duplicate-key-aware parser; exactly one redis:6379 DB0 broker; compare live presence/equality without values | Retain secure prior version; do not reapply the conflicting file as a rollback |
| Production relay-config source, SUPABASE_URL; generated relay-rag-service remains secret-only | RAG API/worker | Persist the reviewed working-tree public setting in appropriate production config; release config explicitly | Render from a clean reviewed revision; value nonempty/valid HTTPS; verify actual Pod presence and key/project/bucket pairing without paid/write calls | Revert config revision only with awareness that empty value breaks storage; preserve provider credentials |
| Private application-secrets/* and generated/* ownership documentation | Six DB clients; integration worker/Beat | Stop using bootstrap input as live deployment source; reconcile approved authoritative files | Verify all six DB pairs against live and initialized state; both broker DB numbers; no template credentials | Preserve current known-working generated/PVC identity. Never rerun create-secrets.py to repair initialized production |
| Private relay-action-service Google pair and relay-rag-service OPENAI_API_KEY copies | Action and RAG | Reconcile differing provider credential sources securely after identifying intended live keys | Boolean consistency; provider/project metadata if available without charges; do not log/test secret values via paid requests | Retain previous valid credential version per provider policy; rotating encryption keys is unrelated |
| relay-mcp-config / relay-mcp-secret / relay-tls / relay-mcp-tls ownership | MCP and public ingress | Document existing sources/backups; supply private definitions only if actual omissions are confirmed | Live object existence/key presence; proxy CIDR and session-secret structure; TLS metadata only | Preserve current TLS/signing material; never overwrite functioning resources because no local file was found |

### P2 — Reliability and security

| Exact resource / file | Affected service | Proposed change | Validation | Rollback consideration |
| --- | --- | --- | --- | --- |
| deploy/kubernetes/mcp/deployment.yaml and MCP health implementation | MCP | Add suitable health checks; account for trusted-ingress middleware and startup behavior | Probe via allowed mechanism, verify successful readiness and rejection of invalid traffic; do not use a loopback HTTP request that is intentionally forbidden | Revert probe spec if it blocks healthy Pods; avoid needless session-destroying restarts |
| scripts/deploy-relay-k3s.sh and .github/workflows/cd.yml | All application deployments | Add read-only config/reference/schema drift gates and explicit approved config rollout steps | Check required resources/keys, pinned images, deployed schema compatibility and readiness at dependency level | Keep prior image AND configuration versions; image-only rollback cannot undo config/schema changes |
| NetworkPolicy/relay-cluster-infrastructure, StatefulSet/redis and both broker Secrets | Workers and data services | Evaluate client-specific access and coordinated Redis auth | DNS/connectivity from allowed callers; denial from unrelated workloads; broker/probe compatibility; no task publication in audit | Stage policies/auth together with a reviewed rollback; auth-only changes can disconnect both queues |
| Deployment/integration-celery-beat, worker probes, monitoring | Scheduling and RAG ingestion | Add read-only checks/alerts for dependencies and last successful operation; retain singleton Beat | Observe existing state/metrics without enqueueing work; assess hung process recovery | Revert monitoring/probe changes independently of queue and schedule state |
| Image selections / immutable production overlay and bootstrap manifests | All applications and infrastructure | Document/pin the reviewed release and prevent accidental reapply of dev/Never image defaults | Compare desired release to actual image digests; offline render; verify registry access separately | Keep previous working image references; do not assume GHCR private pulls work without live pull-secret checks |

### P3 — Optional cleanup

| Exact resource / file | Affected service | Proposed change | Validation | Rollback consideration |
| --- | --- | --- | --- | --- |
| Frontend env / ConfigMap relay-config: MCP_PUBLIC_ORIGIN | Frontend integrations UI | Set reviewed public MCP origin if integration UI should be enabled | Server-rendered integrations/dashboard show expected endpoint; OAuth discovery stays reachable | Remove optional setting to disable UI without affecting MCP server |
| service/{integration-service,rag-service}/app/celery_app.py | Celery | Consider topology-specific broker validation rather than a silent rag-redis fallback | Unit-level config check and offline render; avoid changing the supported Compose topology unintentionally | Keep explicit working broker Secrets; restore prior code if development compatibility changes |
| Shared relay-config and private-source documentation | All | Document intentionally unused per-service injections and override ownership; keep one authoritative release/config record | No missing consumer after narrowing any env injection; duplicate-key checks on all private YAML | Restore prior nonsecret mapping; do not delete settings based solely on one service not using them |

### Completion boundary and required follow-up evidence

To complete the requested **actual-cluster** audit, an operator-approved connection is still required. Outstanding: live resource inventory; Secret/CM key sets and boolean equality; effective container env presence; ready endpoints/DNS/gRPC reachability; read-only DB authentication/Alembic checks; Redis/Kafka non-mutating checks; recent RAG errors/events; image digests; PVC health; live RBAC/NetworkPolicy enforcement and MCP proxy/TLS resources. These checks are not replaced by offline rendering or four public 200 responses.

**Production readiness verdict: unverified, with confirmed configuration defects in the available sources. Prioritize diagnosing RAG with live evidence, then reconcile the duplicate broker key, committed Supabase setting, and authoritative private configuration. Approve fixes only after that evidence identifies the affected live resources. No production fixes were performed.**
