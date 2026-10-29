#!/usr/bin/env python3
"""Filter rendered manifests without contacting a cluster or reading credentials."""

import sys

import yaml

mode, path, *extra = sys.argv[1:]
with open(path) as stream:
    objects = [obj for obj in yaml.safe_load_all(stream) if obj]
if mode == "names":
    print("\n".join(o["metadata"]["name"] for o in objects if o["kind"] == "Job"))
else:
    if mode == "infrastructure":
        objects = [o for o in objects if o["kind"] not in {"Deployment", "Ingress"}]
    elif mode == "job":
        objects = [o for o in objects if o["kind"] == "Job" and o["metadata"]["name"] == extra[0]]
    else:
        raise SystemExit("Unknown render mode")
    print(yaml.safe_dump_all(objects, sort_keys=False))
