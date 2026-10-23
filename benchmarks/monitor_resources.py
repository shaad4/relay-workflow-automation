
import csv
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


CONTAINERS = [
    "relay-execution-service",
    "relay-action-service",
    "relay-execution-postgres",
    "relay-kafka",
    "relay-load-target",
]

output = Path(sys.argv[1])
output.parent.mkdir(parents=True, exist_ok=True)

with output.open("w", newline="") as file:
    writer = csv.writer(file)

    writer.writerow([
        "timestamp",
        "container",
        "cpu_percent",
        "memory_usage",
        "memory_percent",
    ])

    try:
        while True:
            result = subprocess.run(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}",
                    *CONTAINERS,
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            timestamp = datetime.now(
                timezone.utc
            ).isoformat()

            for line in result.stdout.splitlines():
                name, cpu, memory, mem_pct = line.split(",", 3)

                writer.writerow([
                    timestamp,
                    name,
                    cpu.strip("%"),
                    memory.split("/")[0].strip(),
                    mem_pct.strip("%"),
                ])

            file.flush()
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"Saved resource metrics to {output}")
