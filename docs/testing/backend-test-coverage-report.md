# Relay backend test coverage report

Measured on 23 October 2026 using Python 3.12. No production implementation, API, schema, environment file, or Docker Compose file was modified.

## Executive summary

All seven complete backend suites pass and exceed 80% measured statement coverage. CI now enforces an even stricter 80% combined statement/branch threshold independently for each service. Coverage includes all application modules except generated gRPC/protobuf code. No handwritten production modules were excluded.

External AI, HTTP connector, Gmail, Stripe, storage, Kafka and gRPC boundaries are mocked in unit tests. Database integration tests use a dedicated local pgvector PostgreSQL 16 container and a guarded `ci_test` database on port 55432, separate from existing Relay databases. They use synthetic credentials and unique test records, with scoped cleanup rather than table truncation.

## Coverage results

| Service | Tests | Passed | Failed/errors | Skipped | Statement | Branch | Combined CI metric | Time (s) | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| api-gateway | 68 | 68 | 0 | 0 | 82.34% | 66.67% | 81.03% | 3.61 | PASS |
| auth-service | 53 | 53 | 0 | 0 | 87.80% | 73.03% | 85.78% | 7.02 | PASS |
| workflow-service | 142 | 142 | 0 | 0 | 84.72% | 67.42% | 80.93% | 7.54 | PASS |
| integration-service | 123 | 123 | 0 | 0 | 82.18% | 80.88% | 81.96% | 7.14 | PASS |
| execution-service | 245 | 245 | 0 | 0 | 85.80% | 75.29% | 83.72% | 37.14 | PASS |
| action-service | 54 | 54 | 0 | 0 | 87.03% | 78.70% | 85.17% | 2.01 | PASS |
| rag-service | 99 | 99 | 0 | 0 | 85.11% | 79.05% | 84.16% | 15.50 | PASS |

Total: 784 tests, 784 passed, 0 failed/errors, 0 skipped. Summed service test time: 79.95s; services ran in parallel, so this is not wall time.

Statement and branch percentages are reported separately from Coverage.py’s branch-inclusive combined percentage. Rounded display values are not used to determine pass/fail.

## Initial audit and coverage gaps

The existing repository already contained tests in all services. Initial runs exposed missing packages in the temporary local environment, stale Execution error-message expectations, a changed health signature/lifespan, an incomplete SQLite history fixture, and a finalization fixture that predated DLQ insertion. These were corrected only in tests or the temporary environment. Existing CI exempted RAG from its coverage gate and did not measure branches.

| Service | Module / gap found | Priority | Work / evidence |
|---|---|---|---|
| Execution | Dispatcher capacity, cleanup, polling, cancellation, duplicate IDs | Critical | Real async dispatcher tests for 5, 10, 25 tasks, five active permits, wakeups, two-second timeout argument, graceful drain and cancellation |
| Execution | Queue atomic claim, ownership, lease expiry, duplicate events | Critical | Real PostgreSQL transactions: 25 competing claimants, ten duplicate deliveries, owner renewal and foreign-owner rejection |
| Execution | Heartbeat lease loss / DB failure | Critical | Failed renewals cancel owner; heartbeat cancellation propagates |
| Execution | Shared AI provider semaphore | Critical | 25 requests across three instances/providers; maximum ten active calls; success, exceptions and cancellation |
| Execution | DLQ and replay safety | Critical | Real failed step creates DLQ; GET/HEAD replay accepted, POST rejected; repeated replay rejected; scoped resolve |
| Execution | Provider error and transport cleanup | High | OpenAI/Anthropic/Gemini status mapping, credential-probe cleanup, RAG gRPC errors, Kafka lifecycle failures |
| Action | HTTP concurrency and independent connectors | Critical | 25 HTTP calls; maximum ten; failure/cancellation release; non-HTTP completes while HTTP waits |
| Workflow | Integration webhook lifecycle and transport | High | Activation/revocation failure translation, client cleanup, schedule and webhook protobuf identifiers/deadlines |
| Gateway | Public webhook request/response propagation | High | Payload/signature preservation, hop header removal, production/test paths, invalid tokens |
| RAG | Vector persistence, isolation and atomic ingestion | Critical | Real 1536-dimension pgvector cosine ranking, top-K, pending-document filtering, workspace/KB isolation and ten competing ingestion claims |
| Auth / Integration | Existing suites and worker paths | High | Full suites executed with coverage; remaining gaps listed below |

