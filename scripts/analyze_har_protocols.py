"""Print a secret-free protocol inventory for controlled LinkedIn HAR captures.

The report intentionally omits all header values, cookies, response bodies, and
request-body values. It is safe to use as a first-pass map before inspecting a
specific captured operation in a controlled local environment.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

INTERESTING_PATH_PARTS = ("/voyager/api/", "/rsc-action/")


def _header_names(headers: object) -> list[str]:
    if not isinstance(headers, list):
        return []
    return sorted(
        {
            str(header.get("name", "")).lower()
            for header in headers
            if isinstance(header, dict) and header.get("name")
        }
    )


def _query_shape(url: str) -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "value_length": len(value),
            **({"identifier": value} if name == "componentId" else {}),
        }
        for name, value in parse_qsl(urlsplit(url).query, keep_blank_values=True)
    ]


def _post_shape(post_data: object) -> dict[str, object] | None:
    if not isinstance(post_data, dict):
        return None
    text = post_data.get("text")
    params = post_data.get("params")
    return {
        "mime_type": post_data.get("mimeType"),
        "text_length": len(text) if isinstance(text, str) else 0,
        "param_names": sorted(
            {
                str(param.get("name", ""))
                for param in params
                if isinstance(param, dict) and param.get("name")
            }
        )
        if isinstance(params, list)
        else [],
    }


def _response_bytes(content: dict[str, Any]) -> bytes:
    text = content.get("text")
    if not isinstance(text, str):
        return b""
    if content.get("encoding") == "base64":
        try:
            return base64.b64decode(text)
        except ValueError:
            return b""
    return text.encode("utf-8", errors="replace")


def _semantic_markers(content: dict[str, Any]) -> dict[str, int]:
    decoded = _response_bytes(content).decode("utf-8", errors="replace").lower()
    markers = (
        "profilecards",
        "experience",
        "education",
        "skill",
        "certification",
        "language",
        "position",
        "school",
    )
    return {marker: decoded.count(marker) for marker in markers if marker in decoded}


def analyze(path: Path, *, compact: bool = False, rsc_only: bool = False) -> dict[str, Any]:
    with path.open(encoding="utf-8", errors="replace") as source:
        document = json.load(source)

    entries = document.get("log", {}).get("entries", [])
    operations: list[dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        request = entry.get("request") or {}
        response = entry.get("response") or {}
        content = response.get("content") or {}
        url = request.get("url", "")
        parsed = urlsplit(url)
        if not any(part in parsed.path for part in INTERESTING_PATH_PARTS):
            continue
        if rsc_only and "/rsc-action/" not in parsed.path:
            continue
        body = content.get("text")
        decoded = _response_bytes(content)
        operation = {
            "method": request.get("method"),
            "origin": f"{parsed.scheme}://{parsed.netloc}",
            "path": parsed.path,
            "query": _query_shape(url),
            "request_header_names": _header_names(request.get("headers")),
            "post_data": _post_shape(request.get("postData")),
            "status": response.get("status"),
            "response_mime_type": content.get("mimeType"),
            "response_text_length": len(body) if isinstance(body, str) else 0,
            "response_decoded_length": len(decoded),
            "response_encoding": content.get("encoding"),
            "response_sha256": hashlib.sha256(decoded).hexdigest() if decoded else None,
            "semantic_markers": _semantic_markers(content),
            "response_header_names": _header_names(response.get("headers")),
        }
        if compact:
            operation.pop("request_header_names")
            operation.pop("response_header_names")
            operation["query"] = [
                item for item in operation["query"] if item["name"] in {"componentId", "queryId"}
            ]
        operations.append(operation)

    return {
        "capture": path.name,
        "entry_count": len(entries),
        "interesting_operation_count": len(operations),
        "operations": operations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("har", type=Path, nargs="+")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--rsc-only", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            [analyze(path, compact=args.compact, rsc_only=args.rsc_only) for path in args.har],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
