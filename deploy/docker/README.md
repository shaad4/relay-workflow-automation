# Docker Compose operations

Requires Docker Engine and **Compose 2.24.4+** (`!reset`/`!override` remove inherited
ports and development env files). These files are templates, not permission to
change a live machine. No script changes host firewall, DNS or cloud rules.

## Configuration precedence and existing installations

* Root `.env` supplies **Compose interpolation** (database container credentials,
  published local ports, image names, concurrency). It is not injected wholesale
  into apps. Never print `docker compose config` with live credentials; use
  `docker compose config --quiet`.
* Development app env files load `service/<name>/.env.example` then the optional
  existing `service/<name>/.env`. The latter wins. Existing credentials and
  integration settings are not regenerated or overwritten.
* Production **replaces** that list with
  `${RELAY_ENV_DIR}/<service>.env`; no development fallback survives. Keep files
  outside the checkout and mode `0600` (directory `0700`). Env injection is visible
  to Docker administrators; it is not an encrypted vault.
* Keep actual old DB names/users/passwords, JWT key and both credential-encryption
  keys. Changing PostgreSQL image environment does **not** change passwords or
  rename a database already stored in a volume. Percent-encode credentials in
  `DATABASE_URL` and broker URLs. Quoted env values containing `$` must follow
  Compose's env-file quoting rules.
* Existing named volume keys and project name `relay-workflow-automation` are
  preserved. Container names are now generated; use service DNS and `docker
  compose` commands rather than hard-coded container names. Before upgrading,
  inspect volume mounts locally and preserve any existing project-name override.

## Existing Kafka installation: stop before recreation

The old Compose file mounted `/var/lib/kafka/data` without selecting `log.dirs`.
Apache's [image defaults](https://github.com/apache/kafka/blob/4.0.1/docker/server.properties)
use `/tmp/kraft-combined-logs`; your running broker may therefore have authoritative
segments, consumer offsets and KRaft metadata **inside the old container**, not in
the named volume. The new configuration explicitly selects `/var/lib/kafka/data`.
Do not blindly recreate or remove an existing broker container. Before any upgrade,
inspect the running broker's effective log directories, stop writers and the broker,
and preserve its complete metadata and segments under a reviewed offline backup /
restore procedure. Confirm ownership and cluster/node identity on a disposable
restore. Merely retaining `kafka_data` does not preserve data stored elsewhere.
No script here copies, formats or deletes Kafka data. `KAFKA_LOG_DIRS` is required explicitly (including for an existing root env file)
so an upgrade fails closed until storage has been reviewed. It is configurable
for a reviewed existing layout, but its directory must actually be volume-backed.
If the storage layout is uncertain, leave the running broker untouched and block
the rollout until the operator has verified it.

## Local development

```bash
cp .env.example .env
# Optional: copy a service/.env.example to service/.env for overrides.
# This helper creates missing root .env only; never overwrites service files.
./scripts/dev-up.sh
# A pgvector image has the extension binaries, but each RAG database needs activation.
# Fresh local database only: use its existing PostgreSQL administrator role.
docker compose exec -T rag-postgres sh -ec 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"'
# For a NEW database, or after a reviewed schema update, run once:
./scripts/migrate.sh
# Start all application services after migrations complete:
docker compose up -d --wait --wait-timeout 180
# Optional containerized frontend (otherwise npm run dev in frontend):
docker compose --profile frontend up -d --build frontend
```

For an already migrated database, `docker compose up -d --build` remains supported.
`/ready` needs a reachable database and execution background workers. A fresh
execution service may fail before migrations; migrate first, then restart it.
The committed values are local-only placeholders. Actual mail/OAuth, document
storage and AI integrations need the corresponding operator-supplied settings;
starting local containers does not configure these providers or call them.

