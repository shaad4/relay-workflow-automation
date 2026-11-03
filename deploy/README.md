# Deployment

Relay supports Docker Compose and Kubernetes/K3s using the same application images.
Choose the guide for the environment you operate:

| Guide | Purpose |
| --- | --- |
| [Docker Compose](docker/README.md) | Local development, self-hosted production and private infrastructure for hybrid K3s |
| [Kubernetes/K3s](kubernetes/README.md) | Application overlays using existing external stateful services |
| [Full K3s](kubernetes/FULL-K3S.md) | Staged installation with PostgreSQL, Kafka and Redis inside Kubernetes |
| [Backup and restore](BACKUP-RESTORE.md) | Database, credentials and stateful-service recovery |
| [Frontend](../frontend/README.md) | Runtime proxy, health checks and browser configuration |
| [MCP server](../service/mcp-server/README.md) | stdio and OAuth HTTP transports, configuration and separate MCP deployment |

## Scripts and release workflow

- `scripts/dev-up.sh` starts the Compose development stack. `scripts/migrate.sh`
  runs explicit service migrations after checking the RAG pgvector prerequisite.
- `scripts/k8s/` provides the staged provisioning, migration, image import, rollout
  and verification commands documented in the Full K3s guide.
- `.github/workflows/ci.yml` runs tests, quality/security checks, image builds and
  offline deployment validation. These checks do not deploy an application.
- `.github/workflows/cd.yml` is manually dispatched from `main`. It publishes the
  nine application images to GHCR, then uses the Production environment gate and
  `scripts/deploy-relay-k3s.sh` to update existing Oracle K3s deployments.
- CD requires the application, worker and `relay-mcp` deployments to exist already.
  Initial provisioning, secrets, ingress and schema migrations are separate steps.
  MCP manifests live in `kubernetes/mcp/`, outside the application Kustomize base.
  CD also reconciles MCP's persistent storage mount and verifies its OAuth schema.
  Preserve the MCP session/encryption key and PVC across releases.

## Configuration and recovery

Use each service's `.env.example` as its configuration inventory. Compose env files
interpolate the model; Kubernetes uses ConfigMaps and service-specific Secrets.
The example files contain placeholders and must not be applied as real credentials.

Keep the six service databases separate. Preserve existing JWT and credential
encryption keys when upgrading, and back them up with the data they protect.
Use private database, Kafka, Redis and gRPC endpoints; expose only the intended
HTTP ingress. Configure HTTPS origins, cookies and provider callbacks together.

Keep a single scheduler Beat and the documented execution worker topology. Stop
and drain writers before migrations; do not start duplicate schedulers or consumers
during a topology change. Startup and release scripts do not reset application data.

Before a production release, verify a backup restore, review pending migrations,
select immutable image tags and retain schema-compatible rollback images. Check
readiness plus authentication, workflow publication, triggers, approvals, scheduling
and RAG ingestion. A healthy HTTP endpoint alone does not verify those workflows.
