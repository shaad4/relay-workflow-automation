#!/usr/bin/env python3
"""Offline deployment invariants; never reads local .env or contacts a service."""

import argparse
import ast
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVICES = (
    "api-gateway",
    "auth-service",
    "workflow-service",
    "integration-service",
    "action-service",
    "execution-service",
    "rag-service",
)
MIGRATING = set(SERVICES) - {"api-gateway"}
WORKERS = {"integration-celery-worker", "integration-celery-beat", "rag-celery-worker"}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def env_keys(path):
    return {
        line.split("=", 1)[0].strip()
        for line in path.read_text().splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }


def check_sources():
    for service in SERVICES:
        folder = ROOT / "service" / service
        dockerfile = (folder / "Dockerfile").read_text()
        check("USER " in dockerfile, f"{service}: explicit non-root USER required")
        check("alembic upgrade" not in dockerfile, f"{service}: startup migration forbidden")
        check((folder / ".dockerignore").is_file(), f"{service}: missing build exclusions")
        check(".env" in (folder / ".dockerignore").read_text(), f"{service}: exclude .env")
        keys = env_keys(folder / ".env.example")
        check("RELAY_ENV" in keys, f"{service}: missing RELAY_ENV template")
        if service in MIGRATING:
            check("DATABASE_URL" in keys, f"{service}: missing DATABASE_URL template")
        for requirement in (folder / "requirements.txt").read_text().splitlines():
            line = requirement.strip()
            if line and not line.startswith("#"):
                check("==" in line, f"{service}: unlocked dependency")
        check("/ready" in (folder / "app/main.py").read_text(), f"{service}: no readiness")
    for service in SERVICES:
        for path in (ROOT / "service" / service / "app").rglob("*.py"):
            if "generated" in path.parts:
                continue
            ast.parse(path.read_text(), filename=str(path))
    frontend = (ROOT / "frontend/Dockerfile").read_text()
    check("USER " in frontend, "frontend: explicit non-root USER required")
    check(
        not any(
            "NEXT_PUBLIC_" in line
            for line in frontend.splitlines()
            if not line.lstrip().startswith("#")
        ),
        "frontend image must not bake public deployment URL",
    )
    check("iptables" not in (ROOT / "scripts/dev-up.sh").read_text(), "no host firewall edits")


def check_kubernetes(path):
    objects = [obj for obj in yaml.safe_load_all(path.read_text()) if obj]
    check(not any(obj["kind"] == "Secret" for obj in objects), "do not deploy example secrets")
    check(
        not any(obj["kind"] in {"RoleBinding", "ClusterRoleBinding"} for obj in objects),
        "applications must not receive Kubernetes API permissions",
    )
    deployments = {o["metadata"]["name"]: o for o in objects if o["kind"] == "Deployment"}
    jobs = [o for o in objects if o["kind"] == "Job"]
    if deployments:
        check(
            set(deployments) == set(SERVICES) | WORKERS | {"frontend"},
            "application inventory mismatch",
        )
        check(not jobs, "migration Jobs must not be included in ordinary app rollout")
        for name, deployment in deployments.items():
            check(deployment["spec"]["replicas"] in {0, 1}, f"{name}: unsafe default replicas")
            pod = deployment["spec"]["template"]["spec"]
            check(pod.get("automountServiceAccountToken") is False, f"{name}: API token mounted")
            check(pod["securityContext"].get("runAsNonRoot") is True, f"{name}: root pod")
            if name in {"execution-service", "integration-celery-beat"}:
                check(
                    deployment["spec"]["strategy"]["type"] == "Recreate", f"{name}: overlap unsafe"
                )
            if name == "execution-service":
                check(
                    pod["terminationGracePeriodSeconds"] >= 120, "execution drain window shortened"
                )
            for container in pod["containers"]:
                check(
                    container["resources"].get("requests") and container["resources"].get("limits"),
                    f"{name}: resource budget missing",
                )
                check(
                    container["securityContext"].get("allowPrivilegeEscalation") is False,
                    f"{name}: privilege escalation allowed",
                )
                if name not in WORKERS:
                    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
                        check(probe in container, f"{name}: {probe} missing")
        policies = [o for o in objects if o["kind"] == "NetworkPolicy"]
        check(
            any(o["metadata"]["name"] == "default-deny" for o in policies), "default deny missing"
        )
        for obj in objects:
            if obj["kind"] == "Service":
                check(
                    obj["spec"].get("type", "ClusterIP") == "ClusterIP", "public service exposure"
                )
    if jobs:
        check(len(jobs) == 6, "exactly six independent migration Jobs required")
        for job in jobs:
            spec = job["spec"]
            check(spec.get("backoffLimit") == 0, "migrations must not blindly auto-retry")
            command = spec["template"]["spec"]["containers"][0]["command"]
            check(command == ["alembic", "upgrade", "head"], "unexpected migration command")


def check_published_networks(path):
    model = json.loads(path.read_text())
    networks = model.get("networks", {})
    for name, service in model["services"].items():
        if service.get("ports"):
            check(
                any(
                    not networks.get(network, {}).get("internal", False)
                    for network in service.get("networks", {"default": {}})
                ),
                f"{name}: published ports need a non-internal network gateway",
            )
    return model


def check_compose(path):
    model = check_published_networks(path)
    services = model["services"]
    for name in SERVICES:
        check(name in services, f"Compose missing {name}")
        check(services[name].get("healthcheck"), f"Compose {name}: missing healthcheck")
    for name, service in services.items():
        for port in service.get("ports", []):
            check(
                port.get("host_ip") in {"127.0.0.1", "::1"}, f"{name}: non-loopback production port"
            )
    for name in (
        *[service.replace("-service", "-postgres") for service in MIGRATING],
        "kafka",
        "rag-redis",
    ):
        check(not services[name].get("ports"), f"{name}: production stateful port exposed")
        check(
            all(
                model["networks"][network].get("internal") for network in services[name]["networks"]
            ),
            f"{name}: production stateful network must remain internal",
        )
    check(
        services["integration-celery-beat"].get("deploy", {}).get("replicas", 1) == 1,
        "Compose Beat must be singleton",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubernetes", type=Path, action="append", default=[])
    parser.add_argument("--production-compose", type=Path)
    parser.add_argument("--compose", type=Path, action="append", default=[])
    args = parser.parse_args()
    check_sources()
    for path in args.kubernetes:
        check_kubernetes(path)
    for path in args.compose:
        check_published_networks(path)
    if args.production_compose:
        check_compose(args.production_compose)
    print(
        "Deployment source and supplied render invariants passed (no live infrastructure checked)."
    )


if __name__ == "__main__":
    main()
