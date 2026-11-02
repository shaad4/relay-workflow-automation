#!/usr/bin/env python3
"""Negative manifest checks plus offline credential-pairing/permissions tests."""

import copy
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from check_full_k3s import check

ROOT = Path(__file__).resolve().parents[1]


class FullK3sTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            ["kubectl", "kustomize", str(ROOT / "deploy/kubernetes/overlays/full-k3s")],
            check=True,
            capture_output=True,
            text=True,
        )
        cls.objects = list(yaml.safe_load_all(result.stdout))

    def mutated(self, kind, name):
        objects = copy.deepcopy(self.objects)
        return objects, next(
            o for o in objects if o["kind"] == kind and o["metadata"]["name"] == name
        )

    def test_baseline(self):
        check(self.objects)

    def test_public_database_rejected(self):
        objects, service = self.mutated("Service", "auth-postgres")
        service["spec"]["type"] = "LoadBalancer"
        with self.assertRaises(AssertionError):
            check(objects)

    def test_duplicate_beat_rejected(self):
        objects, deployment = self.mutated("Deployment", "integration-celery-beat")
        deployment["spec"]["replicas"] = 2
        with self.assertRaises(AssertionError):
            check(objects)

    def test_evicting_broker_rejected(self):
        objects, redis = self.mutated("StatefulSet", "redis")
        args = redis["spec"]["template"]["spec"]["containers"][0]["args"]
        args[args.index("noeviction")] = "allkeys-lru"
        with self.assertRaises(AssertionError):
            check(objects)

    def test_missing_pvc_class_rejected(self):
        objects, postgres = self.mutated("StatefulSet", "auth-postgres")
        postgres["spec"]["volumeClaimTemplates"][0]["spec"]["storageClassName"] = "other"
        with self.assertRaises(AssertionError):
            check(objects)

    def test_unknown_app_secret_rejected(self):
        objects, deployment = self.mutated("Deployment", "auth-service")
        deployment["spec"]["template"]["spec"]["containers"][0]["envFrom"].append(
            {"secretRef": {"name": "unknown"}}
        )
        with self.assertRaises(AssertionError):
            check(objects)

    def test_secret_pairing_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / "input"
            source.mkdir()
            output = folder / "output"
            values = {
                "relay-jwt": {"JWT_SECRET_KEY": "synthetic-test-key"},
                "relay-action-service": {"ACTION_CREDENTIAL_ENCRYPTION_KEY": "synthetic-action"},
                "relay-execution-service": {"AI_CREDENTIAL_ENCRYPTION_KEY": "synthetic-ai"},
            }
            for service in ["auth", "workflow", "integration", "action", "execution", "rag"]:
                values.setdefault("relay-" + service + "-service", {})
            for name, data in values.items():
                (source / (name + ".yaml")).write_text(
                    yaml.safe_dump(
                        {"kind": "Secret", "metadata": {"name": name}, "stringData": data}
                    )
                )
            command = [
                "python3",
                str(ROOT / "scripts/k8s/create-secrets.py"),
                "--application-secrets",
                str(source),
                "--output",
                str(output),
            ]
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertNotIn("synthetic", result.stdout)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
            passwords = set()
            for service in ["auth", "workflow", "integration", "action", "execution", "rag"]:
                db = yaml.safe_load((output / (service + "-postgres.yaml")).read_text())[
                    "stringData"
                ]
                app = yaml.safe_load((output / ("relay-" + service + "-service.yaml")).read_text())[
                    "stringData"
                ]
                self.assertIn(db["POSTGRES_PASSWORD"], app["DATABASE_URL"])
                self.assertIn(
                    "@" + service + "-postgres:5432/" + service + "_db", app["DATABASE_URL"]
                )
                passwords.add(db["POSTGRES_PASSWORD"])
                if service in ["rag", "integration"]:
                    self.assertEqual(
                        app["CELERY_BROKER_URL"],
                        "redis://redis:6379/" + ("0" if service == "rag" else "1"),
                    )
            self.assertEqual(len(passwords), 6)
            self.assertTrue(all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in output.iterdir()))
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})


if __name__ == "__main__":
    unittest.main()
