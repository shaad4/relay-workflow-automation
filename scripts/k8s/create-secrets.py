#!/usr/bin/env python3
"""Prepare fresh full-K3s secrets OFFLINE; never applies or prints credentials.

Input: a private directory containing reviewed existing application Secret YAMLs.
Output must not exist and must be outside the checkout. Never rerun to rotate an
initialized database: POSTGRES_PASSWORD only takes effect on an empty PGDATA.
"""

import argparse
import base64
import os
import secrets
import uuid
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--application-secrets", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
output = args.output.resolve()
if output.is_relative_to(root) or output.exists():
    raise SystemExit("Output must be a NEW private directory outside the repository")
objects = {}
for path in args.application_secrets.glob("*.yaml"):
    for obj in yaml.safe_load_all(path.read_text()):
        if obj and obj.get("kind") == "Secret":
            values = {k: base64.b64decode(v).decode() for k, v in obj.get("data", {}).items()}
            values.update(obj.get("stringData", {}))
            objects[obj["metadata"]["name"]] = values
required = {
    "relay-jwt": ["JWT_SECRET_KEY"],
    "relay-action-service": ["ACTION_CREDENTIAL_ENCRYPTION_KEY"],
    "relay-execution-service": ["AI_CREDENTIAL_ENCRYPTION_KEY"],
}
for name, keys in required.items():
    for key in keys:
        value = objects.get(name, {}).get(key, "")
        if not value or "REPLACE" in value:
            raise SystemExit(f"Missing reviewed credential: {name}/{key}")
for name, values in objects.items():
    for key, value in values.items():
        if key not in {"DATABASE_URL", "CELERY_BROKER_URL"} and "REPLACE" in str(value):
            raise SystemExit(f"Replace or clear optional placeholder: {name}/{key}")
# Validate all input contracts before creating output.
for service in ["auth", "workflow", "integration", "action", "execution", "rag"]:
    if "relay-" + service + "-service" not in objects:
        raise SystemExit("Supply all six reviewed application Secrets")
os.umask(0o077)
output.mkdir(parents=True, mode=0o700)


def save(name, values):
    obj = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": name, "namespace": "relay"},
        "type": "Opaque",
        "stringData": values,
    }
    (output / (name + ".yaml")).write_text(yaml.safe_dump(obj, sort_keys=False))


for service in ["auth", "workflow", "integration", "action", "execution", "rag"]:
    password = secrets.token_hex(24)  # URL-safe; never reuse Compose DB passwords.
    user = service + "_user"
    database = service + "_db"
    save(
        service + "-postgres",
        {"POSTGRES_USER": user, "POSTGRES_DB": database, "POSTGRES_PASSWORD": password},
    )
    values = objects["relay-" + service + "-service"]
    values["DATABASE_URL"] = (
        f"postgresql+asyncpg://{user}:{password}@{service}-postgres:5432/{database}"
    )
    if service in {"integration", "rag"}:
        values["CELERY_BROKER_URL"] = "redis://redis:6379/" + (
            "1" if service == "integration" else "0"
        )
    save("relay-" + service + "-service", values)
save("relay-jwt", objects["relay-jwt"])
save(
    "kafka-kraft", {"CLUSTER_ID": base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip("=")}
)
print("Prepared private Secret files. Review and back them up securely; no cluster was contacted.")
