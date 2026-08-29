from __future__ import annotations

import hmac
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, Security, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.security import APIKeyHeader

from .batch.service import BatchService
from .canonicalizer import canonicalize_profile_url
from .errors import (
    CallerRateLimited,
    InvalidProfileUrl,
    ProblemError,
    UnauthorizedCaller,
    UpstreamFailure,
)
from .metrics import METRICS
from .models import ProfileResponse
from .parsers import parse_section_payload
from .rate_limit import SlidingWindowLimiter
from .rsc import describe_rsc_payload
from .runtime import Runtime

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _authorized(x_api_key: str | None, runtime: Runtime) -> str:
    if x_api_key is None or not any(
        hmac.compare_digest(x_api_key, expected) for expected in runtime.settings.api_key_values
    ):
        raise UnauthorizedCaller()
    return x_api_key


def _authorized_validation(x_api_key: str | None, runtime: Runtime) -> str:
    validation_key = runtime.settings.app_validation_api_key
    expected = validation_key.get_secret_value() if validation_key else None
    if x_api_key is None or expected is None or not hmac.compare_digest(x_api_key, expected):
        raise UnauthorizedCaller()
    return x_api_key


def build_router(runtime: Runtime) -> APIRouter:
    router = APIRouter()
    limiter = SlidingWindowLimiter(
        runtime.settings.app_rate_limit_requests,
        runtime.settings.app_rate_limit_window_seconds,
    )
    batches = BatchService(runtime)

    @router.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @router.get("/healthz", tags=["operations"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/readyz", tags=["operations"])
    async def ready() -> JSONResponse:
        capability = runtime.extraction_capability()
        ready = runtime.ready
        body: dict[str, object] = {
            "status": "ready" if ready else "not_ready",
            "extraction_capability": capability,
        }
        return JSONResponse(body, status_code=200 if ready else 503)

    @router.get("/v1/capability", tags=["operations"])
    async def capability(
        x_api_key: str | None = Security(API_KEY_HEADER),
    ) -> JSONResponse:
        _authorized(x_api_key, runtime)
        queue = batches.queue_stats()
        metrics = METRICS.snapshot()
        metrics["gauges"]["queue_depth"] = queue["queue_depth"]
        metrics["gauges"]["jobs_running"] = queue["jobs_running"]
        metrics["gauges"]["queue_oldest_age_seconds"] = queue["queue_oldest_age_seconds"]
        return JSONResponse(
            {
                "extraction_capability": runtime.extraction_capability(),
                "queue": queue,
                "metrics": metrics,
            }
        )

    @router.get("/metrics", tags=["operations"], include_in_schema=False)
    async def metrics_endpoint() -> Response:
        queue = batches.queue_stats()
        METRICS.set_gauge("queue_depth", queue["queue_depth"])
        METRICS.set_gauge("jobs_running", queue["jobs_running"])
        METRICS.set_gauge("queue_oldest_age_seconds", queue["queue_oldest_age_seconds"])
        METRICS.set_gauge("jobs_blocked_upstream", queue["jobs_blocked_upstream"])
        breaker = runtime.governor.breaker
        METRICS.set_gauge(
            "breaker_state",
            {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}[breaker.state.value],
        )
        return Response(content=METRICS.prometheus(), media_type="text/plain")

    @router.get(
        "/v1/profiles",
        response_model=ProfileResponse,
        responses={
            400: {"content": {"application/problem+json": {}}},
            401: {},
            404: {},
            429: {},
            502: {},
            503: {},
            504: {},
        },
        tags=["profiles"],
    )
    async def profile(
        request: Request,
        url: Annotated[str, Query(min_length=1, max_length=2048)],
        x_api_key: str | None = Security(API_KEY_HEADER),
    ) -> ProfileResponse:
        caller = _authorized(x_api_key, runtime)
        retry_after = limiter.check(caller)
        if retry_after is not None:
            raise CallerRateLimited(retry_after)
        canonical = canonicalize_profile_url(url)
        runtime.ensure_profile_available()
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        try:
            response = await runtime.orchestrator.fetch(canonical, request_id)
        except UpstreamFailure as exc:
            runtime.mark_live_failure(exc.code)
            raise
        runtime.mark_live_success()
        response.request_id = request_id
        response.status = "partial" if response.partial else "succeeded"
        return response

    @router.get("/v1/protocol-probe", tags=["operations"], include_in_schema=False)
    async def protocol_probe(
        request: Request,
        slug: Annotated[str, Query(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,99}$")],
        member_id: Annotated[str, Query(pattern=r"^[A-Za-z0-9_-]{10,100}$")],
        section: Annotated[
            str, Query(pattern="^(experience|education|skills|certifications|languages)$")
        ],
        x_api_key: str | None = Security(API_KEY_HEADER),
    ) -> JSONResponse:
        """Controlled live protocol probe; no raw Flight data is returned."""

        _authorized_validation(x_api_key, runtime)
        contract = f"profile_{section}"
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        result = await runtime.governor.run(
            contract,
            lambda: runtime.transport.execute(contract, slug, request_id, member_id),
        )
        values = parse_section_payload(result.payload, section)
        return JSONResponse(
            {
                "evidence_class": "live",
                "operation": contract,
                "status_code": result.status_code,
                "item_count": len(values),
                "items": values,
                "diagnostics": describe_rsc_payload(result.payload),
            }
        )

    @router.post(
        "/v1/batches",
        responses={
            400: {"content": {"application/problem+json": {}}},
            401: {},
            413: {},
            422: {},
        },
        tags=["batches"],
    )
    async def create_batch(
        request: Request,
        x_api_key: str | None = Security(API_KEY_HEADER),
        text: Annotated[str | None, Query(max_length=1_000_000)] = None,
        files: list[UploadFile] | None = None,
    ) -> JSONResponse:
        _authorized(x_api_key, runtime)
        content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
        if not text and content_type != "multipart/form-data":
            # Accept pasted text as a JSON document body or as a raw
            # text/plain body, in addition to the ?text= query parameter.
            # Multipart bodies belong to the file uploads and are left alone.
            body = await request.body()
            if len(body) > 1_000_000:
                raise InvalidProfileUrl("The request body exceeds the maximum text size.")
            if content_type == "application/json" and body:
                try:
                    document = json.loads(body)
                except json.JSONDecodeError as exc:
                    raise InvalidProfileUrl("The JSON body is malformed.") from exc
                if isinstance(document, dict):
                    candidate = document.get("text")
                    text = candidate if isinstance(candidate, str) else None
            elif body:
                text = body.decode("utf-8", errors="replace")
        idempotency_key = request.headers.get("Idempotency-Key")
        batch = await batches.create(
            pasted_text=text, files=files or [], idempotency_key=idempotency_key
        )
        return JSONResponse(batch.summary(), status_code=202)

    @router.get("/v1/batches/{batch_id}", tags=["batches"])
    async def get_batch(
        batch_id: str,
        x_api_key: str | None = Security(API_KEY_HEADER),
        wait_seconds: Annotated[float | None, Query(ge=0, le=25)] = None,
    ) -> JSONResponse:
        _authorized(x_api_key, runtime)
        batch = await batches.advance(batch_id, wait_seconds)
        return JSONResponse({**batch.summary(), "report": batches.aggregate(batch.batch_id)})

    @router.get("/v1/batches/{batch_id}/profiles", tags=["batches"])
    async def get_batch_profiles(
        batch_id: str,
        x_api_key: str | None = Security(API_KEY_HEADER),
        include_responses: bool = False,
    ) -> JSONResponse:
        _authorized(x_api_key, runtime)
        await batches.advance(batch_id, 0.0)
        return JSONResponse(batches.profiles(batch_id, include_responses))

    @router.get("/v1/batches/{batch_id}/profiles/{profile_id}", tags=["batches"])
    async def get_batch_profile(
        batch_id: str,
        profile_id: str,
        x_api_key: str | None = Security(API_KEY_HEADER),
    ) -> JSONResponse:
        _authorized(x_api_key, runtime)
        await batches.advance(batch_id, 0.0)
        return JSONResponse(batches.profile(batch_id, profile_id))

    @router.get("/v1/batches/{batch_id}/report", tags=["batches"])
    async def get_batch_report(
        batch_id: str,
        x_api_key: str | None = Security(API_KEY_HEADER),
    ) -> JSONResponse:
        _authorized(x_api_key, runtime)
        await batches.advance(batch_id, 0.0)
        return JSONResponse(batches.report(batch_id))

    @router.get("/v1/batches/{batch_id}/export", tags=["batches"])
    async def export_batch(
        batch_id: str,
        x_api_key: str | None = Security(API_KEY_HEADER),
        format: Annotated[str, Query(pattern="^(json|csv|xlsx)$")] = "csv",
    ) -> Response:
        _authorized(x_api_key, runtime)
        await batches.advance(batch_id, 0.0)
        return batches.export(batch_id, format)  # type: ignore[no-any-return]

    return router


def problem_response(request: Request, exc: ProblemError) -> JSONResponse:
    headers = {"Content-Type": "application/problem+json", "Cache-Control": "no-store"}
    if exc.status == 401:
        headers["WWW-Authenticate"] = "ApiKey"
    if exc.extensions and "retry_after_seconds" in exc.extensions:
        headers["Retry-After"] = str(exc.extensions["retry_after_seconds"])
    return JSONResponse(exc.as_dict(request.url.path), status_code=exc.status, headers=headers)
