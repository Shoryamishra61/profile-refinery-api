from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Protocol

import httpx

from .config import Settings
from .errors import (
    ProfileNotFound,
    UpstreamAuthExpired,
    UpstreamChallenge,
    UpstreamForbidden,
    UpstreamOperationDrift,
    UpstreamRateLimited,
    UpstreamTimeout,
    UpstreamUnavailable,
)
from .models import OperationResult
from .observability import OperationEvent, log_operation
from .operation_registry import Operation, OperationRegistry, TransportKind
from .rsc import build_profile_activity_body, build_profile_component_body
from .session import SessionProvider

UPSTREAM_ORIGIN = "https://www.linkedin.com"
_JSON_CONTENT_TYPES = {"application/json", "application/vnd.linkedin.normalized+json+2.1"}
_MAX_HTML_EMBEDDED_BYTES = 4_000_000

# Authenticated LinkedIn pages embed server-rendered Voyager entities inside
# <code><!--{...}--></code> blocks. Embedded-JSON documents may also appear in
# inline scripts; both shapes are scanned for {"included": [...]} documents.
_CODE_BLOCK_RE = re.compile(r"<code[^>]*><!--(.*?)--></code>", re.DOTALL)
_INCLUDED_KEY = '{"included"'


class Transport(Protocol):
    call_count: int

    async def execute(
        self, semantic_name: str, slug: str, request_id: str, resource_id: str | None = None
    ) -> OperationResult: ...

    async def aclose(self) -> None: ...


class FixtureTransport:
    def __init__(self, registry: OperationRegistry, fixture_root: Path) -> None:
        self._registry = registry
        self._fixture_root = fixture_root.resolve()
        self.call_count = 0

    async def execute(
        self, semantic_name: str, slug: str, request_id: str, resource_id: str | None = None
    ) -> OperationResult:
        del slug, resource_id
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


def extract_embedded_json(html: str) -> dict[str, Any] | None:
    """Return the richest embedded Voyager JSON document found in an HTML page.

    Handles both the <code><!--{...}--></code> SSR blocks and inline-script JSON
    documents that carry an "included" entity array. Returns None when no block
    contains one, which callers treat as operation drift rather than as success.
    """
    best: dict[str, Any] | None = None
    candidates: list[str] = [match.group(1) for match in _CODE_BLOCK_RE.finditer(html)]
    start = 0
    while True:
        found = html.find(_INCLUDED_KEY, start)
        if found == -1:
            break
        start = found + 1
        candidates.append(html[found : found + _MAX_HTML_EMBEDDED_BYTES])
    for candidate in candidates:
        payload = _decode_json_object(candidate)
        if isinstance(payload, dict) and isinstance(payload.get("included"), list):
            size = len(payload["included"])
            if best is None or size > len(best["included"]):
                best = payload
    return best


def _decode_json_object(text: str) -> Any:
    decoder = json.JSONDecoder()
    try:
        payload, _ = decoder.raw_decode(text.lstrip())
    except (json.JSONDecodeError, ValueError):
        return None
    return payload