## Critical reliability results

- Dispatcher: all new concurrency, cleanup, polling, duplicate-ID, graceful shutdown and cancellation tests pass. Polling uses a short controlled wait while asserting the production two-second timeout argument; it is not a wall-clock timing benchmark.
- AI: 25 calls share ten permits across OpenAI, Gemini and Anthropic, including separate AIService instances. Failure and cancellation free permits. Provider SDKs are mocked; no paid generation occurs.
- HTTP: 25 requests share ten permits on one ActionInternalService instance. Success, exception and cancellation cleanup pass. A non-HTTP connector completes while HTTP work is blocked.
- Queue: exactly one of 25 real concurrent PostgreSQL claim attempts wins. Only the owner can renew or finalize; expired leases reject renewal/finalization. Ten duplicate events produce one execution and a workspace-scoped idempotency key.
- DLQ: terminal failure persists a DLQ entry and failed-step attempt count. GET/HEAD replays preserve replay origin and start node. POST replay is unsafe; replayed/resolved events reject another replay. Resolve and workspace isolation pass.
- Retry: existing retry, error-classifier, AI runner and RAG suites pass. They cover retryable failures, terminal failures and downstream suppression. Remaining retry lines are explicitly listed below; this is not a claim of exhaustive retry fault injection.
- RAG: real PostgreSQL vector values produce expected cosine distances and ranking. Only ready documents in the requested workspace and knowledge base are returned. Exactly one of ten concurrent document claims wins.

## Reproduce locally

From the repository root, create an isolated environment and install dependencies for the service under test (CI installs each service independently):

```bash
python3.12 -m venv /tmp/relay-backend-tests
/tmp/relay-backend-tests/bin/python -m pip install -r service/execution-service/requirements.txt -r requirements-test.txt
docker run -d --name relay-coverage-postgres -e POSTGRES_USER=relay -e POSTGRES_PASSWORD=relay -e POSTGRES_DB=ci_test -p 127.0.0.1:55432:5432 pgvector/pgvector:pg16
export DATABASE_URL=postgresql+asyncpg://relay:relay@localhost:55432/ci_test
export JWT_SECRET_KEY=ci-test-secret-key-that-is-long-enough-for-hs256
export JWT_ALGORITHM=HS256
export FRONTEND_URL=http://localhost:3000
export AUTH_SERVICE_URL=http://localhost:8000
export OPENAI_API_KEY=ci-synthetic-key-no-network-calls
cd service/execution-service
/tmp/relay-backend-tests/bin/python -m alembic upgrade head
/tmp/relay-backend-tests/bin/python -m pytest tests --cov=app --cov-branch --cov-report=term-missing --cov-report=html --cov-report=xml:coverage.xml --cov-report=json:coverage.json --cov-fail-under=80 --junitxml=test-results.xml
```

Run the same pytest command from each other service directory after installing its `requirements.txt` and the root `requirements-test.txt`. RAG integration tests initialize the vector extension and their tables in the guarded isolated test database. Execution integration tests require the migrated schema. No `.env` edits are needed.

## CI verification

Updated `.github/workflows/service-tests.yml` retains its existing seven-service matrix and frontend job. Each backend job uses Python 3.12, isolated pgvector PostgreSQL 16 and Redis 7, installs development test dependencies separately, measures branch coverage, fails on tests or coverage below 80%, and uploads HTML/XML/JSON coverage plus JUnit results. RAG no longer has an exemption.

Local verification: all seven full pytest commands returned exit code 0 using the same pytest/cov options and per-service configuration (HTML/JSON/JUnit paths were redirected under `/tmp/relay-backend-coverage`). XML was exported from the same coverage data afterward. CI YAML parses successfully and contains all seven matrix entries. `git diff --check` passed. GitHub-hosted Actions was not triggered or observed; remote runner execution and artifact upload remain unverified.

Local detailed artifacts: `/tmp/relay-backend-coverage/<service>.log`, `<service>.json`, `<service>.xml` (JUnit), `<service>-coverage.xml`, and `<service>/index.html`. These are machine-local artifacts and are not committed.

## Remaining risks

