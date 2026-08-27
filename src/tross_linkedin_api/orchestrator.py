from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from .canonicalizer import CanonicalProfile
from .errors import UpstreamOperationDrift
from .models import FieldStatus, ProfileResponse, ResponseMeta
from .normalizer import normalize_profile
from .operation_registry import OperationRegistry
from .parsers import parse
from .transport import Transport
from .validation import SchemaValidator

SECTION_OPERATIONS = ("experience", "education", "skills", "certifications", "languages")


class ProfileOrchestrator:
    def __init__(
        self, registry: OperationRegistry, transport: Transport, validator: SchemaValidator
    ) -> None:
        self._registry = registry
        self._transport = transport
        self._validator = validator

    async def fetch(
        self, canonical: CanonicalProfile, request_id: str, observed_at: datetime | None = None
    ) -> ProfileResponse:
        timestamp = observed_at or datetime.now(UTC)
        attempted = ["profile_core"]
        core_result = await self._transport.execute("profile_core", canonical.slug, request_id)
        core_operation = self._registry.get("profile_core")
        core = parse("profile_core", core_operation.parser, core_result.payload)
        succeeded = ["profile_core"]

        enabled_sections = [
            name for name in SECTION_OPERATIONS if name in self._registry.enabled_names()
        ]
        attempted.extend(enabled_sections)
        results = await asyncio.gather(
            *(self._fetch_section(name, canonical.slug, request_id) for name in enabled_sections),
            return_exceptions=True,
        )
        sections: dict[str, object] = {}
        failures: dict[str, FieldStatus] = {}
        warnings: list[str] = []
        latency = core_result.duration_ms
        calls = 1
        for name, result in zip(enabled_sections, results, strict=True):
            if isinstance(result, BaseException):
                parser_failed = isinstance(result, UpstreamOperationDrift)
                failures[name] = (
                    FieldStatus.PARSER_FAILED if parser_failed else FieldStatus.UPSTREAM_FAILED
                )
                warnings.append(
                    f"{name}: {'parser_or_operation_drift' if parser_failed else 'upstream_failed'}"
                )
                continue
            value, duration = result
            sections[name] = value
            latency += duration
            calls += 1
            succeeded.append(name)

        for name in SECTION_OPERATIONS:
            if name not in enabled_sections:
                failures[name] = FieldStatus.NOT_AVAILABLE_FROM_ENDPOINT
                warnings.append(f"{name}: operation_disabled")

        profile = normalize_profile(canonical.slug, core, sections, failures, timestamp)
        response = ProfileResponse(
            input_url=canonical.input_url,
            canonical_url=canonical.canonical_url,
            observed_at=timestamp,
            partial=bool(failures),
            profile=profile,
            meta=ResponseMeta(
                viewer_context="authenticated_backend_member",
                operations_attempted=attempted,
                operations_succeeded=succeeded,
                upstream_calls=calls,
                upstream_latency_ms=latency,
                warnings=warnings,
            ),
        )
        serialized = response.model_dump(mode="json")
        self._validator.validate(serialized)
        return response

    async def _fetch_section(self, name: str, slug: str, request_id: str) -> tuple[object, float]:
        result = await self._transport.execute(name, slug, request_id)
        operation = self._registry.get(name)
        return parse(name, operation.parser, result.payload), result.duration_ms
