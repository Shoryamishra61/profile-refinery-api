"""Probe the authenticated profile bootstrap over direct HTTP, without parsing DOM."""

from __future__ import annotations

import argparse
from pathlib import Path

import httpx
from dotenv import dotenv_values

from profile_refinery_api.canonicalizer import canonicalize_profile_url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    values = dotenv_values(args.env_file)
    li_at = values.get("LINKEDIN_LI_AT")
    jsessionid = values.get("LINKEDIN_JSESSIONID")
    if not li_at or not jsessionid:
        raise ValueError("Owned session material is unavailable.")
    canonical = canonicalize_profile_url(args.url)
    cookies = {
        "li_at": li_at,
        "JSESSIONID": (
            jsessionid if jsessionid.startswith('"') else f'"{jsessionid}"'
        ),
    }
    for pair in (values.get("LINKEDIN_COOKIE") or "").split(";"):
        name, separator, value = pair.strip().partition("=")
        if separator and name and name not in cookies:
            cookies[name] = value
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
    }
    with httpx.Client(timeout=30, follow_redirects=False, cookies=cookies) as client:
        response = client.get(canonical.canonical_url + "/", headers=headers)
    print(f"status={response.status_code}")
    print(f"content_type={response.headers.get('content-type', '').split(';', 1)[0]}")
    print(f"bytes={len(response.content)}")
    print(f"has_rehydrate_data={'window.__como_rehydration__' in response.text}")
    print(f"is_redirect={response.is_redirect}")


if __name__ == "__main__":
    main()
