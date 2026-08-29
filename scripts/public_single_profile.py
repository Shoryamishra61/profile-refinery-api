"""Call the deployed single-profile API using a secret env file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx
from dotenv import dotenv_values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--base", default="https://tross-linkedin-profile-api.vercel.app")
    args = parser.parse_args()
    keys = dotenv_values(args.env_file).get("APP_API_KEYS")
    if not keys:
        raise ValueError("APP_API_KEYS is unavailable.")
    key = keys.split(",", 1)[0].strip()
    response = httpx.get(
        f"{args.base}/v1/profiles",
        params={"url": args.url},
        headers={"X-API-Key": key},
        timeout=60,
    )
    print(f"status={response.status_code}")
    try:
        body = response.json()
    except ValueError:
        print("response=non-json")
        return
    if response.status_code != 200:
        print(f"code={body.get('code')}")
        return
    print(f"name={body['profile']['name']['value']}")
    print("coverage=" + json.dumps(body["meta"]["coverage"], sort_keys=True))


if __name__ == "__main__":
    main()
