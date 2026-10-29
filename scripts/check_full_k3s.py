#!/usr/bin/env python3
"""Offline full-K3s contract checks; accepts a rendered overlay, never live data."""

import sys
from pathlib import Path

import yaml


def check(objects):
    by_kind = {}
    for obj in objects:
        by_kind.setdefault(obj["kind"], {})[obj["metadata"]["name"]] = obj
    sts = by_kind["StatefulSet"]
    databases = {
        s + "-postgres" for s in ["auth", "workflow", "integration", "action", "execution", "rag"]
    }
    assert set(sts) == databases | {"kafka", "redis"}
    assert "Job" not in by_kind and "Secret" not in by_kind
    assert "relay-private-infrastructure" not in by_kind["NetworkPolicy"]
    assert {
        "default-deny",
        "relay-internal",
        "relay-cluster-infrastructure",
        "relay-external-providers",
        "relay-ingress-controller",
    } <= set(by_kind["NetworkPolicy"])
    for name, obj in sts.items():
        spec = obj["spec"]
        pod = spec["template"]["spec"]
        c = pod["containers"][0]
        assert spec["replicas"] == 1 and pod["automountServiceAccountToken"] is False
        assert spec["serviceName"] in by_kind["Service"]
        assert c["imagePullPolicy"] == "IfNotPresent"
        assert c["resources"]["requests"] and c["resources"]["limits"]
        for resource in ["cpu", "memory"]:
            assert resource in c["resources"]["requests"] and resource in c["resources"]["limits"]
        assert set(spec["selector"]["matchLabels"].items()) <= set(
            spec["template"]["metadata"]["labels"].items()
        )
        assert c["startupProbe"] and c["readinessProbe"]
        pvc = spec["volumeClaimTemplates"][0]["spec"]
        assert pvc["storageClassName"] == "local-path" and pvc["accessModes"] == ["ReadWriteOnce"]
        assert pvc["resources"]["requests"]["storage"]
        assert by_kind["Service"][name]["spec"]["selector"] == spec["selector"]["matchLabels"]
        if name in databases:
            assert c["envFrom"][0]["secretRef"]["name"] == name
            assert c["image"] == (
                "pgvector/pgvector:pg16" if name == "rag-postgres" else "postgres:16"
            )
            assert "alembic" not in str(c) and "DROP " not in str(c)
    kafka = sts["kafka"]["spec"]["template"]["spec"]["containers"][0]
    assert kafka["image"] == "apache/kafka:4.0.1"
    command = kafka["command"][-1]
    assert (
        "meta.properties" in command
        and "Refusing to format" in command
        and "cluster.id=$CLUSTER_ID" in command
    )
    props = by_kind["ConfigMap"]["kafka-config"]["data"]["server.properties"]
    assert "advertised.listeners=PLAINTEXT://kafka-0.kafka.relay.svc.cluster.local:9092" in props
    for line in [
        "process.roles=broker,controller",
        "node.id=1",
        "log.retention.hours=24",
        "offsets.topic.replication.factor=1",
        "auto.create.topics.enable=false",
    ]:
        assert line in props
    assert "zookeeper" not in props.lower()
    redis = sts["redis"]["spec"]["template"]["spec"]["containers"][0]
    assert all(
        s in redis["args"]
        for s in ["noeviction", "everysec", "yes", "192mb", "--protected-mode", "no"]
    )
    assert redis["livenessProbe"]
    for obj in by_kind["Service"].values():
        assert obj["spec"].get("type", "ClusterIP") == "ClusterIP"
        assert not obj["spec"].get("externalIPs")
    ingress = by_kind["Ingress"]["relay"]
    assert ingress["spec"]["ingressClassName"] == "traefik" and ingress["spec"]["tls"]
    assert all(
        p["backend"]["service"]["name"] == "frontend"
        for r in ingress["spec"]["rules"]
        for p in r["http"]["paths"]
    )
    deployments = by_kind["Deployment"]
    assert len(deployments) == 11
    for name in ["execution-service", "integration-celery-beat"]:
        assert deployments[name]["spec"]["replicas"] == 1
        assert deployments[name]["spec"]["strategy"]["type"] == "Recreate"
    # Every explicit app secret reference must be covered by the documented secret contract.
    allowed = {"relay-jwt"} | {
        "relay-" + s + "-service"
        for s in ["auth", "workflow", "integration", "action", "execution", "rag"]
    }
    for deployment in deployments.values():
        for c in deployment["spec"]["template"]["spec"]["containers"]:
            for env in c.get("env", []):
                ref = env.get("valueFrom", {}).get("secretKeyRef")
                if ref:
                    assert ref["name"] in allowed
            for ref in c.get("envFrom", []):
                if "secretRef" in ref:
                    assert ref["secretRef"]["name"] in allowed
    config = by_kind["ConfigMap"]["relay-config"]["data"]
    assert config["KAFKA_BOOTSTRAP_SERVERS"] == "kafka:9092"
    for service in ["auth", "workflow", "integration", "action", "execution", "rag"]:
        assert config[service.upper() + "_SERVICE_URL"] == "http://" + service + "-service:8000"
    assert config["API_GATEWAY_URL"] == "http://api-gateway:8000"


if __name__ == "__main__":
    check([o for o in yaml.safe_load_all(Path(sys.argv[1]).read_text()) if o])
    print("Full-K3s offline infrastructure contracts passed.")
