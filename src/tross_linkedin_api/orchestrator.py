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
from .parsers import parse_core_payload, parse_section_payload
from .transport import Transport
from .validation import SchemaValidator

# Governing spec §6/§8: the fetch plan is core-first, then only the minimum
# verified section requests needed for missing required sections, sequential
# by default. Each section is its own registry contract.
PRIMARY_OPERATION = "profile_view"
FALLBACK_OPERATION = "profile_page"
SECTION_ORDER = ("experience", "education", "skills", "certifications", "languages")
SECTION_CARD_CONSTANTS = {
    "experience": "EXPERIENCE",
    "education": "EDUCATION",
    "skills": "SKILLS",
    "certifications": "CERTIFICATIONS",
    "languages": "LANGUAGES",
}
SECTION_CONTRACTS = {name: f"profile_{name}" for name in SECTION_ORDER}
LIVE_FIXTURE_SENTINELS = (
    "SYNTHETIC-001",
    "Synthetic Systems Ltd",
    "Example Research Lab",
    "Example Institute of Technology",
)

# Section truthfulness states (governing spec P0.4) — surfaced in meta.coverage.
COVERAGE_OBSERVED = "observed"
COVERAGE_EMPTY = "observed_empty"
COVERAGE_UNAVAILABLE = "unavailable"


class ProfileOrchestrator:
    """ProfileFetchPlan: core → classify → graph → owned fields → minimum
    sequential section requests → assemble → validate.

    The governor is the single control plane for upstream operations. Tests
    may inject a transport without a governor; that path invokes the transport
    directly with no scarce-upstream policy.
    """

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
        section_failures: dict[str, str] = {}
        coverage: dict[str, str] = {}
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
        parsed = parse_core_payload(result.payload, canonical.slug)
        core = parsed["core"]
        sections = dict(parsed["sections"])
        for name, values in sections.items():
            coverage[name] = COVERAGE_EMPTY if not values else COVERAGE_OBSERVED

        # Section plan: only the minimum additional requests for missing
        # required sections, sequential, each an individually registered
        # contract. A challenge aborts the remaining plan (terminal for this
        # session plan).
        member_urn = core["identity"].get("member_urn")
        member_id = member_urn.split(":")[-1] if member_urn else None
        for name in SECTION_ORDER:
            if coverage.get(name) == COVERAGE_OBSERVED:
                continue
            contract = SECTION_CONTRACTS[name]
            if contract not in self._registry.enabled_names():
                section_failures[name] = "contract_unverified"
                coverage[name] = COVERAGE_UNAVAILABLE
                warnings.append(f"{name}: contract_unverified")
                continue
            if not member_id:
                section_failures[name] = "member_identity_unresolved"
                coverage[name] = COVERAGE_UNAVAILABLE
                warnings.append(f"{name}: member_identity_unresolved")
                continue
            attempted.append(contract)
            resource = f"{member_id}-{SECTION_CARD_CONSTANTS[name]}-en_US"
            try:
                section_result = await self._execute(contract, canonical.slug, request_id, resource)
            except CircuitOpen:
                raise
            except UpstreamChallenge:
                # Terminal for the current session plan: abort remaining
                # sections, retain what succeeded, typed failure upstream.
                section_failures[name] = "session_challenged"
                coverage[name] = COVERAGE_UNAVAILABLE
                warnings.append(f"{name}: session_challenged")
                for remaining in SECTION_ORDER[SECTION_ORDER.index(name) + 1 :]:
                    if remaining not in section_failures:
                        section_failures[remaining] = "session_challenged"
                        coverage[remaining] = COVERAGE_UNAVAILABLE
                break
            except ProfileNotFound:
                section_failures[name] = "not_found"
                coverage[name] = COVERAGE_UNAVAILABLE
                warnings.append(f"{name}: not_found")
                continue
            except UpstreamFailure as exc:
                section_failures[name] = "upstream_failed"
                coverage[name] = COVERAGE_UNAVAILABLE
                warnings.append(f"{name}: {type(exc).__name__}")
                continue
            succeeded.append(contract)
            sections[name] = parse_section_payload(section_result.payload, name)
            coverage[name] = COVERAGE_EMPTY if not sections[name] else COVERAGE_OBSERVED

        profile = normalize_profile(
            canonical.slug, core, sections, timestamp, section_failures=section_failures
        )
        response = ProfileResponse(
            input_url=canonical.input_url,
            canonical_url=canonical.canonical_url,
            observed_at=timestamp,
            partial=bool(section_failures),
            retrieval=Retrieval(
                mode="live",
                source="linkedin",
                fixture=False,
                requested_url=canonical.input_url,
                canonical_url=canonical.canonical_url,
                observed_at=timestamp,
                partial=bool(section_failures),
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
                coverage=coverage,
            ),
        )
        serialized = response.model_dump(mode="json")
        serialized_text = json.dumps(serialized, ensure_ascii=False).casefold()
        if any(sentinel.casefold() in serialized_text for sentinel in LIVE_FIXTURE_SENTINELS):
            raise LiveFixtureLeakDetected()
        self._validator.validate(serialized)
        return response
