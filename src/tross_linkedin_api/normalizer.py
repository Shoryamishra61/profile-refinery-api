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


def failed_field(operation: str, observed_at: datetime, status: FieldStatus) -> ProfileField[Any]:
    return field(None, operation, observed_at, status=status)


def normalize_profile(
    slug: str,
    core: dict[str, Any],
    sections: dict[str, Any],
    section_failures: dict[str, FieldStatus],
    observed_at: datetime,
) -> Profile:
    member_urn = core.get("identity", {}).get("member_urn")
    core_ref = member_urn if isinstance(member_urn, str) else None
    identity = Identity(vanity_slug=slug, member_urn=core_ref)

    def section(name: str, model: type[Any]) -> ProfileField[Any]:
        if name in section_failures:
            return failed_field(name, observed_at, section_failures[name])
        raw = sections.get(name, [])
        try:
            values = [model.model_validate(item) for item in raw]
        except (TypeError, ValidationError) as exc:
            raise ValueError(f"normalization failed for {name}") from exc
        return field(values, name, observed_at, raw_ref=core_ref)

    return Profile(
        identity=field(identity, "profile_core", observed_at, raw_ref=core_ref),
        name=field(core.get("name"), "profile_core", observed_at, raw_ref=core_ref),
        headline=field(core.get("headline"), "profile_core", observed_at, raw_ref=core_ref),
        location=field(core.get("location"), "profile_core", observed_at, raw_ref=core_ref),
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
