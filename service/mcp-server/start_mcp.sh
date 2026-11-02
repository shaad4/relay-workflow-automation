#!/usr/bin/env bash
set -e

cd /home/ubuntu/Projects/relay-workflow-automation/service/mcp-server

set -a
source .env.local
set +a

exec .venv/bin/python server.py