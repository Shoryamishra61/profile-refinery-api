"""Inspect target-owned identity state in a captured LinkedIn Flight response.

The report is deliberately narrow: it prints semantic state names, scalar
types, and short public-profile values. It never emits request headers, cookies,
request bodies, or complete response records.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from tross_linkedin_api.rsc import FlightDocument, parse_rsc_core_payload


def _objects(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _component_id(entry: dict[str, Any]) -> str:
    url = entry.get("request", {}).get("url", "")
    return parse_qs(urlsplit(url).query).get("componentId", [""])[0]


def _response_text(entry: dict[str, Any]) -> str:
    content = entry.get("response", {}).get("content", {})
    text = content.get("text", "")
    if not isinstance(text, str):
        raise ValueError("Capture response has no text payload.")
    if content.get("encoding") == "base64":
        return base64.b64decode(text).decode("utf-8", errors="replace")
    return text


def _flight_models(text: str) -> list[Any]:
    output = []
    for line in text.splitlines():
        _, separator, payload = line.partition(":")
        if not separator or payload.startswith("I"):
            continue
        try:
            output.append(json.loads(payload))
        except json.JSONDecodeError:
            continue
    return output


def _state_summary(node: dict[str, Any]) -> tuple[str, str, str] | None:
    key = node.get("key")
    if not isinstance(key, dict):
        return None
    key_value = key.get("value")
    if not isinstance(key_value, dict) or not isinstance(key_value.get("id"), str):
        return None
    state_id = key_value["id"]
    if "loading_state" not in state_id:
        return None
    shape = {
        name: (
            sorted(child) if isinstance(child, dict) else type(child).__name__
        )
        for name, child in node.items()
        if name != "key"
    }
    scalar = next(
        (
            child
            for name, child in node.items()
            if name != "key" and isinstance(child, (str, int, float, bool))
        ),
        None,
    )
    return state_id, json.dumps(shape, sort_keys=True), str(scalar or "")[:160]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--har", type=Path, required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--component-suffix", default="profileCardsActivity")
    args = parser.parse_args()

    with args.har.open(encoding="utf-8", errors="replace") as source:
        document = json.load(source)
    entry = next(
        item
        for item in document["log"]["entries"]
        if _component_id(item).endswith(args.component_suffix)
    )
    request_body = json.loads(entry["request"]["postData"]["text"])
    print("request_body=" + json.dumps(request_body, separators=(",", ":"), ensure_ascii=True))
    print("request_query=" + json.dumps(parse_qs(urlsplit(entry["request"]["url"]).query)))
    flight_text = _response_text(entry)
    captured_slug = request_body["clientArguments"]["payload"]["vanityName"]
    parsed_core = parse_rsc_core_payload({"flight": flight_text}, captured_slug)
    safe_core = {
        "identity": parsed_core["identity"],
        "name": parsed_core["name"],
        "headline": parsed_core["headline"],
        "profile_image_present": parsed_core["profile_image"] is not None,
    }
    print("parsed_core=" + json.dumps(safe_core, ensure_ascii=True))
    raw_prioritized = sorted(
        set(re.findall(r'"prioritizedProfileId":"([A-Za-z0-9_-]+)"', flight_text))
    )
    print("captured_prioritized_profile_ids=" + json.dumps(raw_prioritized))
    document = FlightDocument.parse(flight_text)
    models = [document.resolve(model) for model in _flight_models(flight_text)]
    candidates = [
        node
        for model in models
        for node in _objects(model)
        if any(
            child.get("prioritizedProfileId") == args.target_id for child in _objects(node)
        )
        and any("loading_state" in value for value in _strings(node))
    ]
    if not candidates:
        raise ValueError("No target-owned identity state candidate was found.")
    owner = min(candidates, key=lambda node: len(json.dumps(node, separators=(",", ":"))))
    print(f"owner_candidate_count={len(candidates)}")
    print(f"owner_bytes={len(json.dumps(owner, separators=(',', ':')))}")
    prioritized = sorted(
        {
            node["prioritizedProfileId"]
            for node in _objects(owner)
            if isinstance(node.get("prioritizedProfileId"), str)
        }
    )
    summaries = sorted(
        {summary for node in _objects(owner) if (summary := _state_summary(node)) is not None}
    )
    print(f"component={args.component_suffix}")
    print(f"flight_models={len(models)}")
    print("prioritized_profile_ids=" + json.dumps(prioritized))
    for state_id, case_name, preview in summaries:
        print(
            "state="
            + json.dumps(
                {"id": state_id, "case": case_name, "preview": preview},
                ensure_ascii=True,
            )
        )
    for state_id in (
        "prioritizedProfileId",
        "profile_name_loading_state",
        "profile_headline_loading_state",
        "profile_photo_loading_state",
    ):
        index = flight_text.find(state_id)
        if index >= 0:
            context = flight_text[max(0, index - 240) : index + 360]
            print("context=" + json.dumps({"id": state_id, "text": context}, ensure_ascii=True))


if __name__ == "__main__":
    main()