- Branch coverage is below 80% for six services; Integration exceeds it. The mandatory per-service statement target is satisfied, and the branch-inclusive combined gate passes everywhere.
- Security and execution-critical modules are not uniformly at 90%; in particular Auth token session error/revocation paths and Execution administrative routes still have gaps. Engine runner and error classifier coverage are substantially higher; see the measured module table below.
- The suites use controlled external boundaries. Live Kafka broker delivery/redelivery, multi-process Celery/Redis behavior, third-party availability and real provider credentials were not exercised. The CI Redis service is provisioned but these tests do not claim live Celery broker integration.
- PGVector and execution queue tests use PostgreSQL; existing history grouping tests use SQLite and do not establish PostgreSQL query-planner performance.
- Concurrent claim/idempotency behavior is verified with independent transactions. DLQ duplicate replay rejection is verified sequentially; a concurrent replay race is not separately stress-tested.
- Dispatcher and connector semaphore limits are verified within their current process/service-instance scope. Distributed global limits, process restarts under load, sustained soak testing and crash recovery are not established by these tests.
- Existing RAG tests emit one LangChain pending-deprecation warning.
- No production fixes were made. The application was preserved per the user’s explicit instruction.

## Exact remaining missing lines

All handwritten modules with uncovered statements are listed below from the final coverage JSON. Missing branch counts are included; use HTML/JSON artifacts for individual branch arcs. Empty modules and modules with complete statement coverage are omitted from this display, not from measurement.

### api-gateway

| Module | Statement | Branch | Missing statement lines | Missing branches |
|---|---:|---:|---|---:|
| `app/main.py` | 96.23% | 62.50% | 35-36 | 3 |
| `app/routes/ai_provider_connections.py` | 92.86% | 75.00% | 35, 66-67 | 1 |
| `app/routes/approvals.py` | 96.55% | 75.00% | 45 | 1 |
| `app/routes/auth.py` | 94.44% | 75.00% | 12 | 1 |
| `app/routes/connections.py` | 71.93% | 50.00% | 33, 37, 41, 45, 49, 53, 112-113, 126, 128, 130-131, 133, 135-136, 148 | 2 |
| `app/routes/dead_letter.py` | 43.59% | 0.00% | 34, 45, 55, 66, 77, 79, 83, 88, 93, 97, 104, 112, 119-120, 124, 131-132, 137-138, 144, 152, 159 | 2 |
| `app/routes/executions.py` | 40.00% | 0.00% | 30, 38, 49, 59, 61, 65, 70, 75, 77, 83, 91, 98-99, 103, 110-111, 116-117, 122, 130, 137 | 2 |
| `app/routes/integration.py` | 53.66% | 0.00% | 12, 16, 20, 27, 31, 35, 39, 43, 51, 53, 55-56, 61, 63-64, 66, 68-69, 81 | 4 |
| `app/routes/knowledge_bases.py` | 80.00% | 50.00% | 36, 41, 49, 59, 70, 90, 103, 116, 134, 187-188 | 1 |
| `app/routes/manual_triggers.py` | 87.50% | 100.00% | 21 | 0 |
| `app/routes/schedules.py` | 75.00% | 100.00% | 20, 31, 43, 54, 66 | 0 |
| `app/routes/workflows.py` | 97.40% | 50.00% | 56, 229 | 1 |

### auth-service

| Module | Statement | Branch | Missing statement lines | Missing branches |
|---|---:|---:|---|---:|
| `app/core/dependencies.py` | 77.55% | 66.67% | 18-19, 33, 67-71, 76, 84-85 | 4 |
| `app/grpc/auth_server.py` | 83.78% | 70.00% | 39-42, 50-51 | 3 |
| `app/main.py` | 72.22% | 12.50% | 41-42, 47, 54-59, 63 | 7 |
| `app/routes/auth.py` | 91.18% | 73.08% | 115-116, 195, 199-201, 239, 241, 281, 283, 311, 313, 390, 429, 451 | 7 |
| `app/schemas/auth.py` | 90.62% | 50.00% | 13, 18, 23, 28, 33, 38 | 6 |
| `app/services/auth_service.py` | 80.77% | 87.50% | 23, 53-55, 98-100, 115-117 | 1 |
| `app/services/email_service.py` | 94.44% | 100.00% | 145-146, 150 | 0 |
| `app/services/email_verification_service.py` | 82.46% | 91.67% | 57-59, 87-89, 131, 138-140 | 1 |
| `app/services/google_login.py` | 89.74% | 87.50% | 33-35, 77 | 1 |
| `app/services/google_oauth.py` | 98.08% | 93.75% | 27 | 1 |
| `app/services/google_signup.py` | 88.52% | 93.75% | 39-41, 120, 169-171 | 1 |
| `app/services/password_reset_service.py` | 88.00% | 100.00% | 67-69, 133-135 | 0 |
| `app/services/token_sessions.py` | 63.16% | 35.71% | 35-37, 60-61, 64, 71-72, 84, 86, 119-124, 126-127, 132-141 | 9 |