Application ports and PostgreSQL debug ports bind loopback by default. Redis,
Kafka and gRPC are unpublished. Do not set a bind address to `0.0.0.0` to work
around a connectivity problem. The `backend` network is internal. Application containers also join the
outbound-capable default bridge for provider calls. In development and hybrid
mode, stateful containers join that default bridge too: Docker cannot publish
host ports from containers attached **only** to internal networks. Production
removes their default-bridge attachment and all stateful published ports. Hybrid
private binds therefore have a gateway-capable bridge, not an internal-only
network. This adds outbound capability in hybrid mode; assess that trade-off and
apply separately reviewed host policies if required. See the
[Moby maintainer explanation](https://github.com/moby/moby/discussions/53256).

## Production preparation (manual, no auto-deploy)

1. Inventory and back up all six databases, Redis/Kafka volumes and external RAG
   objects. Test a restoration into separate disposable storage. See the deployment
   backup/restore guide. Never use `down -v`, volume removal or schema reset.
2. Copy `production.env.example` outside the checkout and replace placeholders
   with **existing** deployment settings. Create six DB-backed service env files
   and the gateway env file in `RELAY_ENV_DIR`, using service examples as a key
   inventory, not as production defaults. Do not reuse the local database password
   or development JWT. Keep provider and encryption secrets in the relevant file.
3. Set `FRONTEND_URL=https://relay.example.com` and normally
   `BACKEND_URL=https://relay.example.com/api/relay`. Configure OAuth callbacks
   with that same public route. Browser requests use the frontend's same-origin
   `/api/relay`; `API_GATEWAY_URL` remains internal. No secret belongs in
   `NEXT_PUBLIC_*` or Docker build arguments.
4. Select immutable reviewed application image tags (prefer a commit SHA), test
   them, and retain the preceding tag for rollback. All seven services and the
   frontend use the same images in Compose and Kubernetes. Base images use
   multiarch tags; pin reviewed manifest-list digests for a controlled release.
5. Review CPU/memory/disk budgets and free headroom. Limits are caps, not capacity
   guarantees. The seven HTTP processes, three Celery processes, six databases,
   Kafka, Redis and frontend do not fit every small VM. Set limits from measured
   load; do not remove limits or increase workers to hide memory pressure.
6. Arrange HTTPS at the existing host reverse proxy. Adapt
   `nginx.conf.example`, provision certificates manually, and restrict the host
   and OCI network to intended public HTTP(S) access. The production override
   leaves only frontend `127.0.0.1:3000` and gateway `127.0.0.1:8001` published.
   PostgreSQL, Kafka, Redis and gRPC stay unpublished.

Use a private root env path below, replacing it with your actual path:

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.production.yml
export COMPOSE_ENV_FILES=/etc/relay/production.env
docker compose config --quiet
# Pull images prepared by your manually approved release process; no live CI deploy.
docker compose pull
docker compose up -d --wait --wait-timeout 180 auth-postgres workflow-postgres integration-postgres action-postgres execution-postgres rag-postgres rag-redis kafka
docker compose up -d kafka-init
docker compose wait kafka-init
# Quiesce ALL writers before all-six-service schema changes. Back up first.
# Stop external writers too; HTTP readiness alone does not prevent DB writes.
docker compose stop frontend api-gateway auth-service workflow-service integration-service action-service execution-service rag-service integration-celery-beat integration-celery-worker rag-celery-worker
# Administrator prerequisite: activate pgvector in the actual RAG database.
# This command is ONLY for RAG DATABASE_URL targeting this Compose database.
# For an external database, the DBA runs the same SQL against that exact target.
docker compose exec -T rag-postgres sh -ec 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"'
./scripts/migrate.sh
# Uses the selected existing images; never builds silently on the server.
docker compose up -d --no-build --pull never --wait --wait-timeout 180
docker compose ps
```

For local release builds, `docker compose build --pull` uses the same Dockerfiles;
validate both target architectures in CI before publishing a multiarch release.
`pgvector/pgvector` supplies the extension files, but does **not** activate the
extension in a database. The initial RAG migration needs `CREATE EXTENSION IF NOT
EXISTS vector;` in its exact target database. An administrator performs that
explicitly before migrations; do not grant the ordinary app user superuser solely
to make deployment work. Existing application DB passwords/roles stay unchanged.
The migration helper first queries `pg_extension` using the RAG application's
actual `DATABASE_URL` and stops before any service Alembic command if the extension
is missing or unreachable. This avoids quietly preparing the wrong Compose DB
when the service points at an external database. No extension is created during
normal application startup, and historical migration files are not rewritten.

No production schema migration occurs in a container startup command. Run
`migrate.sh` from **one** terminal/operator at a time, never alongside K8s migration
Jobs. Review Alembic history first; a migration failure is a stop condition.
Do not substitute `create_all`, delete tables, or automatically retry a destructive
migration.

## Health, shutdown and rollback

```bash
docker compose exec -T api-gateway python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready',timeout=3).read(); print('ready')"
docker compose exec -T execution-service python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready',timeout=3).read(); print('ready')"
# Stop new schedules first, then allow execution's 120-second shutdown grace:
docker compose stop integration-celery-beat integration-celery-worker
docker compose stop -t 120 execution-service
# RAG ingestion uses 600s soft / 660s hard task limits; preserve a longer grace:
docker compose stop -t 720 rag-celery-worker
docker compose stop
```

Docker marks failed checks unhealthy but does not itself restart an unhealthy
process; alert on readiness/task-health failures and investigate before manually
restarting. Execution image health checks include its consumer and dispatcher.

Keep one execution instance and **one Celery Beat globally**, including during a
Compose-to-K8s handoff. The integration/RAG worker concurrency settings default to
one. Raising worker counts does not establish exactly-once external side effects;
check idempotency, provider limits and the execution safety notes first. HTTP
services run one Uvicorn process because gRPC and execution consumers are embedded
in their lifespans. Never add `--workers` without checking those embedded servers.

For an application-only rollback, restore the preceding immutable image tag and
run the production `up` command again. Do not run Alembic downgrade automatically;
confirm schema backward compatibility or restore a verified backup into separate
storage under an approved recovery plan. Keep existing volumes attached.

## Hybrid: K3s applications, Docker infrastructure

`docker-compose.hybrid.yml` is an **opt-in trusted-private-network example**. Use
it with the base file, not the production override. It profiles application
containers off by default and preserves stateful volume names. It does not move
or migrate existing volumes into Kubernetes.

Before enabling its published ports:

* Set `RELAY_PRIVATE_BIND_IP` to the VM's stable private interface address, never
  `0.0.0.0`, a public address or a Docker container IP. Set `KAFKA_PRIVATE_HOST` to
  private DNS resolving to that interface **from pods**. K3s containerd cannot
  resolve Compose service DNS. Do not use `host.docker.internal` as portable K8s DNS.
* Permit only the required trusted pod/node source CIDRs to the private ports in
  both OCI security rules and the existing host firewall, manually. Docker's
  forwarding/NAT rules and K3s CNI rules require careful review; do not flush
  iptables, blindly insert accept rules, or expose Kubernetes API port 6443.
* Broker/database/Redis protocols in this example are not encrypted; Kafka and
  Redis are not authenticated. **This is not suitable for an untrusted/shared
  network.** Use protocol-native TLS/authentication or a separately secured tunnel
  before crossing that boundary, and configure matching application clients.
  No blanket firewall rule is supplied.
* Configure the six K8s DB URLs with private DNS and published ports
  auth 5434 / workflow 5433 / integration 5435 / action 5436 / execution 5437 / rag 5438, preserving
  each database's existing name/user/password. Redis is private 6379 (DB0 RAG,
  DB1 integration). Kafka is private 19092; its internal listener remains 9092.
  Both bootstrap **and advertised** broker addresses must be reachable from pods.
* Stop Compose Beat, execution and workers before starting their K8s replacements.
  Do not scale both deployments against the same queues during a handoff.

```bash
# Add the two private-network values to a mode-0600 operator root env file first.
export COMPOSE_FILE=docker-compose.yml:docker-compose.hybrid.yml
export COMPOSE_ENV_FILES=/etc/relay/production.env
docker compose config --quiet
# Run only after reviewing connectivity and taking backups; apps stay profiled off.
docker compose up -d --wait --wait-timeout 180 auth-postgres workflow-postgres integration-postgres action-postgres execution-postgres rag-postgres rag-redis kafka
docker compose up -d kafka-init
docker compose wait kafka-init
```

A single VM remains a single failure domain. Docker Compose and K3s on that VM
share CPU, memory, disk and network; K3s orchestration does not create HA.

## Dependency maintenance and validation

`requirements.in` is the editable input; `requirements.txt` contains exact resolved
runtime pins. `deploy/docker/python-constraints.txt` retains the existing pinned
shared-library baseline to limit unrelated upgrades. Use
`scripts/lock-python-dependencies.sh` with `uv`, review the diff and run tests plus
vulnerability scans. Test tooling and protobuf compilers are not runtime packages;
generated gRPC Python files remain committed.

CI builds `linux/amd64` and `linux/arm64`; Python builds require binary wheels and
fail clearly if an architecture lacks a wheel rather than embedding a compiler.
Config rendering is not a runtime test. Verify actual architecture builds, service
readiness, queue recovery, ingress/cookies, migration rollback policy and backups
in a staging environment before calling a release production-ready.

Reference: [Compose merge semantics](https://docs.docker.com/reference/compose-file/merge/)
and [environment precedence](https://docs.docker.com/compose/how-tos/environment-variables/envvars-precedence/).

For all infrastructure inside Kubernetes, see [Full K3s](../kubernetes/FULL-K3S.md). Compose remains independent and complete; full K3s does not require Compose at runtime.
