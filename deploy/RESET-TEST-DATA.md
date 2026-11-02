# Fresh disposable test environment — destructive, explicit opt-in

The owner has confirmed the current Relay data is **test data**, so preserving it
need not block a fresh test deployment. This document is a manual option, **not**
an action performed by this branch or permission to modify the Oracle VM now.
Normal startup and migrations never delete/reset data.

Prefer a new Compose project with new volumes when space allows. If reusing an
existing disposable test installation, the following operation permanently removes
that project's managed named volumes: all six databases, Kafka history/offsets and
Redis queues. Saved users, workflows, credentials, executions and ingested metadata
will be lost. External Supabase objects/provider accounts are not deleted.

1. Verify the target host and Compose project name, configuration files and actual
   attached volumes. Confirm **every** affected volume is disposable test data.
   Do not infer this from a folder name. Retain a backup if uncertain.
2. Stop external triggers and both Compose/Kubernetes application writers. There
   must be no other Beat, execution process or worker using these databases/queues.
3. Obtain action-specific approval before anyone executes the destructive command
   on a live host. Substitute the confirmed project name below deliberately.

```bash
# DESTRUCTIVE. Example only; NEVER use against real production data.
# Use the same explicitly reviewed Compose files/env as the target test project.
docker compose --project-name CONFIRMED_TEST_PROJECT down --volumes --remove-orphans
```

Do not run `docker system prune`, indiscriminate volume deletion, or `kubectl delete
namespace` as a substitute. Do not reset a shared database or object-storage bucket.

4. For a new empty Kafka store, set `KAFKA_LOG_DIRS=/var/lib/kafka/data` in the
   reviewed root env file so new data is persisted to the declared volume. Existing
   credential-encryption keys may be retained; changing them is unnecessary.
5. Keep the same confirmed project name through the entire fresh initialization.
   Follow the Docker guide: build/start infrastructure, provision the pgvector
   extension in the RAG database through the explicit migration prerequisite, run
   the six controlled migrations once, then start application services.
6. Recreate a synthetic user/workspace and test workflows. Leave real schedules,
   payments, email recipients and paid AI providers disabled until separately
   approved. Validate readiness, authentication and queue behavior before exposing
   the test system.

A fresh test reset is not a production upgrade strategy, and successful reset
procedures do not replace backup/restore verification for real data.