### workflow-service

| Module | Statement | Branch | Missing statement lines | Missing branches |
|---|---:|---:|---|---:|
| `app/db/database.py` | 88.89% | 50.00% | 11 | 1 |
| `app/grpc/auth_client.py` | 56.25% | 100.00% | 12-13, 16, 20, 23, 27, 30 | 0 |
| `app/grpc/execution_client.py` | 66.67% | 100.00% | 15-16, 21, 28, 31 | 0 |
| `app/grpc/workflow_server.py` | 95.71% | 93.75% | 178-180 | 1 |
| `app/main.py` | 78.38% | 25.00% | 32-33, 42-47 | 6 |
| `app/routes/workflows.py` | 72.28% | 46.00% | 51-52, 114, 134, 170, 185, 191-195, 199, 204-207, 212, 218-220, 239, 264, 270, 294, 326, 329, 335, 361, 389-390, 396, 423-424, 430, 455-456, 462, 488, 517-518, 524, 552-553, 559, 582, 612-613, 619, 630-631, 654-655, 658, 685-686, 689 | 27 |
| `app/schemas/node_configuration.py` | 63.04% | 19.57% | 53, 118, 120-121, 123, 131, 133-134, 136, 140, 145-146, 150, 152-153, 157, 165-167, 171, 205, 207, 210, 212, 217-218, 222, 239, 241-242, 246, 270-271, 276, 309-312, 314-316, 320-321, 325-327, 331-332, 336-337, 341 | 37 |
| `app/services/workflow_service.py` | 88.29% | 80.80% | 109, 194, 200, 214-216, 389, 401, 413, 495, 507, 510, 549-551, 572, 584, 611-613, 635, 647, 650, 722, 753, 765, 768, 780, 793, 812-814, 836, 848, 851, 868-870, 1079-1080, 1083-1085, 1088, 1104-1105, 1109-1111, 1115, 1165, 1363, 1373, 1396, 1452, 1454, 1473-1475, 1492, 1506-1508 | 43 |

### integration-service

| Module | Statement | Branch | Missing statement lines | Missing branches |
|---|---:|---:|---|---:|
| `app/db/database.py` | 87.50% | 50.00% | 19, 29 | 2 |
| `app/grpc/server.py` | 44.44% | 100.00% | 8-9, 13-15 | 0 |
| `app/grpc/webhook_lifecycle_server.py` | 16.46% | 100.00% | 20-27, 29-31, 38, 41-44, 47-54, 56-58, 64, 67-70, 74-77, 80-81, 86-88, 97, 101-102, 108-112, 117-119, 125, 129-130, 136-140, 145-147, 153, 157-158 | 0 |
| `app/grpc/workflow_client.py` | 78.95% | 100.00% | 36, 41, 53, 59 | 0 |
| `app/main.py` | 69.23% | 0.00% | 15-19, 21-23 | 2 |
| `app/routes/public_webhooks.py` | 81.71% | 72.73% | 90-99, 147, 160, 171, 179, 190 | 12 |
| `app/routes/schedules.py` | 36.17% | 100.00% | 35-38, 43-44, 57-60, 65-66, 80-83, 88-89, 105-108, 113-114, 130-133, 138-139 | 0 |
| `app/routes/webhooks.py` | 81.30% | 70.83% | 32-33, 48-49, 99-100, 116-117, 139-140, 217-228, 231 | 7 |
| `app/schemas/events.py` | 89.47% | 50.00% | 26, 31 | 2 |
| `app/services/webhook_service.py` | 82.17% | 75.00% | 47, 184, 238, 242-243, 245-251, 261, 269-278 | 6 |
| `app/services/workflow_schedule_service.py` | 94.81% | 85.00% | 244, 247-250, 276-277 | 6 |

### execution-service

