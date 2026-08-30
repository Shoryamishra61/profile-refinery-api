from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import __version__
from .api import build_router, problem_response
from .config import Settings
from .errors import InternalContractFailure, ProblemError
from .runtime import Runtime

logging.basicConfig(level=logging.INFO, format="%(message)s")


def create_app(settings: Settings | None = None, runtime: Runtime | None = None) -> FastAPI:
    active_runtime = runtime or Runtime(settings or Settings())

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await active_runtime.aclose()

    application = FastAPI(
        title="Profile Refinery API",
        summary="Registry-driven direct HTTP profile normalization research API",
        version=__version__,
        openapi_version="3.1.0",
        lifespan=lifespan,
    )
    application.state.runtime = active_runtime
    application.include_router(build_router(active_runtime))

    @application.middleware("http")
    async def assign_request_id(request: Request, call_next: Any) -> Any:
        request.state.profile_refinery_request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        return await call_next(request)

    @application.exception_handler(ProblemError)
    async def handle_problem(request: Request, exc: ProblemError) -> JSONResponse:
        response = problem_response(request, exc)
        # Correlation: every problem response carries the caller-visible request id.
        request_id = getattr(request.state, "profile_refinery_request_id", None)
        if request_id:
            body = json.loads(bytes(response.body))
            body["request_id"] = request_id
            headers = {
                k: v
                for k, v in response.headers.items()
                if k.lower() != "content-length"  # body grew; let the frame recompute it
            }
            return JSONResponse(body, status_code=response.status_code, headers=headers)
        return response

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # FastAPI's default 422 body includes the rejected raw input. That is
        # unsafe for request-scoped cookie fields, so validation diagnostics
        # expose only location, type, and message for every endpoint.
        errors = [
            {
                key: value
                for key, value in error.items()
                if key in {"loc", "msg", "type", "url"}
            }
            for error in exc.errors()
        ]
        request_id = getattr(request.state, "profile_refinery_request_id", None)
        return JSONResponse(
            {
                "code": "REQUEST_VALIDATION_ERROR",
                "title": "Request validation failed",
                "status": 422,
                "detail": "One or more request fields are invalid.",
                "errors": errors,
                "request_id": request_id,
            },
            status_code=422,
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    @application.exception_handler(ValueError)
    async def handle_contract_failure(request: Request, exc: ValueError) -> JSONResponse:
        logging.getLogger("profile_refinery_api").error(
            "internal_contract_failure path=%s exception_type=%s",
            request.url.path,
            type(exc).__name__,
        )
        return problem_response(request, InternalContractFailure())

    @application.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("profile_refinery_api").exception(
            "unexpected_failure path=%s exception_type=%s",
            request.url.path,
            type(exc).__name__,
        )
        return problem_response(request, InternalContractFailure())

    return application


app = create_app()