class LinkedInTransport:
    """Direct HTTP transport for LinkedIn endpoints using an owned session.

    Protocol model (evidence: anonymous probe on 2026-08-28, see
    docs/REVERSE_ENGINEERING_PROTOCOL.md):
      * /voyager/api resources require a `csrf-token` header whose value equals
        the JSESSIONID cookie (quotes stripped) — a request without it is
        rejected with 403 "CSRF check failed" before any authorization check.
      * The classic /voyager/api/identity/profiles/{slug}/profileView resource
        is retired (HTTP 410). The current member-finder resource observed live
        (2026-08-28) is /voyager/api/identity/dash/profiles?q=memberIdentity,
        which answers 200 JSON for an authenticated session.
      * LinkedIn rotates session cookies server-side; the transport therefore
        seeds a persistent cookie jar with li_at/JSESSIONID and lets the jar
        track Set-Cookie across requests, deriving csrf-token from the jar's
        current JSESSIONID on every call.
      * Bursty scripted traffic is answered with a same-URL 302 that clears
        cookies (soft challenge). The transport never loops: one same-URL
        retry, then an explicit UPSTREAM_CHALLENGE.
      * Unauthenticated page requests are refused with the 999 bot-wall status;
        an owned `li_at` session is therefore required for live extraction.
    """

    def __init__(
        self, settings: Settings, registry: OperationRegistry, session: SessionProvider
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._session = session
        timeout = httpx.Timeout(settings.app_upstream_timeout_seconds, connect=5.0)
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        proxy = settings.linkedin_egress_proxy
        client_options: dict[str, Any] = {
            "timeout": timeout,
            "limits": limits,
            "follow_redirects": False,
            "http2": True,
        }
        if proxy is not None:
            client_options["proxy"] = proxy.get_secret_value()
        self._client = httpx.AsyncClient(**client_options)
        if self._session.available:
            seeded = self._session.load()
            self._client.cookies.set("li_at", seeded.li_at, domain=".linkedin.com")
            self._client.cookies.set(
                "JSESSIONID", f'"{seeded.jsessionid}"', domain=".www.linkedin.com"
            )
            extra = self._settings.linkedin_cookie
            if extra:
                for pair in extra.get_secret_value().split(";"):
                    name, _, value = pair.strip().partition("=")
                    if name and value and name not in ("li_at", "JSESSIONID"):
                        self._client.cookies.set(
                            name.strip(), value.strip(), domain=".linkedin.com"
                        )
        self.call_count = 0

    def _csrf_token(self) -> str:
        # The jar's JSESSIONID is authoritative: the server rotates it and the
        # CSRF contract requires the header to match the cookie sent.
        current = self._client.cookies.get("JSESSIONID", domain=".www.linkedin.com")
        if not current:
            current = self._client.cookies.get("JSESSIONID") or ""
        if not current:
            current = self._session.load().jsessionid
        return current.strip('"')

    def _api_headers(self) -> dict[str, str]:
        self._session.load()  # fail closed when no session is configured
        return {
            "accept": "application/vnd.linkedin.normalized+json+2.1",
            "csrf-token": self._csrf_token(),
            "x-restli-protocol-version": "2.0.0",
            "x-li-lang": "en_US",
            "user-agent": self._settings.linkedin_user_agent,
            "accept-language": self._settings.linkedin_accept_language,
        }

    def _page_headers(self) -> dict[str, str]:
        self._session.load()  # fail closed when no session is configured
        return {
            "accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),
            "user-agent": self._settings.linkedin_user_agent,
            "accept-language": self._settings.linkedin_accept_language,
        }

    def _rsc_headers(self, slug: str) -> dict[str, str]:
        self._session.load()
        return {
            "accept": "*/*",
            "accept-language": self._settings.linkedin_accept_language,
            "content-type": "application/json",
            "csrf-token": self._csrf_token(),
            "origin": UPSTREAM_ORIGIN,
            "referer": f"{UPSTREAM_ORIGIN}/in/{slug}/",
            "user-agent": self._settings.linkedin_user_agent,
            "x-li-anchor-page-key": "d_flagship3_profile_view_base",
            "x-li-rsc-stream": "true",
        }

    async def execute(
        self, semantic_name: str, slug: str, request_id: str, resource_id: str | None = None
    ) -> OperationResult:
        operation = self._registry.get(semantic_name)
        if operation.kind is TransportKind.HTML:
            return await self._execute_page(operation, slug, request_id)
        if operation.kind is TransportKind.RSC:
            return await self._execute_rsc(operation, slug, request_id, resource_id)
        return await self._execute_restli(operation, slug, request_id, resource_id)

    async def _execute_rsc(
        self,
        operation: Operation,
        slug: str,
        request_id: str,
        viewee_id: str | None,
    ) -> OperationResult:
        if not operation.component_id or (
            operation.request_variant == "profile_section" and not viewee_id
        ):
            raise UpstreamOperationDrift(
                operation.semantic_name, "RSC request lacks component or target identity."
            )
        started = time.perf_counter()
        url = f"{UPSTREAM_ORIGIN}{operation.path}"
        params = {
            "componentId": operation.component_id,
            "sduiid": operation.component_id,
        }
        body = (
            build_profile_activity_body(slug)
            if operation.request_variant == "profile_activity"
            else build_profile_component_body(slug, viewee_id or "")
        )
        try:
            async with self._client.stream(
                "POST",
                url,
                params=params,
                headers=self._rsc_headers(slug),
                content=json.dumps(body, separators=(",", ":")).encode(),
            ) as response:
                self.call_count += 1
                duration = (time.perf_counter() - started) * 1000
                if response.is_redirect:
                    location = response.headers.get("location", "")
                    if "authwall" in location or "login" in location:
                        self._session.fail_closed()
                        raise UpstreamAuthExpired()
                    raise UpstreamChallenge()
                if response.status_code == 401:
                    self._session.fail_closed()
                    raise UpstreamAuthExpired()
                if response.status_code == 403:
                    raise UpstreamForbidden()
                if response.status_code == 404:
                    raise UpstreamOperationDrift(
                        operation.semantic_name, "RSC component operation returned 404."
                    )
                if response.status_code == 429:
                    raise UpstreamRateLimited()
                if response.status_code >= 500:
                    raise UpstreamUnavailable(operation.semantic_name)
                if response.status_code >= 300:
                    raise UpstreamOperationDrift(
                        operation.semantic_name,
                        f"Unexpected RSC status class: {response.status_code // 100}xx",
                    )
                media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                raw = await self._read_limited(response, operation.semantic_name)
                if media_type != "application/octet-stream":
                    raise UpstreamOperationDrift(
                        operation.semantic_name, "RSC operation returned an unexpected media type."
                    )
                try:
                    flight = raw.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise UpstreamOperationDrift(
                        operation.semantic_name, "RSC operation returned non-UTF-8 Flight data."
                    ) from exc
                log_operation(
                    OperationEvent(
                        request_id,
                        operation.semantic_name,
                        duration,
                        response.status_code,
                        "pending",
                        1,
                    )
                )
                return OperationResult(
                    operation=operation.semantic_name,
                    payload={"flight": flight, "component_id": operation.component_id},
                    duration_ms=duration,
                    status_code=response.status_code,
                )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeout(operation.semantic_name) from exc
        except (httpx.ConnectError, httpx.ReadError) as exc:
            raise UpstreamUnavailable(operation.semantic_name) from exc

    async def _execute_restli(
        self, operation: Operation, slug: str, request_id: str, resource_id: str | None = None
    ) -> OperationResult:
        """Try each registered decoration id until one yields a usable payload.

        Decoration versions are LinkedIn-side template revisions that rotate; a
        retired version answers 404/410 while a current one answers 200. Trying
        the configured list in order keeps the contract self-healing without
        guessing during a live request. A path containing {resource_id} is a
        sub-resource (e.g. profileCards): resource_id is substituted and the
        memberIdentity query parameters are omitted.
        """
        started = time.perf_counter()
        path = (
            operation.path.replace("{resource_id}", resource_id) if resource_id else operation.path
        )
        sub_resource = resource_id is not None and "{resource_id}" in operation.path
        url = f"{UPSTREAM_ORIGIN}{path}"
        last_error: UpstreamOperationDrift | None = None
        attempts = 0
        # An empty decoration list is a valid configuration: the observed
        # memberIdentity finder answers with its default projection.
        decorations: list[str | None] = list(operation.decoration_ids) or [None]
        for decoration in decorations:
            params: dict[str, str] = {"q": "memberIdentity", "memberIdentity": slug}
            if sub_resource:
                params = {}
            if decoration is not None:
                params["decorationId"] = decoration
            result, error = await self._request_json(
                operation, request_id, url, params, started, attempts
            )
            attempts += 1
            if result is not None:
                return result
            assert error is not None
            last_error = error if isinstance(error, UpstreamOperationDrift) else None
            if last_error is None:
                raise error
        raise last_error or UpstreamOperationDrift(
            operation.semantic_name, "Every registered decoration id was refused upstream."
        )

    async def _request_json(
        self,
        operation: Operation,
        request_id: str,
        url: str,
        params: dict[str, str],
        started: float,
        attempts: int,
    ) -> tuple[OperationResult | None, Exception | None]:
        """Single-attempt JSON request. Retry policy lives in the governor —
        this method performs exactly one HTTP attempt and either returns a
        result, a decoration-fallthrough signal, or a typed failure."""
        # The jar's JSESSIONID may have been rotated by a previous response.
        headers = self._api_headers()
        try:
            async with self._client.stream("GET", url, headers=headers, params=params) as response:
                self.call_count += 1
                duration = (time.perf_counter() - started) * 1000
                if response.is_redirect:
                    # Authwall/login redirects mean the li_at session is dead:
                    # that is a permanent state, so the session is invalidated.
                    location = response.headers.get("location", "")
                    if "authwall" in location or "login" in location:
                        self._session.fail_closed()
                        raise UpstreamAuthExpired()
                    # A same-URL redirect is LinkedIn's soft-challenge signal:
                    # transient, so the circuit breaker owns recovery. The
                    # session itself stays configured and the breaker's
                    # cooldown probe will restore extraction automatically.
                    raise UpstreamChallenge()
                if response.status_code != 404:
                    self._classify_status(response, operation.semantic_name)
                media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                raw = await self._read_limited(response, operation.semantic_name)
                if response.status_code == 404:
                    if media_type in _JSON_CONTENT_TYPES:
                        # A JSON 404 from a current resource means the profile
                        # itself is absent for this viewer.
                        raise ProfileNotFound()
                    return None, UpstreamOperationDrift(
                        operation.semantic_name,
                        "Request answered 404 with an HTML error page.",
                    )
                if media_type not in _JSON_CONTENT_TYPES:
                    if media_type == "text/html":
                        lowered = raw[:4096].lower()
                        if b"checkpoint" in lowered or b"challenge" in lowered:
                            # Transient challenge: breaker owns recovery.
                            raise UpstreamChallenge()
                    # A retired decoration answers with an HTML error page.
                    return None, UpstreamOperationDrift(
                        operation.semantic_name,
                        "Upstream answered a decoration request with non-JSON content.",
                    )
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    # A malformed body means this decoration is not usable;
                    # the next registered one may still answer correctly.
                    return None, UpstreamOperationDrift(
                        operation.semantic_name, "Upstream returned malformed JSON."
                    )
                if not isinstance(payload, dict):
                    return None, UpstreamOperationDrift(
                        operation.semantic_name, "Upstream JSON root is not an object."
                    )
                status = payload.get("data", {})
                if isinstance(status, dict) and status.get("status") == 404:
                    raise ProfileNotFound()
                log_operation(
                    OperationEvent(
                        request_id,
                        operation.semantic_name,
                        duration,
                        response.status_code,
                        "pending",
                        attempts + 1,
                    )
                )
                return (
                    OperationResult(
                        operation=operation.semantic_name,
                        payload=payload,
                        duration_ms=duration,
                        status_code=response.status_code,
                    ),
                    None,
                )
        except httpx.TimeoutException as exc:
            timeout_error = UpstreamTimeout(operation.semantic_name)
            raise timeout_error from exc
        except (httpx.ConnectError, httpx.ReadError) as exc:
            unavailable_error = UpstreamUnavailable(operation.semantic_name)
            raise unavailable_error from exc

    async def _execute_page(
        self, operation: Operation, slug: str, request_id: str
    ) -> OperationResult:
        started = time.perf_counter()
        url = f"{UPSTREAM_ORIGIN}/in/{slug}/"
        headers = self._page_headers()
        try:
            response = await self._client.get(url, headers=headers, follow_redirects=False)
        except httpx.TimeoutException as exc:
            raise UpstreamTimeout(operation.semantic_name) from exc
        except (httpx.ConnectError, httpx.ReadError) as exc:
            raise UpstreamUnavailable(operation.semantic_name) from exc
        self.call_count += 1
        duration = (time.perf_counter() - started) * 1000
        self._classify_page_status(response, operation.semantic_name)
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type != "text/html" or response.status_code != 200:
            raise UpstreamOperationDrift(
                operation.semantic_name,
                "The profile page did not return an HTML document.",
            )
        if len(response.content) > self._settings.app_upstream_max_bytes:
            raise UpstreamOperationDrift(
                operation.semantic_name, "Upstream payload exceeded the configured size limit."
            )
        html = response.text
        payload = extract_embedded_json(html)
        if payload is None:
            raise UpstreamOperationDrift(
                operation.semantic_name,
                "No embedded Voyager JSON document was found in the profile page.",
            )
        log_operation(
            OperationEvent(
                request_id, operation.semantic_name, duration, response.status_code, "pending", 1
            )
        )
        return OperationResult(
            operation=operation.semantic_name,
            payload=payload,
            duration_ms=duration,
            status_code=response.status_code,
        )

    def _classify_page_status(self, response: httpx.Response, operation: str) -> None:
        # Challenges (999 bot wall, same-URL redirects) are transient:
        # the circuit breaker owns their recovery. Only authwall redirects and
        # 401s invalidate the session itself.
        if response.is_redirect:
            location = response.headers.get("location", "")
            if "authwall" in location or "login" in location:
                self._session.fail_closed()
                raise UpstreamAuthExpired()
            raise UpstreamChallenge()
        if response.status_code == 999:
            raise UpstreamChallenge()
        if response.status_code == 401:
            self._session.fail_closed()
            raise UpstreamAuthExpired()
        if response.status_code == 403:
            raise UpstreamForbidden()
        if response.status_code == 404:
            raise ProfileNotFound()
        if response.status_code == 429:
            raise UpstreamRateLimited()
        if response.status_code >= 500:
            raise UpstreamUnavailable(operation)
        if response.status_code >= 300:
            raise UpstreamOperationDrift(
                operation, f"Unexpected page status class: {response.status_code // 100}xx"
            )

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
            raise UpstreamForbidden()
        if response.status_code == 404:
            # Only fatal once every decoration has been tried; callers treat this
            # as a candidate-level signal inside _execute_restli.
            raise ProfileNotFound()
        if response.status_code == 429:
            raise UpstreamRateLimited()
        if response.status_code in {400, 410, 422}:
            raise UpstreamOperationDrift(operation)
        if response.status_code >= 500:
            raise UpstreamUnavailable(operation)
        if response.status_code >= 300:
            raise UpstreamOperationDrift(
                operation, f"Unexpected upstream status class: {response.status_code // 100}xx"
            )

    async def aclose(self) -> None:
        await self._client.aclose()