| Module | Statement | Branch | Missing statement lines | Missing branches |
|---|---:|---:|---|---:|
| `app/ai/base.py` | 91.67% | 100.00% | 25 | 0 |
| `app/ai/config.py` | 75.00% | 50.00% | 9 | 1 |
| `app/ai/encryption.py` | 95.83% | 83.33% | 39 | 1 |
| `app/ai/schemas.py` | 89.58% | 58.33% | 35, 53, 58, 88, 100 | 5 |
| `app/ai/service.py` | 90.74% | 88.89% | 37, 64, 85, 93, 110 | 2 |
| `app/db/database.py` | 88.89% | 50.00% | 16 | 1 |
| `app/engine/error_classifier.py` | 91.67% | 90.62% | 144-146, 239-241, 243 | 3 |
| `app/engine/executor.py` | 96.97% | 83.33% | 51 | 2 |
| `app/engine/handlers/ai_decision.py` | 22.22% | 0.00% | 21-22, 24-25, 29, 31-32, 36-38, 41, 44, 48-49, 51-52, 54-55, 57, 62-63, 70-71, 75, 79, 86, 88, 95 | 8 |
| `app/engine/handlers/rag_search.py` | 94.59% | 85.00% | 14, 22 | 3 |
| `app/engine/retry.py` | 91.67% | 70.00% | 73, 84, 100 | 3 |
| `app/engine/runner.py` | 96.81% | 83.33% | 69, 123, 160, 169, 210, 487, 531, 624, 706, 734-735 | 18 |
| `app/grpc/server.py` | 44.44% | 100.00% | 8-9, 12-14 | 0 |
| `app/kafka/consumer.py` | 93.55% | 75.00% | 65, 83 | 2 |
| `app/main.py` | 79.01% | 33.33% | 41-43, 49-51, 53-54, 80-83, 85, 145-146, 153, 200 | 4 |
| `app/repositories/ai_provider_connection.py` | 37.50% | 0.00% | 21, 29-30, 32, 39, 44-45, 51, 59-60, 69-70, 72-73, 75-76, 78-79, 85-86 | 6 |
| `app/repositories/dead_letter.py` | 95.35% | 50.00% | 130, 144 | 3 |
| `app/repositories/execution.py` | 71.28% | 66.67% | 67-68, 70, 94-95, 97, 107-108, 125, 129, 133-134, 139-140, 142, 144-145, 147, 200-202, 222-224, 246-248 | 4 |
| `app/repositories/execution_queue.py` | 87.76% | 50.00% | 88, 91, 134, 137, 171, 196 | 6 |
| `app/routes/ai_provider_connections.py` | 34.78% | 0.00% | 30-31, 44, 46-47, 53-54, 59, 72, 74, 78, 95, 97, 102-103, 108, 123, 125-126, 131-132, 137-138, 143, 157, 159, 164-165, 170, 179, 181-182, 187-188, 193-194, 199, 212, 214-215, 220-221, 226-227, 232 | 6 |
| `app/routes/approvals.py` | 94.12% | 91.67% | 41-43, 47-48, 233 | 1 |
| `app/routes/dead_letter.py` | 36.00% | 0.00% | 19-20, 34, 36-37, 39, 57, 59-60, 62, 67-68, 73, 83, 85-86, 88, 93-94, 99, 110, 112-113, 115-116, 121-122, 124-125, 130-131, 136 | 8 |
| `app/routes/executions.py` | 68.00% | 62.50% | 24-25, 60, 88, 95-96, 113-114, 116-117, 119, 124-125, 130, 132-133 | 3 |
| `app/schemas/ai_provider_connection.py` | 66.00% | 0.00% | 23-25, 30, 32-33, 35, 48-52, 57-61 | 12 |
| `app/services/ai_provider_connection.py` | 85.71% | 69.23% | 100, 106, 111-112, 114, 120, 135-137, 157-159 | 8 |
| `app/services/approval_service.py` | 98.11% | 86.36% | 99, 137 | 3 |
| `app/services/dead_letter.py` | 84.88% | 66.67% | 146, 149, 160, 168, 210, 216, 227, 233, 245, 253, 283-285 | 10 |
| `app/services/execution_dispatcher.py` | 90.62% | 93.75% | 88-91, 115-116 | 1 |
| `app/services/execution_history.py` | 87.18% | 66.67% | 63, 97, 102-103, 105 | 4 |
| `app/services/execution_queue.py` | 58.62% | 47.83% | 42-43, 51, 53, 55, 73, 108-109, 117, 122, 127, 162, 164, 182, 185, 206-208, 235-237, 255, 304, 386-388, 400, 402, 407-408, 412-413, 420, 422-423, 427-428, 431-433, 435, 441, 443-444, 448, 456-457, 466-467, 477-479, 481-482, 485-486, 488-491, 493, 496, 498-501, 503, 512-513, 517-518, 526-527, 535, 539, 541-544, 557-558, 560, 564, 568 | 24 |
| `app/services/replay_validator.py` | 75.00% | 44.44% | 25, 28, 33, 41, 51-52, 57-58 | 10 |
| `app/utils/payload_sanitizer.py` | 77.78% | 73.08% | 63, 85, 101, 113-114, 119, 135, 146-147, 150-151, 153 | 7 |

