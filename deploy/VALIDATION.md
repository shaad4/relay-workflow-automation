# Validation evidence and release gates

Executed in an isolated checkout on 2026-10-29, starting from
`dev` commit `93126e3252977f070914fadb1b43c496fc677df1`.
No live Oracle host, real provider credentials, DNS, firewall, IAM or production
data was accessed or changed. The checks below are not a production certification.

## Executed checks

| Check | Result / scope |
| --- | --- |
| API Gateway pytest | 109 passed; full service suite including deployment/legacy-alias/redirect tests. |
| Auth pytest | 58 passed; 87.06% branch-inclusive coverage, rerun after dnspython 2.9.0 security update. |
| Workflow pytest | 296 passed; 86.24% coverage. |
| Integration pytest | 126 passed; 82.87% coverage. |
| Action pytest | 62 passed; 86.00% coverage. |
| Execution pytest | 297 passed; 84.70% coverage, including real isolated PostgreSQL integration and gRPC tests. |
| RAG pytest | 102 passed; 86.42% coverage, including real isolated pgvector ranking/tenant/claim tests. |
| Backend total | **1,050 passed**. All seven suites exceeded the existing 80% coverage gate on the coverage runs (Gateway coverage run: 107 tests, 82.99%; two additional alias tests then passed). |
| Six Alembic histories | `upgrade head` succeeded on six independent, freshly created local test databases; pgvector explicitly provisioned in RAG first. No migration files changed. |
| Migration prerequisite | Actual-target pgvector preflight accepted installed extension and rejected absent extension. Shell orchestration test verified missing extension stops before every Alembic command. |
| Python Ruff | `ruff check service` and `ruff format --check service` passed, plus new deployment validator. |
| Python syntax | Service compile/AST checks passed; no new Python logging imports/initialization/calls. |
| Frontend tests | **129 passed, 1 optional Chromium test skipped**. Includes 21 initial deployment/auth-error tests and 4 slow-body/abort cases. |
| Frontend lint / format | ESLint 0 errors, 2 existing warnings; Prettier check passed. |
| Frontend production build | Next.js standalone production build passed. |
| Standalone HTTP smoke | Runtime gateway URL, login page, refresh/multiple cookies, CSRF rejection, OAuth redirects, health/readiness and dependency-failure handling passed using a local synthetic gateway. |
| npm audit | 0 vulnerabilities reported. |
| Bandit | All seven app trees passed the existing medium/high-severity and confidence policy, excluding generated gRPC code. |
| pip-audit | All seven locked dependency sets clean after fixing auth `dnspython` CVE-2026-114605 by updating 2.8.0 → 2.9.0. |
| Wheel availability | All seven exact Python dependency sets resolve binary-only for both amd64 and arm64 under Python 3.12 (14 successful resolutions). This is not an image build. |
| Compose | Development, frontend profile, production and private hybrid models render using Compose 2.39.4; precedence, production exposure, profile inventory and published-network invariants checked. |
| Kustomize | Development, production, zero-replica bootstrap, six migration Jobs and optional ingress composition render with Kustomize 5.7.1. |
| Kubernetes schemas | Strict kubeconform 0.7.0: 116 rendered resources valid, 0 invalid/errors/skips; 7 secret templates separately valid. |
| Static deployment invariants | Correct service inventory, no applied example Secrets/migration Jobs in normal rollouts, singleton execution/Beat, probes/security contexts, ClusterIP-only services, internal-only production stateful network passed. |
| Shell / whitespace | Shell syntax and `git diff --check` passed. |

The isolated DB server was PostgreSQL 16.2 with pgvector, installed only as local
test tooling—not added to Relay's runtime dependencies. Environment-provided SOCKS
proxy configuration required test-only `socksio` in the local RAG test environment;
initial client-construction failures were environmental, then all 102 tests passed.
No paid AI, mail, payment or storage operations were invoked.

## Checks not established locally

- **Docker image builds, container startup and image vulnerability scans:** no
  Docker daemon was available. The existing GitHub workflow now builds all 8 images
  for amd64/arm64, scans native images for fixable HIGH/CRITICAL vulnerabilities,
  and never pushes images or deploys. Inspect the PR checks for the exact final
  commit; workflow configuration alone is not a pass.
- **Full browser UI regression:** the optional Chromium test could not launch under
  sandbox socket restrictions; a permitted escalation attempt failed environment
  initialization. The suite's optional test remains skipped. Node tests, full
  build and standalone HTTP smoke passed, but do not replace visual/browser QA.
- **Live Compose/K3s networking, readiness, CNI policy enforcement, ingress/TLS,
  DNS/firewall configuration, resource limits under load and image imports** were
  not exercised. User-provided K3s system-pod/DNS observations are not application
  deployment verification.
- **Existing volume/Kafka layout, live upgrades, backup/restoration and external
  provider flows** require manual staging validation. Disposable current test data
  may use the explicit reset option; real production data requires backups.
- No TypeScript checker exists in this JavaScript frontend; ESLint and Next's
  production build are the available source/build checks. No new typecheck pass is
  claimed. No complete end-to-end multi-container workflow benchmark was run.

## Reproduce the non-live gates

```bash
# From repository root; per-service dependencies/test requirements installed.
ruff check service
ruff format --check service
python scripts/check_deployment.py
bash scripts/ci-compose-check.sh
kubectl kustomize deploy/kubernetes/overlays/development > /tmp/relay-development.yaml
kubectl kustomize deploy/kubernetes/overlays/production > /tmp/relay-production.yaml
kubectl kustomize deploy/kubernetes/migrations > /tmp/relay-migrations.yaml
# In frontend:
npm ci
npm test
npm run lint
npm run format:check
npm run build
npm run test:standalone
npm audit --audit-level=high
```

Backend integration tests require an **isolated local database named `ci_test`**,
never a production URL. Existing GitHub service-test jobs provision disposable
PostgreSQL/Redis for this purpose. Do not run their cleanup fixtures against real
data. See each service test suite and CI definition for precise synthetic env.
