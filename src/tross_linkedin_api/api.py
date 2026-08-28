from __future__ import annotations

import hmac
import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, Security
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import APIKeyHeader

from .canonicalizer import canonicalize_profile_url
from .config import AppMode
from .demo import DEMO_HTML
from .errors import CallerRateLimited, ProblemError, UnauthorizedCaller
from .models import ProfileResponse
from .rate_limit import SlidingWindowLimiter
from .runtime import Runtime

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def build_router(runtime: Runtime) -> APIRouter:
    router = APIRouter()
    limiter = SlidingWindowLimiter(
        runtime.settings.app_rate_limit_requests,
        runtime.settings.app_rate_limit_window_seconds,
    )

    @router.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(
            url="/demo" if runtime.settings.app_mode is AppMode.FIXTURE else "/docs"
        )

    if runtime.settings.app_mode is AppMode.FIXTURE:

        @router.get("/demo", include_in_schema=False)
        async def demo() -> HTMLResponse:
            return HTMLResponse(content=DEMO_HTML)


    @router.get("/healthz", tags=["operations"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/readyz", tags=["operations"])
    async def ready() -> JSONResponse:
        status = 200 if runtime.ready else 503
        return JSONResponse(
            {"status": "ready" if runtime.ready else "not_ready"}, status_code=status
        )

    @router.get(
        "/v1/profiles",
        response_model=ProfileResponse,
        responses={
            400: {"content": {"application/problem+json": {}}},
            401: {},
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
        if x_api_key is None or not any(
            hmac.compare_digest(x_api_key, expected) for expected in runtime.settings.api_key_values
        ):
            raise UnauthorizedCaller()
        retry_after = limiter.check(x_api_key)
        if retry_after is not None:
            raise CallerRateLimited(retry_after)
        canonical = canonicalize_profile_url(url)
        runtime.ensure_profile_available()
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        return await runtime.orchestrator.fetch(canonical, request_id)

    return router


def problem_response(request: Request, exc: ProblemError) -> JSONResponse:
    headers = {"Content-Type": "application/problem+json", "Cache-Control": "no-store"}
    if exc.status == 401:
        headers["WWW-Authenticate"] = "ApiKey"
    if exc.extensions and "retry_after_seconds" in exc.extensions:
        headers["Retry-After"] = str(exc.extensions["retry_after_seconds"])
    return JSONResponse(exc.as_dict(request.url.path), status_code=exc.status, headers=headers)
