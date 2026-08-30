"""Differential acceptance test against the deployed production API.

Requests three unrelated real profiles plus an A-repeat, validates the public
contract, profile-specific differences, and absence of fixture sentinels.
Paced: one request at a time with gaps, respecting upstream safety.
"""

import asyncio
import json
import os
import sys

import httpx

BASE = os.environ.get("PROFILE_REFINERY_BASE", "https://profile-refinery-api.vercel.app")
KEY = os.environ["PROFILE_REFINERY_API_KEY"]
SLUGS = ["williamhgates", "satyanadella", "reidhoffman"]
SENTINELS = ("SYNTHETIC-001", "Synthetic Systems Ltd", "Example Research Lab")
GAP_SECONDS = 20


async def fetch(client: httpx.AsyncClient, slug: str) -> tuple[int, dict]:
    r = await client.get(
        f"{BASE}/v1/profiles",
        params={"url": f"https://www.linkedin.com/in/{slug}/"},
        headers={"X-API-Key": KEY},
    )
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:200]}
    return r.status_code, body


def value(body: dict, field: str):
    return (body.get("profile", {}).get(field) or {}).get("value")


async def main() -> None:
    results: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=60) as client:
        for index, slug in enumerate(list(SLUGS) + [SLUGS[0]]):
            label = "A-repeat" if index == len(SLUGS) else slug
            status, body = await fetch(client, slug)
            code = body.get("code")
            print(f"{label}: HTTP {status} code={code}", flush=True)
            if status == 200:
                name = value(body, "name")
                headline = value(body, "headline")
                experience = value(body, "experience") or []
                education = value(body, "education") or []
                skills = value(body, "skills") or []
                text = json.dumps(body)
                assert body["retrieval"]["mode"] == "live", "mode must be live"
                assert body["retrieval"]["fixture"] is False, "fixture must be false"
                assert body["retrieval"]["source"] == "linkedin"
                assert slug in body["canonical_url"], f"canonical_url must match {slug}"
                for sentinel in SENTINELS:
                    assert sentinel not in text, f"sentinel {sentinel} leaked"
                results[label] = {
                    "status": status,
                    "name": name,
                    "headline": (headline or "")[:70],
                    "location": value(body, "location"),
                    "experience_count": len(experience),
                    "education_count": len(education),
                    "skills_count": len(skills),
                    "first_role": (
                        {k: experience[0].get(k) for k in ("title", "company_name")}
                        if experience
                        else None
                    ),
                    "current": next(
                        (e.get("company_name") for e in experience if e.get("is_current")), None
                    ),
                    "urn": (value(body, "identity") or {}).get("member_urn"),
                    "observed_at": body["observed_at"],
                }
                print(f"   name={name!r} headline={results[label]['headline']!r}", flush=True)
            if index < len(SLUGS):
                await asyncio.sleep(GAP_SECONDS)

    if len(results) < 4:
        print(f"INCOMPLETE: only {len(results)}/4 requests succeeded", flush=True)
        sys.exit(1)

    a, b, c, a2 = (results.get(k) for k in (*SLUGS, "A-repeat"))
    assert a["name"] != b["name"] != c["name"], "names must differ across profiles"
    assert a["urn"] != b["urn"] != c["urn"], "member URNs must differ"
    assert a2["name"] == a["name"] and a2["urn"] == a["urn"], "A-repeat must return A"
    print("\nDIFFERENTIAL PASS", flush=True)
    print(json.dumps(results, indent=1, ensure_ascii=False), flush=True)


asyncio.run(main())
