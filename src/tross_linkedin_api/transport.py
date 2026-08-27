from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Protocol

import httpx

from .config import Settings
from .errors import (
    ProfileNotFound,
    UpstreamAuthExpired,
    UpstreamChallenge,
    UpstreamOperationDrift,
    UpstreamRateLimited,
    UpstreamTimeout,
)
from .models import OperationResult
from .observability import OperationEvent, log_operation
from .operation_registry import Operation, OperationRegistry
from .session import SessionProvider

UPSTREAM_ORIGIN = "https://www.linkedin.com"
_JSON_CONTENT_TYPES = {"application/json", "application/vnd.linkedin.normalized+json+2.1"}


class Transport(Protocol):
    async def execute(self, semantic_name: str, slug: str, request_id: str) -> OperationResult: ...

    async def aclose(self) -> None: ...


class FixtureTransport:
    def __init__(self, registry: OperationRegistry, fixture_root: Path) -> None:
        self._registry = registry
        self._fixture_root = fixture_root.resolve()
        self.call_count = 0

    async def execute(self, semantic_name: str, slug: str, request_id: str) -> OperationResult:
        del slug
        operation = self._registry.get(semantic_name)
        if not operation.fixture:
            raise UpstreamOperationDrift(
                semantic_name, "The fixture-backed operation has no fixture."
            )
        path = (self._fixture_root / Path(operation.fixture).name).resolve()
        if self._fixture_root not in path.parents or not path.is_file():
            raise UpstreamOperationDrift(semantic_name, "The registered fixture is unavailable.")
        started = time.perf_counter()
        try:
            raw = path.read_bytes()
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise UpstreamOperationDrift(
                semantic_name, "The registered fixture is malformed."
            ) from exc
        if not isinstance(payload, dict):
            raise UpstreamOperationDrift(semantic_name, "The fixture root must be an object.")
        duration = (time.perf_counter() - started) * 1000
        self.call_count += 1
        log_operation(OperationEvent(request_id, semantic_name, duration, 200, "pending", 1))
        return OperationResult(
            operation=semantic_name, payload=payload, duration_ms=duration, status_code=200
        )

    async def aclose(self) -> None:
        return None


class LinkedInTransport:
    def __init__(
        self, settings: Settings, registry: OperationRegistry, session: SessionProvider
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._session = session
        timeout = httpx.Timeout(settings.app_upstream_timeout_seconds, connect=5.0)
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        self._client = httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=False)
        self.call_count = 0

    def _request_parts(
        self, operation: Operation, slug: str
    ) -> tuple[dict[str, str], dict[str, Any]]:
        session = self._session.load()
        headers = {
            "accept": "application/vnd.linkedin.normalized+json+2.1",
            "csrf-token": session.csrf_token,
            "x-restli-protocol-version": "2.0.0",
        }
        cookies = {"li_at": session.li_at, "JSESSIONID": session.jsessionid}
        variables: dict[str, Any] = {"member_identity": slug}
        body: dict[str, Any] = {"variables": variables}
        if operation.query_id_env:
            query_id = os.getenv(operation.query_id_env)
            if not query_id:
                raise UpstreamOperationDrift(
                    operation.semantic_name, "The registered query identifier is unavailable."
                )
            body["queryId"] = query_id
        return {
            **headers,
            "cookie": "; ".join(f"{key}={value}" for key, value in cookies.items()),
        }, body

    async def execute(self, semantic_name: str, slug: str, request_id: str) -> OperationResult:
        operation = self._registry.get(semantic_name)
        headers, body = self._request_parts(operation, slug)
        url = f"{UPSTREAM_ORIGIN}{operation.path}"
        attempts = self._settings.app_upstream_retries + 1
        for attempt in range(1, attempts + 1):
            started = time.perf_counter()
            try:
                async with self._client.stream(
                    operation.method,
                    url,
                    headers=headers,
                    json=body if operation.method == "POST" else None,
                    params=body if operation.method == "GET" else None,
                ) as response:
                    self.call_count += 1
                    duration = (time.perf_counter() - started) * 1000
                    self._classify_status(response, operation.semantic_name)
                    if response.is_redirect:
                        raise UpstreamOperationDrift(
                            semantic_name, "Upstream redirects are refused."
                        )
                    media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    raw = await self._read_limited(response, semantic_name)
                    if media_type not in _JSON_CONTENT_TYPES:
                        lowered = raw[:4096].lower()
                        if media_type == "text/html" and any(
                            token in lowered
                            for token in (b"checkpoint", b"security challenge", b"challenge")
                        ):
                            self._session.fail_closed()
                            raise UpstreamChallenge()
                        raise UpstreamOperationDrift(
                            semantic_name, "Upstream returned a non-JSON content type."
                        )
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        raise UpstreamOperationDrift(
                            semantic_name, "Upstream returned malformed JSON."
                        ) from exc
                    if not isinstance(payload, dict):
                        raise UpstreamOperationDrift(
                            semantic_name, "Upstream JSON root is not an object."
                        )
                    log_operation(
                        OperationEvent(
                            request_id,
                            semantic_name,
                            duration,
                            response.status_code,
                            "pending",
                            attempt,
                        )
                    )
                    return OperationResult(
                        operation=semantic_name,
                        payload=payload,
                        duration_ms=duration,
                        status_code=response.status_code,
                    )
            except httpx.TimeoutException as exc:
                if attempt == attempts:
                    raise UpstreamTimeout(semantic_name) from exc
            except (httpx.ConnectError, httpx.ReadError) as exc:
                if attempt == attempts:
                    raise UpstreamTimeout(semantic_name) from exc
            if attempt < attempts:
                await asyncio.sleep(0.1 * attempt)
        raise AssertionError("unreachable transport retry state")

    async def _read_limited(self, response: httpx.Response, operation: str) -> bytes:
        content_length = response.headers.get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > self._settings.app_upstream_max_bytes:
                raise UpstreamOperationDrift(
                    operation, "Upstream payload exceeded the configured size limit."
                )
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > self._settings.app_upstream_max_bytes:
                raise UpstreamOperationDrift(
                    operation, "Upstream payload exceeded the configured size limit."
                )
            chunks.append(chunk)
        return b"".join(chunks)

    def _classify_status(self, response: httpx.Response, operation: str) -> None:
        if response.status_code == 401:
            self._session.fail_closed()
            raise UpstreamAuthExpired()
        if response.status_code == 403:
            self._session.fail_closed()
            raise UpstreamChallenge()
        if response.status_code == 404:
            raise ProfileNotFound()
        if response.status_code == 429:
            raise UpstreamRateLimited()
        if response.status_code in {400, 410, 422}:
            raise UpstreamOperationDrift(operation)
        if response.status_code >= 500:
            raise httpx.ReadError("transient upstream server failure", request=response.request)
        if response.status_code >= 300:
            raise UpstreamOperationDrift(
                operation, f"Unexpected upstream status class: {response.status_code // 100}xx"
            )

    async def aclose(self) -> None:
        await self._client.aclose()
