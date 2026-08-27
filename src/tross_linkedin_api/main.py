from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import __version__
from .api import build_router, problem_response
from .config import Settings
from .errors import InternalContractFailure, ProblemError
from .runtime import Runtime

logging.basicConfig(level=logging.INFO, format="%(message)s")


def create_app(settings: Settings | None = None, runtime: Runtime | None = None) -> FastAPI:
    active_runtime = runtime or Runtime(settings or Settings())  # type: ignore[call-arg]

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await active_runtime.aclose()

    application = FastAPI(
        title="Tross LinkedIn Profile API",
        summary="Registry-driven direct HTTP profile normalization research API",
        version=__version__,
        openapi_version="3.1.0",
        lifespan=lifespan,
    )
    application.state.runtime = active_runtime
    application.include_router(build_router(active_runtime))

    @application.exception_handler(ProblemError)
    async def handle_problem(request: Request, exc: ProblemError) -> JSONResponse:
        return problem_response(request, exc)

    @application.exception_handler(ValueError)
    async def handle_contract_failure(request: Request, exc: ValueError) -> JSONResponse:
        logging.getLogger("tross_linkedin_api").error(
            "internal_contract_failure path=%s exception_type=%s",
            request.url.path,
            type(exc).__name__,
        )
        return problem_response(request, InternalContractFailure())

    @application.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("tross_linkedin_api").exception(
            "unexpected_failure path=%s exception_type=%s",
            request.url.path,
            type(exc).__name__,
        )
        return problem_response(request, InternalContractFailure())

    return application


app = create_app()
