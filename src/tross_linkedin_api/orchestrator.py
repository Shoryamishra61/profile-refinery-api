from __future__ import annotations

import json
from datetime import UTC, datetime

from .canonicalizer import CanonicalProfile
from .errors import (
    LiveFixtureLeakDetected,
    ProfileNotFound,
    UpstreamFailure,
    UpstreamOperationUnavailable,
)
from .governor import CircuitOpen, UpstreamGovernor
from .models import OperationResult, ProfileResponse, ResponseMeta, Retrieval
from .normalizer import normalize_profile
from .operation_registry import OperationRegistry
from .parsers import parse
from .transport import Transport
from .validation import SchemaValidator

PRIMARY_OPERATION = "profile_view"
FALLBACK_OPERATION = "profile_page"
LIVE_FIXTURE_SENTINELS = (
    "SYNTHETIC-001",
    "Synthetic Systems Ltd",
    "Example Research Lab",
    "Example Institute of Technology",
)


class ProfileOrchestrator:
    def __init__(
        self,
        registry: OperationRegistry,
        transport: Transport,
        validator: SchemaValidator,
        governor: UpstreamGovernor | None = None,
    ) -> None:
        self._registry = registry
        self._transport = transport
        self._validator = validator
        # The governor is the single control plane for upstream operations.
        # Tests may inject a transport without a governor; that path invokes
        # the transport directly with no scarce-upstream policy.
        self._governor = governor

    async def _execute(
        self, semantic_name: str, slug: str, request_id: str
    ) -> OperationResult:
        if self._governor is None:
            return await self._transport.execute(semantic_name, slug, request_id)
        return await self._governor.run(
            semantic_name, lambda: self._transport.execute(semantic_name, slug, request_id)
        )

    async def fetch(
        self, canonical: CanonicalProfile, request_id: str, observed_at: datetime | None = None
    ) -> ProfileResponse:
        timestamp = observed_at or datetime.now(UTC)
        attempted: list[str] = []
        warnings: list[str] = []
        last_error: UpstreamFailure | None = None

        result = None
        for semantic_name in (PRIMARY_OPERATION, FALLBACK_OPERATION):
            if semantic_name not in self._registry.enabled_names():
                continue
            attempted.append(semantic_name)
            try:
                result = await self._execute(semantic_name, canonical.slug, request_id)
                break
            except ProfileNotFound:
                raise
            except CircuitOpen:
                # Breaker policy is global: when the circuit opens, ALL
                # extraction stops — including fallback attempts.
                raise
            except UpstreamFailure as exc:
                last_error = exc
                warnings.append(f"{semantic_name}: {type(exc).__name__}")
        if result is None:
            if last_error is not None:
                raise last_error
            raise UpstreamOperationUnavailable()

        strategy = result.operation
        parsed = parse(strategy, self._registry.get(strategy).parser, result.payload)

        core = parsed["core"]
        sections = {
            name: parsed[name] for name in ("experience", "education", "skills", "certifications", "languages")
        }
        profile = normalize_profile(canonical.slug, core, sections, timestamp)
        partial = False
        response = ProfileResponse(
            input_url=canonical.input_url,
            canonical_url=canonical.canonical_url,
            observed_at=timestamp,
            partial=partial,
            retrieval=Retrieval(
                mode="live",
                source="linkedin",
                fixture=False,
                requested_url=canonical.input_url,
                canonical_url=canonical.canonical_url,
                observed_at=timestamp,
                partial=partial,
            ),
            profile=profile,
            meta=ResponseMeta(
                viewer_context="authenticated_backend_member",
                operations_attempted=attempted,
                operations_succeeded=[strategy],
                transport_strategy=strategy,
                upstream_calls=self._transport.call_count,
                upstream_latency_ms=result.duration_ms,
                warnings=warnings,
            ),
        )
        serialized = response.model_dump(mode="json")
        serialized_text = json.dumps(serialized, ensure_ascii=False).casefold()
        if any(sentinel.casefold() in serialized_text for sentinel in LIVE_FIXTURE_SENTINELS):
            raise LiveFixtureLeakDetected()
        self._validator.validate(serialized)
        return response
