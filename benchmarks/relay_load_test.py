#!/usr/bin/env python3
"""Relay manual-trigger benchmark. Uses HTTPX and psycopg (psycopg 3)."""
import argparse
import asyncio
import csv
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
from psycopg.rows import dict_row

TERMINAL = {"completed", "failed", "cancelled", "canceled"}


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p / 100
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (rank - lo)


def query_rows(dsn, workflow_id, run_id):
    with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, status, created_at, started_at, completed_at,
                       trigger_data->>'request_number' AS request_number
                FROM executions
                WHERE workflow_id = %s::uuid
                  AND trigger_type = 'manual'
                  AND trigger_data->>'benchmark_run_id' = %s
                ORDER BY created_at, id
            """, (workflow_id, run_id))
            return cur.fetchall()


def iso(dt):
    return dt.isoformat() if dt else ""


async def main(args):
    run_id = f"baseline-c{args.concurrency_label}-n{args.count}-{uuid4().hex[:10]}"
    url = f"{args.base_url.rstrip('/')}/workflows/{args.workflow_id}/run"
    headers = {"Authorization": f"Bearer {args.token}"}
    semaphore = asyncio.Semaphore(args.submit_concurrency)
    submissions = []
    start_wall = datetime.now(timezone.utc)
    start_mono = time.monotonic()

    async with httpx.AsyncClient(timeout=20.0) as client:
        async def submit(i):
            async with semaphore:
                sent_at = datetime.now(timezone.utc)
                try:
                    response = await client.post(url, headers=headers, json={"input": {
                        "benchmark_run_id": run_id,
                        "request_number": i,
                    }})
                    try:
                        body = response.json()
                    except ValueError:
                        body = {}
                    return {"number": i, "sent_at": sent_at, "status": response.status_code,
                            "event_id": body.get("event_id", ""), "error": "" if response.status_code == 202 else str(body)[:200]}
                except httpx.HTTPError as exc:
                    return {"number": i, "sent_at": sent_at, "status": 0,
                            "event_id": "", "error": type(exc).__name__}

        submissions = await asyncio.gather(*(submit(i) for i in range(1, args.count + 1)))

    accepted = [x for x in submissions if x["status"] == 202]
    print(f"Run: {run_id}\nSubmitted: {args.count}; accepted: {len(accepted)}; rejected: {args.count-len(accepted)}", flush=True)
    if not accepted:
        print("No accepted requests. Check token, URL, and workflow publication.")
        return 1

    deadline = time.monotonic() + args.drain_timeout
    rows = []
    while True:
        try:
            rows = await asyncio.to_thread(query_rows, args.db_dsn, args.workflow_id, run_id)
        except Exception as exc:
            print(f"Database query failed: {type(exc).__name__}: {exc}")
            return 2
        terminal_count = sum(r["status"] in TERMINAL for r in rows)
        print(f"Found {len(rows)}/{len(accepted)} executions; terminal {terminal_count}/{len(accepted)}", flush=True)
        if len(rows) >= len(accepted) and terminal_count >= len(accepted):
            break
        if time.monotonic() >= deadline:
            print("Drain timeout: report is incomplete.")
            break
        await asyncio.sleep(args.poll_interval)

    finish_wall = datetime.now(timezone.utc)
    elapsed = time.monotonic() - start_mono
    by_number = {str(s["number"]): s for s in submissions}
    latencies, queue_delays, service_times = [], [], []
    output = []
    for row in rows:
        submission = by_number.get(str(row["request_number"]))
        latency = ((row["completed_at"] - submission["sent_at"]).total_seconds()
                   if submission and row["completed_at"] else None)
        queue = ((row["started_at"] - row["created_at"]).total_seconds()
                 if row["started_at"] and row["created_at"] else None)
        service = ((row["completed_at"] - row["started_at"]).total_seconds()
                   if row["completed_at"] and row["started_at"] else None)
        if latency is not None: latencies.append(latency)
        if queue is not None: queue_delays.append(queue)
        if service is not None: service_times.append(service)
        output.append({"run_id": run_id, "request_number": row["request_number"],
                       "execution_id": str(row["id"]), "status": row["status"],
                       "sent_at": iso(submission["sent_at"]) if submission else "",
                       "created_at": iso(row["created_at"]), "started_at": iso(row["started_at"]),
                       "completed_at": iso(row["completed_at"]), "latency_seconds": latency,
                       "queue_delay_seconds": queue, "execution_duration_seconds": service})

    completed = sum(r["status"] == "completed" for r in rows)
    failed = sum(r["status"] == "failed" for r in rows)
    summary = {
        "run_id": run_id, "workflow_id": args.workflow_id, "concurrency_label": args.concurrency_label,
        "requested": args.count, "accepted": len(accepted), "rejected": args.count - len(accepted),
        "observed": len(rows), "completed": completed, "failed": failed,
        "duration_seconds": round(elapsed, 3),
        "successful_workflows_per_minute": round(completed * 60 / elapsed, 2),
        "terminal_workflows_per_minute": round((completed + failed) * 60 / elapsed, 2),
        "average_latency_seconds": round(statistics.mean(latencies), 3) if latencies else None,
        "p95_latency_seconds": round(percentile(latencies, 95), 3) if latencies else None,
        "average_queue_delay_seconds": round(statistics.mean(queue_delays), 3) if queue_delays else None,
        "p95_queue_delay_seconds": round(percentile(queue_delays, 95), 3) if queue_delays else None,
        "average_execution_duration_seconds": round(statistics.mean(service_times), 3) if service_times else None,
        "failure_rate_pct": round(100 * failed / len(rows), 2) if rows else None,
        "start_time_utc": iso(start_wall), "end_time_utc": iso(finish_wall),
    }
    dest = Path(args.output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{run_id}.json").write_text(json.dumps(summary, indent=2))
    if output:
        with (dest / f"{run_id}.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=output[0].keys())
            writer.writeheader()
            writer.writerows(output)
    print(json.dumps(summary, indent=2))
    print(f"Saved to {dest}/{run_id}.json and .csv")
    return 0 if len(rows) == len(accepted) and completed + failed == len(accepted) else 3


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-id", default="91d81817-6193-40e5-9cf1-b9213572cfe2")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--token", default=os.getenv("RELAY_BENCH_TOKEN"), required=False)
    parser.add_argument("--db-dsn", default=os.getenv("RELAY_BENCH_DB_DSN"))
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--submit-concurrency", type=int, default=5)
    parser.add_argument("--concurrency-label", default="5")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--drain-timeout", type=float, default=180.0)
    parser.add_argument("--output-dir", default="benchmarks/results")
    args = parser.parse_args()
    if not args.token or not args.db_dsn:
        parser.error("Set RELAY_BENCH_TOKEN and RELAY_BENCH_DB_DSN environment variables")
    if args.count < 1 or args.submit_concurrency < 1:
        parser.error("count and submit-concurrency must be positive")
    raise SystemExit(asyncio.run(main(args)))
