# Full-K3s validation evidence

Repository-only checks completed on 29 October 2026:

- Kustomize rendered development, production, bootstrap, full-k3s,
  full-k3s-migrations, existing migrations and both initialization stages.
- kubeconform v0.7.0, strict Kubernetes 1.36.0 schemas: **141 valid resources,
  zero invalid/error/skipped resources** across those eight renders.
- Existing deployment source/application/migration invariants passed.
- Full-K3s infrastructure checks passed: stateful inventory, private Services,
  PVCs, Secret references, DNS, Kafka retention/identity guards, resource budgets,
  probes, NetworkPolicies and singleton schedulers.
- Seven focused unittest cases passed: valid baseline, rejection of public DB,
  duplicate Beat, evicting Redis, wrong StorageClass, unknown application Secret,
  plus offline fresh credential pairing, permissions and overwrite refusal.
- Development, production and private hybrid Compose configurations rendered with
  synthetic credentials using the existing Compose validation script.
- All new shell scripts passed `bash -n`; new Python tooling passed Ruff lint and
  formatting checks; `git diff --check` passed.

CI is extended to run the new manifests, contracts, focused tests and strict
schema checks. Remote GitHub Actions execution has not been observed for this
branch. Backend/frontend code and images were unchanged; their application test
suites were not rerun for this infrastructure-only change.

No live apply, migration, image import, certificate issuance, OCI/DNS edit,
Docker stop/removal, live database query or workload smoke test was performed.
Image entrypoints, Kafka restart/PVC behavior, storage provisioning, actual CNI
policy enforcement, HTTPS/cookies/OAuth, resource consumption and business flows
still require operator testing on an approved environment. Schema validity does
not establish the availability of the exact claimed K3s distribution version.
