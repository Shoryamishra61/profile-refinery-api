from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FieldStatus(StrEnum):
    PRESENT = "present"
    NOT_PROVIDED = "not_provided"
    NOT_VISIBLE_TO_VIEWER = "not_visible_to_viewer"
    NOT_AVAILABLE_FROM_ENDPOINT = "not_available_from_endpoint"
    UPSTREAM_FAILED = "upstream_failed"
    PARSER_FAILED = "parser_failed"
    STALE_OR_EXPIRED = "stale_or_expired"
    UNKNOWN = "unknown"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(StrictModel):
    source_operation: str
    observation_time: datetime
    parser_version: str
    raw_entity_reference: str | None = None
    normalization_notes: str | None = None


class ProfileField[T](StrictModel):
    value: T | None
    status: FieldStatus
    provenance: Provenance


class Identity(StrictModel):
    vanity_slug: str
    member_urn: str | None = None
    public_identifier: str | None = None


class DateValue(StrictModel):
    year: int = Field(ge=1900, le=2200)
    month: int | None = Field(default=None, ge=1, le=12)
    day: int | None = Field(default=None, ge=1, le=31)


class Experience(StrictModel):
    id: str | None = None
    title: str | None = None
    company_name: str | None = None
    company_urn: str | None = None
    company_url: str | None = None
    employment_type: str | None = None
    start_date: DateValue | None = None
    end_date: DateValue | None = None
    is_current: bool | None = None
    duration: str | None = None
    location: str | None = None
    workplace_type: str | None = None
    description: str | None = None
    group_id: str | None = None


class Education(StrictModel):
    id: str | None = None
    school_name: str | None = None
    school_urn: str | None = None
    school_url: str | None = None
    degree_name: str | None = None
    field_of_study: str | None = None
    start_date: DateValue | None = None
    end_date: DateValue | None = None
    grade: str | None = None
    activities: str | None = None
    description: str | None = None


class Skill(StrictModel):
    id: str | None = None
    name: str


class Certification(StrictModel):
    id: str | None = None
    name: str
    authority: str | None = None
    license_number: str | None = None
    credential_url: str | None = None
    start_date: DateValue | None = None
    end_date: DateValue | None = None


class Language(StrictModel):
    id: str | None = None
    name: str
    proficiency: str | None = None


class Media(StrictModel):
    url: str
    artifact_id: str | None = None
    expires_at: int | None = None


class Profile(StrictModel):
    identity: ProfileField[Identity]
    first_name: ProfileField[str]
    last_name: ProfileField[str]
    name: ProfileField[str]
    headline: ProfileField[str]
    location: ProfileField[str]
    about: ProfileField[str]
    experience: ProfileField[list[Experience]]
    education: ProfileField[list[Education]]
    skills: ProfileField[list[Skill]]
    certifications: ProfileField[list[Certification]]
    languages: ProfileField[list[Language]]
    profile_image: ProfileField[Media]
    background_image: ProfileField[Media]


class ResponseMeta(StrictModel):
    viewer_context: str
    operations_attempted: list[str]
    operations_succeeded: list[str]
    transport_strategy: str
    upstream_calls: int = Field(ge=0)
    upstream_latency_ms: float = Field(ge=0)
    warnings: list[str]
    coverage: dict[str, str] = Field(default_factory=dict)


class Retrieval(StrictModel):
    mode: Literal["live"]
    source: Literal["linkedin"]
    fixture: Literal[False]
    requested_url: str
    canonical_url: str
    observed_at: datetime
    partial: bool


class ProfileResponse(StrictModel):
    schema_version: str = "1.2.0"
    request_id: str | None = None
    status: Literal["succeeded", "partial"] = "succeeded"
    input_url: str
    canonical_url: str
    observed_at: datetime
    partial: bool
    retrieval: Retrieval
    profile: Profile
    meta: ResponseMeta


class OperationResult(StrictModel):
    operation: str
    payload: dict[str, Any]
    duration_ms: float = Field(ge=0)
    status_code: int
