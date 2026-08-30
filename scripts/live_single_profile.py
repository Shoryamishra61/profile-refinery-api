"""Run one governed direct-HTTP profile extraction with secret-safe output."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from pydantic import SecretStr

from profile_refinery_api.canonicalizer import canonicalize_profile_url
from profile_refinery_api.config import Settings
from profile_refinery_api.runtime import Runtime


async def run(env_file: Path, profile_url: str) -> None:
    settings = Settings(
        _env_file=env_file,
        app_api_keys=[SecretStr("local-live-smoke")],
        app_upstream_retries=0,
    )
    runtime = Runtime(settings)
    try:
        result = await runtime.orchestrator.fetch(
            canonicalize_profile_url(profile_url), "local-live-smoke"
        )
    finally:
        await runtime.aclose()
    profile = result.profile.model_dump(mode="json")
    summary = {
        "schema_version": result.schema_version,
        "partial": result.partial,
        "retrieval": result.retrieval.model_dump(mode="json"),
        "operations_attempted": result.meta.operations_attempted,
        "operations_succeeded": result.meta.operations_succeeded,
        "coverage": result.meta.coverage,
        "warnings": result.meta.warnings,
        "profile": {
            name: profile[name]["value"]
            for name in (
                "name",
                "headline",
                "location",
                "about",
                "profile_image",
                "experience",
                "education",
                "skills",
                "certifications",
                "languages",
            )
        },
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.env_file, args.url))


if __name__ == "__main__":
    main()