### action-service

| Module | Statement | Branch | Missing statement lines | Missing branches |
|---|---:|---:|---|---:|
| `app/connectors/base.py` | 83.33% | 100.00% | 17 | 0 |
| `app/connectors/gmail.py` | 94.34% | 85.00% | 31, 40, 107 | 3 |
| `app/connectors/stripe.py` | 85.71% | 75.00% | 27, 36, 39, 42, 46-47, 59 | 5 |
| `app/core/encryption.py` | 70.83% | 50.00% | 14, 23-24, 30, 42, 50-51 | 3 |
| `app/db/database.py` | 88.89% | 50.00% | 15 | 1 |
| `app/dependencies.py` | 91.67% | 100.00% | 9-10 | 0 |
| `app/grpc/action_server.py` | 74.07% | 59.26% | 29, 87-88, 92, 94, 98, 101-102, 106, 110-111, 115-117, 120-121, 125, 129-130, 134-136, 140-141, 145-146, 150, 203 | 22 |
| `app/grpc/auth_client.py` | 56.25% | 100.00% | 12-13, 16, 20, 23, 27, 30 | 0 |
| `app/grpc/server.py` | 44.44% | 100.00% | 8, 10, 15, 17, 19 | 0 |
| `app/main.py` | 75.00% | 100.00% | 12, 14, 16, 30 | 0 |
| `app/routes/gmail_oauth.py` | 87.74% | 86.67% | 83, 106, 111, 134-136, 210-212, 227, 273-275 | 4 |
| `app/services/connection_service.py` | 83.48% | 86.36% | 57, 64, 82-83, 101-103, 146, 148-150, 175-177, 201-203, 293-294 | 6 |

### rag-service

| Module | Statement | Branch | Missing statement lines | Missing branches |
|---|---:|---:|---|---:|
| `app/api/routes/documents.py` | 68.63% | 100.00% | 77, 137, 139, 142, 149-150, 156, 159-160, 162-163, 175-177, 179, 184 | 0 |
| `app/api/routes/knowledge_bases.py` | 97.67% | 87.50% | 125 | 1 |
| `app/db/database.py` | 77.78% | 100.00% | 24-25 | 0 |
| `app/dependencies.py` | 86.36% | 90.00% | 37-38, 53 | 1 |
| `app/grpc/auth_client.py` | 61.54% | 100.00% | 16, 20, 25, 29, 35 | 0 |
| `app/grpc/rag_server.py` | 80.95% | 80.00% | 112, 114, 119, 121-122, 124, 126, 128 | 2 |
| `app/main.py` | 0.00% | 100.00% | 2, 4, 6, 9, 12, 15-16, 20, 22-23, 27, 30, 37-38, 41-43 | 0 |
| `app/parsers/document_parser.py` | 88.89% | 75.00% | 24 | 1 |
| `app/parsers/document_processor.py` | 90.00% | 50.00% | 26 | 1 |
| `app/parsers/pdf_parser.py` | 18.18% | 0.00% | 10-11, 13-14, 16-17, 21, 23-24, 26-27, 29-30, 34, 36-38, 40 | 12 |
| `app/parsers/text_chunker.py` | 90.00% | 83.33% | 11 | 1 |
| `app/parsers/text_parser.py` | 90.00% | 75.00% | 15 | 1 |
| `app/repositories/document.py` | 94.83% | 75.00% | 143-144, 146 | 1 |
| `app/services/document.py` | 77.01% | 71.43% | 89-91, 117-118, 120, 170, 190-191, 205-206, 211-213, 240, 260-261, 270-272 | 4 |
| `app/services/ingestion.py` | 85.33% | 75.00% | 94-96, 114, 129, 146, 169, 202, 208-209, 211 | 5 |
| `app/services/knowledge_base.py` | 87.10% | 50.00% | 32-34, 70 | 1 |
| `app/tasks/ingestion.py` | 69.57% | 100.00% | 26, 31, 36-38, 40, 46 | 0 |
