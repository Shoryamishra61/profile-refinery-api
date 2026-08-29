"""Replay one captured LinkedIn RSC component request over direct HTTP.

This controlled-research tool reads owned session material from an env file and
a request template from a HAR capture. It never prints cookies, header values,
request bodies, or raw responses. Stop after any non-200 response; do not use it
to automate retries or challenge handling.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import httpx
from dotenv import dotenv_values

SAFE_CAPTURED_HEADERS = {
    "accept",
    "accept-language",
    "content-type",
    "origin",
    "referer",
    "user-agent",
    "x-li-anchor-page-key",
    "x-li-rsc-stream",
}


def _component_id(entry: dict[str, Any]) -> str:
    url = entry.get("request", {}).get("url", "")
    return parse_qs(urlsplit(url).query).get("componentId", [""])[0]


def _component_url(url: str) -> str:
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    stable_query = {
        name: query[name][0]
        for name in ("componentId", "sduiid")
        if name in query and query[name]
    }
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(stable_query), ""))


def _replace_strings(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [_replace_strings(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _replace_strings(item, replacements) for key, item in value.items()}
    return value


def _template_identity(body: dict[str, Any]) -> tuple[str, str]:
    payload = body["clientArguments"]["payload"]
    vanity = payload["vanityName"]
    replacement_args = payload["replaceableSectionArgs"]
    viewee_id = replacement_args["vieweeProfileId"]
    if not isinstance(vanity, str) or not isinstance(viewee_id, str):
        raise ValueError("Captured component body lacks a usable target identity.")
    return vanity, viewee_id


def _session_cookies(values: dict[str, str | None]) -> tuple[dict[str, str], str]:
    li_at = values.get("LINKEDIN_LI_AT")
    jsessionid = values.get("LINKEDIN_JSESSIONID")
    if not li_at or not jsessionid:
        raise ValueError("The env file lacks owned LinkedIn session material.")
    cookies = {
        "li_at": li_at,
        "JSESSIONID": jsessionid if jsessionid.startswith('"') else f'"{jsessionid}"',
    }
    for pair in (values.get("LINKEDIN_COOKIE") or "").split(";"):
        name, separator, value = pair.strip().partition("=")
        if separator and name and name not in cookies:
            cookies[name] = value
    return cookies, jsessionid.strip('"')


def _visible_leaves(text: str) -> list[str]:
    leaves: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "children" and isinstance(child, list):
                    leaves.extend(
                        item
                        for item in child
                        if isinstance(item, str)
                        and not item.startswith("$")
                        and item not in {"button", "div", "hr", "p", "section"}
                    )
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for line in text.splitlines():
        _, separator, payload = line.partition(":")
        if not separator or payload.startswith("I"):
            continue
        try:
            walk(json.loads(payload))
        except json.JSONDecodeError:
            continue
    return leaves


def _semantic_values(text: str, keys: set[str]) -> dict[str, list[str]]:
    found = {key: set() for key in keys}

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in found and isinstance(child, str):
                    found[key].add(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for line in text.splitlines():
        _, separator, payload = line.partition(":")
        if not separator or payload.startswith("I"):
            continue
        try:
            walk(json.loads(payload))
        except json.JSONDecodeError:
            continue
    return {key: sorted(values) for key, values in found.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--har", type=Path, required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--viewee-id", required=True)
    parser.add_argument(
        "--component-suffix",
        action="append",
        default=[],
        help="Captured component suffix to replay; repeat for a paced sequence.",
    )
    parser.add_argument("--pace-seconds", type=float, default=2.0)
    args = parser.parse_args()

    values = dict(dotenv_values(args.env_file))
    cookies, csrf_token = _session_cookies(values)
    with args.har.open(encoding="utf-8", errors="replace") as source:
        document = json.load(source)
    suffixes = args.component_suffix or ["profileCardsExperienceOnly"]
    with httpx.Client(timeout=30, follow_redirects=False, cookies=cookies) as client:
        for index, suffix in enumerate(suffixes):
            if index:
                time.sleep(max(0.0, args.pace_seconds))
            entry = next(
                item for item in document["log"]["entries"] if _component_id(item).endswith(suffix)
            )
            request = entry["request"]
            template_body = json.loads(request["postData"]["text"])
            old_vanity, old_viewee_id = _template_identity(template_body)
            body = _replace_strings(
                template_body,
                {old_vanity: args.slug, old_viewee_id: args.viewee_id},
            )
            headers = {
                header["name"]: header["value"]
                for header in request.get("headers", [])
                if header.get("name", "").lower() in SAFE_CAPTURED_HEADERS
            }
            headers.update(
                {
                    "csrf-token": csrf_token,
                    "referer": f"https://www.linkedin.com/in/{args.slug}/",
                }
            )
            response = client.post(
                _component_url(request["url"]),
                headers=headers,
                content=json.dumps(body, separators=(",", ":")).encode(),
            )

            media_type = response.headers.get("content-type", "").split(";", 1)[0]
            location = response.headers.get("location", "").lower()
            redirect_class = "none"
            if response.is_redirect:
                redirect_class = (
                    "auth"
                    if "login" in location or "authwall" in location
                    else "challenge_or_other"
                )
            print(f"component={suffix}")
            print(f"status={response.status_code}")
            print(f"content_type={media_type}")
            print(f"bytes={len(response.content)}")
            print(f"redirect_class={redirect_class}")
            if response.status_code != 200:
                return

            text = response.content.decode("utf-8", errors="replace")
            print(f"flight_records={len(text.splitlines())}")
            for marker in (
                "profile-card-experience",
                "Experience",
                "entity-collection-item",
                "Education",
                "Skills",
                "Certification",
                "Language",
            ):
                print(f"marker_{marker.lower()}={text.casefold().count(marker.casefold())}")
            semantic = _semantic_values(text, {"legacyControlName", "semanticId", "viewName"})
            print("view_names=" + json.dumps(semantic["viewName"]))
            print("legacy_control_names=" + json.dumps(semantic["legacyControlName"]))
            print("semantic_ids=" + json.dumps(semantic["semanticId"]))
            print("visible_leaves=" + json.dumps(_visible_leaves(text)[:120], ensure_ascii=True))


if __name__ == "__main__":
    main()
