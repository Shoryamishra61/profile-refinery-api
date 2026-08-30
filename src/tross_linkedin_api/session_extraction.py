from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator

from .models import ProfileResponse, StrictModel

ProfileUrls = Annotated[list[str], Field(min_length=1, max_length=10)]


class BrowserSessionInput(StrictModel):
    """Request-scoped LinkedIn session material.

    Values are represented as ``SecretStr`` so validation errors and model
    representations cannot accidentally disclose them. The API never
    serializes this model in a response or writes it to durable storage.
    """

    li_at: SecretStr = Field(min_length=20, max_length=4096)
    jsessionid: SecretStr = Field(min_length=5, max_length=1024)
    companion_cookies: SecretStr | None = Field(default=None, max_length=16_384)
    user_agent: str = Field(min_length=10, max_length=1024)
    accept_language: str = Field(default="en-US,en;q=0.9", min_length=2, max_length=256)

    @field_validator("li_at", "jsessionid", "companion_cookies")
    @classmethod
    def reject_cookie_control_characters(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and any(char in value.get_secret_value() for char in "\r\n\0"):
            raise ValueError("Cookie values cannot contain control characters.")
        return value

    @field_validator("user_agent", "accept_language")
    @classmethod
    def reject_header_control_characters(cls, value: str) -> str:
        if any(char in value for char in "\r\n\0"):
            raise ValueError("Header values cannot contain control characters.")
        return value.strip()


class SessionExtractionRequest(StrictModel):
    urls: ProfileUrls
    session: BrowserSessionInput


class ExtractionProblem(StrictModel):
    code: str
    title: str
    detail: str
    status: int
    retry_after_seconds: int | None = None


class SessionExtractionResult(StrictModel):
    input_url: str
    status: Literal["succeeded", "partial", "failed", "skipped"]
    profile: ProfileResponse | None = None
    error: ExtractionProblem | None = None


class SessionExtractionResponse(StrictModel):
    request_id: str
    credential_handling: Literal["request_memory_only"] = "request_memory_only"
    results: list[SessionExtractionResult]
