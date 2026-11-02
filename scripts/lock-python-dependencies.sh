#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
# uv is a developer-only lock tool, not an application dependency.
# Review the constraints and generated diff; run tests before committing updates.
for service in service/*; do
  uv pip compile "$service/requirements.in" \
    --python-version 3.12 --only-binary :all: \
    --no-header --no-annotate --output-file "$service/requirements.txt"
done
