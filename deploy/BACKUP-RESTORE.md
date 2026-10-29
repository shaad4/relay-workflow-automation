# Backups and restoration

These are **manual operator procedures**, not actions performed by this change.
Never reset/delete production data to make a migration pass. Keep backups and keys
outside Git, with restrictive filesystem permissions and an off-host encrypted
copy. Confirm the backup destination is not the same failure domain as the VM.

## Inventory and consistency

Record all six database names/versions and Alembic revisions, image tags, Compose
project/volume names, Kafka topics/consumer groups, Redis persistence settings,
Supabase bucket/object inventory, JWT and both credential-encryption key versions.
Back up the actual secret material through an existing secure mechanism; do not
print it in terminal logs or a support ticket.

Before a release, pause external triggers/writers as appropriate; stop the one
Celery Beat, workers and execution dispatcher and wait for in-flight work to drain.
A live `pg_dump` is transactionally consistent within **one** database, not across
six independently dumped databases, Kafka, Redis and external object storage.
For a coordinated recovery point, quiesce application writers and record queue
state. Do not replay unknown provider side effects after restoring an old snapshot.

## PostgreSQL logical backups (existing Compose infrastructure)

Select the correct Compose env/files first (see Docker guide). These commands
read container credentials internally; passwords are not command-line arguments.
`BACKUP_DIR` should be an operator-owned absolute directory outside the checkout.

```bash
umask 077
BACKUP_DIR=/secure/off-repo-backups/relay-YYYYMMDD-HHMMSS
mkdir -p "$BACKUP_DIR"
for database in auth-postgres workflow-postgres integration-postgres action-postgres execution-postgres rag-postgres; do
  if ! docker compose exec -T "$database" sh -c \
    'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
    > "$BACKUP_DIR/$database.dump.partial"; then
    echo "Backup failed for $database; do not use the partial file" >&2
    exit 1
  fi
  test -s "$BACKUP_DIR/$database.dump.partial" || exit 1
  mv "$BACKUP_DIR/$database.dump.partial" "$BACKUP_DIR/$database.dump"
done
sha256sum "$BACKUP_DIR"/*.dump > "$BACKUP_DIR/SHA256SUMS"
```

Review exit statuses; an existing nonempty file does not prove a successful dump.
Custom-format dumps can be listed with `pg_restore --list`, but only a successful
restore and application verification demonstrate usability. Also back up any
required database roles/grants separately using an authorized administrator, and
capture PostgreSQL/pgvector extension versions. No database password rotation or
schema change is part of this operation.

## Restore rehearsal, not in-place overwrite

Provision a **separate disposable** PostgreSQL instance/volume/project with a
compatible PostgreSQL major version and pgvector for RAG. Verify the target identity
and that it contains no production data. Create a new empty database and restore
each archive to its corresponding independent database using `pg_restore` with
`--exit-on-error --single-transaction`. Do not use `--clean` against a live target.
For example, after explicitly creating an isolated service named `restore-postgres`:

```bash
# This service/database must be a separately provisioned disposable test target.
# Do not substitute a production service or database here.
docker compose exec -T restore-postgres sh -c \
  'exec pg_restore -U "$POSTGRES_USER" -d relay_restore_test --exit-on-error --single-transaction' \
  < "$BACKUP_DIR/auth-postgres.dump"
```

Restore all required roles/ownership as appropriate to the recovery environment;
review `--no-owner` only when intentional. Verify extension availability, row
counts, Alembic current revision, representative workspace isolation, credentials
decryption, workflow/execution relationships and application login. Do not run
real schedules, webhooks or paid AI/integration operations from the restored copy.
Document actual restoration duration, backup age and validation results.

For a real recovery, obtain approval for the exact target and cutover. Stop old
writers first, preserve the old volumes for investigation, restore into replacement
storage, and reconcile message offsets and provider side effects before reopening
traffic. Rollback of images alone cannot reverse a destructive schema migration.

## Kafka, Redis and RAG objects

- Kafka's log/data volume and metadata are persistent. A raw filesystem copy of a
  running broker is **not** a verified backup. Use a broker-compatible snapshot or
  stop the broker after quiescing producers/consumers, copy the complete volume
  through the operator's existing storage backup process, and rehearse recovery.
  Capture listener configuration and consumer offsets. Avoid changing the Kafka
  cluster identity or formatting an existing volume.
- Redis append-only persistence is enabled. Verify persistence and disk space;
  use Redis-supported backup procedures or a cold copy after stopping its writers
  and server. A queue backup can reintroduce already-completed jobs on restore.
- RAG documents are stored in the existing Supabase bucket; PostgreSQL holds
  metadata/chunks. Back up object bytes plus identifiers and access policy through
  the existing storage account's supported export/versioning mechanism. A DB-only
  backup cannot recover deleted source objects. No new paid storage service is
  required or provisioned by this repository.

The Kubernetes topology initially keeps these stateful services external; the
same backup obligations apply. Kubernetes manifests, Secrets and Pod restarts are
not database backups or a substitute for disaster-recovery testing.
