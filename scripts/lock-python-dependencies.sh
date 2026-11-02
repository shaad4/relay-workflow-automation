#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
# uv is a developer-only lock tool, not an application dependency.
# Review the constraints and generated diff; run tests before committing updates.
# MCP maintains requirements.txt directly; compile only services with lock inputs.
for requirements_input in service/*/requirements.in; do
  uv pip compile "$requirements_input" \
    --python-version 3.12 --only-binary :all: \
    --no-header --no-annotate --output-file "${requirements_input%.in}.txt"
done
