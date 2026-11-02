# Deployment audit

Baseline: `dev` commit `93126e3252977f070914fadb1b43c496fc677df1` (2026-10-29).
This is a source/configuration audit, not a certification of the running Oracle VM.
No live host, DNS, firewall, credentials, data, or cloud resources were changed.

## Architecture and concrete findings

| Area | Baseline finding | Deployment treatment |
| --- | --- | --- |
| Service discovery | Gateway HTTP upstreams, several gRPC clients, and all gRPC binds were hardcoded. | Independent environment-controlled HTTP/gRPC contracts, retaining service-DNS defaults and existing aliases. |
| Databases | Six separate PostgreSQL databases; six Alembic histories; auth SQLAlchemy `echo=True`. Action image ran migrations on every container start. | Preserve database ownership and all schema history; disable SQL echo; explicit controlled migrations, connection readiness/pools, no schema startup mutation. |
| Images | Seven Python images ran as root, no build-context exclusions; several floating dependencies; integration shipped pytest. Frontend lacked a container build. | Non-root production images, locked runtime dependencies, clean build contexts, exec-form single-process startup, production Next.js image. |
| Compose | Existing database/Kafka/Redis volume declarations; Kafka log directory was not explicitly aligned with its volume; mostly `service_started` dependencies; no frontend; hardcoded names; service-specific `.env` required without complete templates. | Keep development topology/volume names; health/readiness and safe configuration templates; production and opt-in private hybrid overrides. |
| Development helper | `scripts/dev-up.sh` silently inserted host iptables/NAT rules and relied on container names. | Remove automatic host firewall changes; documented operator diagnosis only. |
| Execution | Kafka consumer, lifecycle producer and dispatcher are embedded in the execution HTTP lifespan. Database claims/leases, trigger dedupe and conservative expired-lease handling already exist. | Keep one Uvicorn process and one execution replica, graceful shutdown allowance, no HPA. Do not interpret Kubernetes replication as duplicate-side-effect safety. |
| Schedules | Integration Celery Beat enqueues the schedule check every 60 seconds; schedule rows advance before Kafka publication, leaving a crash-window missed occurrence risk. | Exactly one Beat, Recreate strategy; no overlap during updates; concurrency1; retain semantics and document manual reconciliation instead of claiming lossless scheduling. |
| RAG | pgvector database, Redis ingestion queue, Supabase object storage and OpenAI embeddings; ingestion uses late acknowledgement/requeue on worker loss. | Preserve interfaces and storage; retain provider keys as optional until feature use; document provider/storage and idempotency caveats, no paid test calls. |
| Frontend | API URL was a `NEXT_PUBLIC_*` build constant; several auth failures fell back to pretend success. | Runtime server-side gateway configuration with same-origin browser requests; honest failures; no UI redesign. |
| Authentication | Existing JWT and encrypted credentials must survive redeployments. Cookie-origin checks already exist. | Preserve keys and cookie behavior, explicit HTTPS/origin configuration; do not rotate encryption keys as part of deployment. |
| Kubernetes | No deployment manifests. K3s containerd and Docker do not share image stores or DNS. | Kustomize application manifests and explicit manual migration Jobs; external stateful first, opt-in ingress, explicit private hybrid networking. |
| CI | Existing seven-service tests/coverage, Ruff, frontend tests/quality/security, Bandit and pip-audit. | Extend these checks with build/manifest/contract/image validation; no deployment job or production credentials. |

### Existing Kafka installations: stop before recreation

The original Kafka volume mounted `/var/lib/kafka/data`, but `KAFKA_LOG_DIRS` was
not set. The Apache image default may have stored broker metadata/log segments in
`/tmp/kraft-combined-logs` inside the old container writable layer. The new explicit
log directory makes fresh deployments persistent; **do not recreate an existing
broker until its effective log directory and data are inspected and preserved**.
A named volume alone is not proof of a usable backup. See the Docker guide for
the operator gate. No existing broker or volume was inspected/modified here.

## Execution invariants retained

- Kafka `workflow.triggered` ingestion persists the execution and workspace-scoped idempotency record before committing the consumer offset.
- Database-backed dispatch, lease ownership, heartbeat/recovery, guarded dead-letter replay and human approvals remain the existing engine.
- Kafka topic partitions/replication remain conservative for a single broker. Scaling a consumer group is not a substitute for reviewing side effects and database claims.
- Celery integration and RAG queues remain separate; their broker Redis databases are 1 and 0 by default. RAG late acknowledgements mean interrupted work can be redelivered; verify ingestion recovery using a disposable document, not production data.
- Existing OpenAI, Gemini and Anthropic BYOK connections and encryption keys remain compatible; there is no schema conversion or provider-interface rewrite.

## Explicit residual risks / operator decisions

1. Single-node Kubernetes is not high availability. PostgreSQL, Redis and Kafka need off-host backups, disk monitoring and tested restoration. Resource values are starting budgets, not measured capacity guarantees.
2. Hybrid routing requires stable private **host** DNS/IP endpoints and correct Kafka advertised listeners. Docker container IPs, loopback-only ports and Compose-only DNS names are not reachable from Kubernetes pods. CNI/firewall/NAT behavior must be tested on the actual host.
3. Internal gRPC/Kafka/Redis traffic remains trusted-network traffic. Never publish it to the Internet. NetworkPolicy is effective only with an enforcing CNI; container/host networking and SMTP/HTTPS/provider egress need operator review.
4. Existing integration/AI providers may incur charges. This work makes no provider calls, creates no billable services and does not authorize paid usage. Verify account limits before enabling real workflows.
5. Existing weak secrets are not silently rotated. Review JWT strength separately; replacing encryption keys without a controlled re-encryption process makes saved credentials unreadable.
6. RAG object storage and embeddings remain existing external dependencies, not a new self-hosted substitute. Back up objects and their metadata together. No live provider credentials were available for an end-to-end smoke test.
7. Migrations can be irreversible. Review pending Alembic revisions, take verified backups, stop writers when necessary, and run one migration operator per service. Image rollback is not database rollback.
8. Initial context reported unhealthy Oracle K3s components; a later user-provided terminal observation showed system Pods running, installation Jobs completed and cluster DNS resolving. This repository task did not independently verify the host, app migration, ingress or TLS. Any host operation remains separately authorized.

See [deployment guide](README.md), [Kubernetes guide](kubernetes/README.md), and
[validation evidence](VALIDATION.md) for implemented commands and verification boundaries.
