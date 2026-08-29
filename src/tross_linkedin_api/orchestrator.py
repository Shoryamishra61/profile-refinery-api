from __future__ import annotations

import json
from datetime import UTC, datetime

from .canonicalizer import CanonicalProfile
from .errors import (
    LiveFixtureLeakDetected,
    ProfileNotFound,
    UpstreamChallenge,
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
FULL_PROFILE_OPERATION = "profile_view_full"
FALLBACK_OPERATION = "profile_page"
SECTION_CARDS = {
    "experience": "EXPERIENCE",
    "education": "EDUCATION",
    "skills": "SKILLS",
    "certifications": "CERTIFICATIONS",
    "languages": "LANGUAGES",
}
SECTION_PARSERS = {
    "experience": "experience_v1",
    "education": "education_v1",
    "skills": "skills_v1",
    "certifications": "certifications_v1",
    "languages": "languages_v1",
}
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
        self,
        semantic_name: str,
        slug: str,
        request_id: str,
        resource_id: str | None = None,
    ) -> OperationResult:
        if self._governor is None:
            return await self._transport.execute(semantic_name, slug, request_id, resource_id)
        return await self._governor.run(
            semantic_name,
            lambda: self._transport.execute(semantic_name, slug, request_id, resource_id),
        )

    async def fetch(
        self, canonical: CanonicalProfile, request_id: str, observed_at: datetime | None = None
    ) -> ProfileResponse:
        timestamp = observed_at or datetime.now(UTC)
        attempted: list[str] = []
        succeeded: list[str] = []
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
                if isinstance(exc, UpstreamChallenge):
                    # The challenge is the primary signal: a fallback attempt
                    # would only be rejected by the freshly-opened breaker and
                    # mask this code behind UPSTREAM_CIRCUIT_OPEN.
                    raise
        if result is None:
            if last_error is not None:
                raise last_error
            raise UpstreamOperationUnavailable()

        strategy = result.operation
        succeeded.append(strategy)
        parsed = parse(strategy, self._registry.get(strategy).parser, result.payload)

        # Section completion: the default projection carries the core entity
        # only. Try the full-profile decoration once (1 request for every
        # section), then per-section profileCards for whatever is missing.
        missing = [name for name in SECTION_CARDS if not parsed[name]]
        if missing:
            member_urn = parsed["core"]["identity"].get("member_urn")
            member_id = member_urn.split(":")[-1] if member_urn else None
            full_enabled = FULL_PROFILE_OPERATION in self._registry.enabled_names()
            if full_enabled and member_id:
                attempted.append(FULL_PROFILE_OPERATION)
                try:
                    full = await self._execute(
                        FULL_PROFILE_OPERATION, canonical.slug, request_id
                    )
                    full_parsed = parse(
                        FULL_PROFILE_OPERATION,
                        self._registry.get(FULL_PROFILE_OPERATION).parser,
                        full.payload,
                    )
                    for name in list(missing):
                        if full_parsed[name]:
                            parsed[name] = full_parsed[name]
                    succeeded.append(FULL_PROFILE_OPERATION)
                    missing = [name for name in SECTION_CARDS if not parsed[name]]
                except CircuitOpen:
                    raise
                except UpstreamFailure as exc:
                    warnings.append(f"{FULL_PROFILE_OPERATION}: {type(exc).__name__}")

            cards_enabled = "profile_sections" in self._registry.enabled_names()
            if missing and cards_enabled and member_id:
                for name in missing:
                    attempted.append(f"profile_sections:{name}")
                    resource = f"{member_id}-{SECTION_CARDS[name]}-en_US"
                    try:
                        section_result = await self._execute(
                            "profile_sections", canonical.slug, request_id, resource
                        )
                        parsed[name] = parse(
                            "profile_sections",
                            SECTION_PARSERS[name],
                            section_result.payload,
                        )
                        succeeded.append(f"profile_sections:{name}")
                    except CircuitOpen:
                        raise
                    except UpstreamFailure as exc:
                        warnings.append(f"profile_sections:{name}: {type(exc).__name__}")

        core = parsed["core"]
        sections = {
            name: parsed[name] for name in ("experience", "education", "skills", "certifications", "languages")
        }
        profile = normalize_profile(canonical.slug, core, sections, timestamp)
        response = ProfileResponse(
            input_url=canonical.input_url,
            canonical_url=canonical.canonical_url,
            observed_at=timestamp,
            partial=False,
            retrieval=Retrieval(
                mode="live",
                source="linkedin",
                fixture=False,
                requested_url=canonical.input_url,
                canonical_url=canonical.canonical_url,
                observed_at=timestamp,
                partial=False,
            ),
            profile=profile,
            meta=ResponseMeta(
                viewer_context="authenticated_backend_member",
                operations_attempted=attempted,
                operations_succeeded=succeeded,
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
