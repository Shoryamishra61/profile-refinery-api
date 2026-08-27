from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from .canonicalizer import canonicalize_profile_url
from .config import Settings
from .runtime import Runtime

EXPECTED = Path("tests/fixtures/expected/synthetic-profile.expected.json")


def _semantic_profile(response: dict[str, Any]) -> dict[str, Any]:
    profile = response["profile"]
    return {
        "identity": profile["identity"]["value"],
        "name": profile["name"]["value"],
        "headline": profile["headline"]["value"],
        "location": profile["location"]["value"],
        "about": profile["about"]["value"],
        "experience": [
            {key: item.get(key) for key in ("id", "title", "company_name")}
            for item in profile["experience"]["value"]
        ],
        "education": [
            {key: item.get(key) for key in ("id", "school_name", "degree_name", "field_of_study")}
            for item in profile["education"]["value"]
        ],
        "skills": [item["name"] for item in profile["skills"]["value"]],
        "certifications": [item["name"] for item in profile["certifications"]["value"]],
        "languages": [item["name"] for item in profile["languages"]["value"]],
        "profile_image_url": profile["profile_image"]["value"]["url"],
    }


def _load_expected() -> dict[str, Any]:
    if not EXPECTED.is_file():
        raise FileNotFoundError(f"independent expected output is required: {EXPECTED}")
    value = json.loads(EXPECTED.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("independent expected output must be an object")
    return value


async def run_fixture_benchmark(iterations: int = 10) -> dict[str, Any]:
    expected = _load_expected()
    settings = Settings(app_api_keys=[SecretStr("fixture-benchmark-only")])
    runtime = Runtime(settings)
    latencies = []
    try:
        response = None
        for index in range(iterations):
            started = time.perf_counter()
            response = await runtime.orchestrator.fetch(
                canonicalize_profile_url("https://www.linkedin.com/in/synthetic-profile"),
                f"benchmark-{index}",
                observed_at=datetime(2026, 8, 27, tzinfo=UTC),
            )
            latencies.append((time.perf_counter() - started) * 1000)
        assert response is not None
        actual = response.model_dump(mode="json")
    finally:
        await runtime.aclose()

    expected_profile = expected["profile"]
    actual_profile = _semantic_profile(actual)
    primitive_keys = ("name", "headline", "location", "about")
    primitive_correct = sum(actual_profile[key] == expected_profile[key] for key in primitive_keys)
    nested_keys = ("experience", "education", "skills", "certifications", "languages")
    expected_entries = sum(len(expected_profile[key]) for key in nested_keys)
    matched_entries = sum(
        len([entry for entry in actual_profile[key] if entry in expected_profile[key]])
        for key in nested_keys
    )
    status_correct = sum(
        actual["profile"][key]["status"] == status
        for key, status in expected["expected_status"].items()
    )
    provenance_fields = list(actual["profile"].values())
    provenance_correct = sum(
        bool(item["provenance"]["source_operation"] and item["provenance"]["parser_version"])
        for item in provenance_fields
    )
    ordered = sorted(latencies)
    p95_index = max(0, min(len(ordered) - 1, round(0.95 * len(ordered) + 0.5) - 1))
    return {
        "evidence_class": "FIXTURE_VERIFIED",
        "fixture_cases": 1,
        "iterations": iterations,
        "primitive_correct": primitive_correct,
        "primitive_n": len(primitive_keys),
        "primitive_accuracy": primitive_correct / len(primitive_keys),
        "nested_entries_correct": matched_entries,
        "nested_entries_n": expected_entries,
        "nested_entry_recall": matched_entries / expected_entries,
        "status_correct": status_correct,
        "status_n": len(expected["expected_status"]),
        "status_accuracy": status_correct / len(expected["expected_status"]),
        "provenance_correct": provenance_correct,
        "provenance_n": len(provenance_fields),
        "provenance_coverage": provenance_correct / len(provenance_fields),
        "expected_upstream_calls": expected["expected_upstream_calls"],
        "actual_fixture_operations": actual["meta"]["upstream_calls"],
        "fixture_pipeline_latency_ms": {
            "mean": statistics.fmean(latencies),
            "p50": statistics.median(latencies),
            "p95": ordered[p95_index],
        },
        "live_extraction_claim": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the independent fixture benchmark")
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be at least 1")
    result = asyncio.run(run_fixture_benchmark(args.iterations))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Fixture benchmark only; no live extraction claim")
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
