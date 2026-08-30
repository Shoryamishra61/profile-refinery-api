"""Paced ~30-profile production acceptance run against the deployed API.

Submits the batch, polls until terminal (breaker-aware: the server pauses
itself when challenged), then reports the measured capacity metrics required
by the architecture workload model:

  submitted / deduplicated / jobs / upstream requests / p50+p95 extraction
  latency / success+failure counts / challenge+breaker events / total time.

Usage:
  PROFILE_REFINERY_API_KEY=<key> python scripts/acceptance_run.py [--base URL] [--out file]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from datetime import UTC, datetime

import httpx

PROFILES = [
    "williamhgates", "satyanadella", "reidhoffman", "jeffweiner01", "ariannahuff",
    "marissamayer", "warrenbuffett", "richardbranson", "barackobama", "elonmusk",
    "jeffbezos", "tim_cook", "sherylsandberg", "pmarca", "jack", "evwilliams",
    "drewhouston", "tobi", "bchesky", "stpeterman", "guykawasaki", "lopatsky",
    "ericries", "sama", "naval", "adamdraper", "hcalcote", "kmin", "annimani",
    "productdestiny",
]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="https://profile-refinery-api.vercel.app")
    parser.add_argument("--out", default="C:/tmp/acceptance_result.json")
    args = parser.parse_args()
    key = os.environ["PROFILE_REFINERY_API_KEY"]
    headers = {"X-API-Key": key}
    text = "\n".join(
        f"{i + 1}. https://www.linkedin.com/in/{slug}/" for i, slug in enumerate(PROFILES)
    )
    # Two duplicates to exercise deduplication: 32 occurrences -> 30 unique.
    text += "\n\nhttps://www.linkedin.com/in/williamhgates/\nlinkedin.com/in/satyanadella"

    started = time.monotonic()
    async with httpx.AsyncClient(timeout=90) as client:
        before = (await client.get(f"{args.base}/v1/capability", headers=headers)).json()
        created = await client.post(
            f"{args.base}/v1/batches", params={"text": text}, headers=headers
        )
        assert created.status_code == 202, created.text
        batch_id = created.json()["batch_id"]
        print(f"batch {batch_id} created", flush=True)

        final = {}
        polls = 0
        while True:
            polls += 1
            response = await client.get(
                f"{args.base}/v1/batches/{batch_id}", params={"wait_seconds": 25}, headers=headers
            )
            final = response.json()
            stats = final["statistics"]
            print(
                f"poll {polls}: status={final['status']} ok={stats['succeeded']} "
                f"failed={stats['failed']} retry={stats['retry_wait']} "
                f"blocked={stats['blocked_upstream']} pending={stats['pending']}",
                flush=True,
            )
            if stats["pending"] == 0 and stats["retry_wait"] == 0 and stats["blocked_upstream"] == 0:
                break
            if time.monotonic() - started > 40 * 60:
                print("time budget exceeded; reporting current state", flush=True)
                break

        profiles = (
            await client.get(
                f"{args.base}/v1/batches/{batch_id}/profiles", headers=headers
            )
        ).json()
        after = (await client.get(f"{args.base}/v1/capability", headers=headers)).json()

    elapsed = time.monotonic() - started
    latencies = [
        attempt["latency_ms"]
        for job in profiles["profiles"]
        for attempt in job["attempt_history"]
        if attempt["outcome"] == "succeeded"
    ]
    report = {
        "batch_id": batch_id,
        "completed_at": datetime.now(UTC).isoformat(),
        "submitted_occurrences": len(PROFILES) + 2,
        "deduplicated_unique": final["statistics"]["unique_profiles"],
        "duplicates_removed": final["statistics"]["duplicates_removed"],
        "succeeded": final["statistics"]["succeeded"],
        "failed": final["statistics"]["failed"],
        "blocked_at_end": final["statistics"]["blocked_upstream"],
        "retry_wait_at_end": final["statistics"]["retry_wait"],
        "polls": polls,
        "total_wall_clock_seconds": round(elapsed, 1),
        "upstream_requests_total": {
            "before": before["extraction_capability"]["governor"]["operations_total"],
            "after": after["extraction_capability"]["governor"]["operations_total"],
        },
        "breaker": after["extraction_capability"]["governor"]["breaker"],
        "extraction_latency_ms": {
            "count": len(latencies),
            "p50": round(statistics.median(latencies), 1) if latencies else None,
            "p95": (
                round(sorted(latencies)[int(0.95 * len(latencies)) - 1], 1)
                if len(latencies) >= 20
                else (max(latencies) if latencies else None)
            ),
        },
        "profiles": [
            {
                "slug": job["canonical_url"].rsplit("/", 1)[-1],
                "state": job["state"],
                "error": job["error_code"],
                "name": (
                    (job.get("response", {}).get("profile", {}).get("name", {}) or {}).get("value")
                    if job.get("response")
                    else None
                ),
            }
            for job in profiles["profiles"]
        ],
    }
    print(json.dumps({k: v for k, v in report.items() if k != "profiles"}, indent=1), flush=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(f"written: {args.out}", flush=True)


asyncio.run(main())
