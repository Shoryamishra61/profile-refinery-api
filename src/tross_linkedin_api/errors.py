from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ProblemError(Exception):
    status: int
    code: str
    title: str
    detail: str
    extensions: dict[str, Any] | None = None

    def as_dict(self, instance: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": f"https://tross.dev/problems/{self.code.lower().replace('_', '-')}",
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "instance": instance,
            "code": self.code,
        }
        if self.extensions:
            body.update(self.extensions)
        return body


class InvalidProfileUrl(ProblemError):
    def __init__(self, detail: str) -> None:
        super().__init__(400, "INVALID_PROFILE_URL", "Invalid LinkedIn profile URL", detail)


class UnauthorizedCaller(ProblemError):
    def __init__(self) -> None:
        super().__init__(
            401, "UNAUTHORIZED_CALLER", "Unauthorized caller", "A valid X-API-Key is required."
        )


class CallerRateLimited(ProblemError):
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            429,
            "CALLER_RATE_LIMITED",
            "Caller rate limit exceeded",
            "The caller-side request limit has been exceeded.",
            {"retry_after_seconds": retry_after},
        )


class ProfileNotFound(ProblemError):
    def __init__(self) -> None:
        super().__init__(
            404,
            "PROFILE_NOT_FOUND",
            "Profile not found",
            "The profile was not found for this viewer.",
        )


class UpstreamFailure(ProblemError):
    pass


class UpstreamAuthRequired(UpstreamFailure):
    def __init__(self) -> None:
        super().__init__(
            503,
            "UPSTREAM_AUTH_REQUIRED",
            "Upstream authentication required",
            "Live extraction is unavailable until an authorized LinkedIn session is configured.",
        )


class UpstreamOperationUnavailable(UpstreamFailure):
    def __init__(self) -> None:
        super().__init__(
            503,
            "UPSTREAM_OPERATION_UNAVAILABLE",
            "Live operation unavailable",
            "No current live-verified core profile operation is configured.",
        )


class LiveFixtureLeakDetected(UpstreamFailure):
    def __init__(self) -> None:
        super().__init__(
            502,
            "LIVE_FIXTURE_LEAK_DETECTED",
            "Live response rejected",
            "The service refused a live response containing fixture-only sentinel data.",
        )


class UpstreamAuthExpired(UpstreamFailure):
    def __init__(self) -> None:
        super().__init__(
            503,
            "UPSTREAM_AUTH_EXPIRED",
            "Upstream session unavailable",
            "The LinkedIn session requires manual renewal.",
        )


class UpstreamChallenge(UpstreamFailure):
    def __init__(self) -> None:
        super().__init__(
            503,
            "UPSTREAM_CHALLENGE",
            "Upstream security challenge",
            "Live requests stopped; manual operator action is required.",
        )


class UpstreamRateLimited(UpstreamFailure):
    def __init__(self) -> None:
        super().__init__(
            503,
            "UPSTREAM_RATE_LIMITED",
            "Upstream rate limited",
            "LinkedIn temporarily refused the operation.",
        )


class UpstreamOperationDrift(UpstreamFailure):
    def __init__(
        self,
        operation: str,
        detail: str = "The registered upstream operation no longer matches its contract.",
    ) -> None:
        super().__init__(
            502,
            "UPSTREAM_OPERATION_DRIFT",
            "Upstream operation drift",
            detail,
            {"operation": operation},
        )


class UpstreamTimeout(UpstreamFailure):
    def __init__(self, operation: str) -> None:
        super().__init__(
            504,
            "UPSTREAM_TIMEOUT",
            "Upstream timeout",
            "The upstream operation exceeded its time budget.",
            {"operation": operation},
        )


class InternalContractFailure(ProblemError):
    def __init__(self) -> None:
        super().__init__(
            500,
            "INTERNAL_CONTRACT_FAILURE",
            "Internal response contract failure",
            "The service refused to emit a response that violates its public schema.",
        )
