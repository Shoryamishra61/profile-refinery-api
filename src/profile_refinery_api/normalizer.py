from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ValidationError

from .models import (
    Certification,
    Education,
    Experience,
    FieldStatus,
    Identity,
    Language,
    Media,
    Profile,
    ProfileField,
    Provenance,
    Skill,
)
from .parsers import PARSER_VERSION


def provenance(operation: str, observed_at: datetime, raw_ref: str | None = None) -> Provenance:
    return Provenance(
        source_operation=operation,
        observation_time=observed_at,
        parser_version=PARSER_VERSION,
        raw_entity_reference=raw_ref,
    )


def field(
    value: Any,
    operation: str,
    observed_at: datetime,
    *,
    status: FieldStatus | None = None,
    raw_ref: str | None = None,
) -> ProfileField[Any]:
    resolved = status or (FieldStatus.PRESENT if value is not None else FieldStatus.NOT_PROVIDED)
    return ProfileField(
        value=value, status=resolved, provenance=provenance(operation, observed_at, raw_ref)
    )


def normalize_profile(
    slug: str,
    core: dict[str, Any],
    sections: dict[str, Any],
    observed_at: datetime,
    section_failures: dict[str, str] | None = None,
) -> Profile:
    """Deterministically normalize a parsed profile payload.

    Section truthfulness (governing spec P0.4): a section that was retrieved
    and is genuinely empty normalizes to ``[]`` with status ``present``; a
    section whose retrieval failed is ``null`` with an explicit failure
    status. There is no third "guessed" state.
    """
    identity_data = core.get("identity", {})
    member_urn = identity_data.get("member_urn")
    core_ref = member_urn if isinstance(member_urn, str) else None
    identity = Identity(
        vanity_slug=slug,
        member_urn=core_ref,
        public_identifier=identity_data.get("public_identifier"),
    )

    failures = section_failures or {}
    field_sources = core.get("_field_sources", {})

    def core_source(name: str) -> str:
        source = field_sources.get(name) if isinstance(field_sources, dict) else None
        return source if isinstance(source, str) else "profile_core"

    def section(name: str, model: type[Any]) -> ProfileField[Any]:
        if name in failures:
            status = {
                "parser_failed": FieldStatus.PARSER_FAILED,
                "upstream_failed": FieldStatus.UPSTREAM_FAILED,
                "not_found": FieldStatus.UPSTREAM_FAILED,
                "session_challenged": FieldStatus.UPSTREAM_FAILED,
            }.get(failures[name], FieldStatus.NOT_AVAILABLE_FROM_ENDPOINT)
            return field(None, name, observed_at, status=status, raw_ref=core_ref)
        raw = sections.get(name, [])
        try:
            values = [model.model_validate(item) for item in raw]
        except (TypeError, ValidationError) as exc:
            raise ValueError(f"normalization failed for {name}") from exc
        return field(values, name, observed_at, raw_ref=core_ref)

    return Profile(
        identity=field(identity, "profile_core", observed_at, raw_ref=core_ref),
        first_name=field(core.get("first_name"), "profile_core", observed_at, raw_ref=core_ref),
        last_name=field(core.get("last_name"), "profile_core", observed_at, raw_ref=core_ref),
        name=field(core.get("name"), "profile_core", observed_at, raw_ref=core_ref),
        headline=field(core.get("headline"), "profile_core", observed_at, raw_ref=core_ref),
        location=field(
            core.get("location"), core_source("location"), observed_at, raw_ref=core_ref
        ),
        about=field(core.get("about"), "profile_core", observed_at, raw_ref=core_ref),
        experience=section("experience", Experience),
        education=section("education", Education),
        skills=section("skills", Skill),
        certifications=section("certifications", Certification),
        languages=section("languages", Language),
        profile_image=field(
            Media.model_validate(core["profile_image"]) if core.get("profile_image") else None,
            "profile_core",
            observed_at,
            raw_ref=core_ref,
        ),
        background_image=field(
            Media.model_validate(core["background_image"])
            if core.get("background_image")
            else None,
            "profile_core",
            observed_at,
            raw_ref=core_ref,
        ),
    )
