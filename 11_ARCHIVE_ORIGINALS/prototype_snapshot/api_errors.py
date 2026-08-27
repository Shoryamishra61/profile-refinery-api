from fastapi import HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any

class ProblemDetailException(Exception):
    """
    Base exception conforming to RFC 9457 Problem Details for HTTP APIs.
    """
    def __init__(
        self,
        status_code: int,
        type_uri: str,
        title: str,
        detail: str,
        instance: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.type_uri = type_uri
        self.title = title
        self.detail = detail
        self.instance = instance or ""
        self.extra = extra or {}
        super().__init__(detail)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "type": self.type_uri,
            "title": self.title,
            "status": self.status_code,
            "detail": self.detail,
        }
        if self.instance:
            payload["instance"] = self.instance
        if self.extra:
            payload["invalid_params"] = self.extra
        return payload

    def to_json_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=self.status_code,
            content=self.to_dict(),
            headers={"Content-Type": "application/problem+json"}
        )

# Concrete Subclasses
class InvalidSlugException(ProblemDetailException):
    def __init__(self, detail: str, instance: Optional[str] = None):
        super().__init__(
            status_code=400,
            type_uri="https://api.tross-profile-challenge.com/errors/invalid-slug",
            title="Invalid Profile Slug",
            detail=detail,
            instance=instance
        )

class SessionExpiredException(ProblemDetailException):
    def __init__(self, detail: str, instance: Optional[str] = None):
        super().__init__(
            status_code=401,
            type_uri="https://api.tross-profile-challenge.com/errors/session-expired",
            title="LinkedIn Session Expired",
            detail=detail,
            instance=instance
        )

class UpstreamSchemaDriftException(ProblemDetailException):
    def __init__(self, detail: str, instance: Optional[str] = None):
        super().__init__(
            status_code=502,
            type_uri="https://api.tross-profile-challenge.com/errors/upstream-schema-drift",
            title="Upstream Response Drift Detected",
            detail=detail,
            instance=instance
        )

class SecurityChallengeException(ProblemDetailException):
    def __init__(self, detail: str, instance: Optional[str] = None):
        super().__init__(
            status_code=403,
            type_uri="https://api.tross-profile-challenge.com/errors/security-challenge",
            title="Security Checkpoint Triggered",
            detail=detail,
            instance=instance
        )

class ProfileNotFoundException(ProblemDetailException):
    def __init__(self, detail: str, instance: Optional[str] = None):
        super().__init__(
            status_code=404,
            type_uri="https://api.tross-profile-challenge.com/errors/profile-not-found",
            title="Profile Not Found",
            detail=detail,
            instance=instance
        )

class RateLimitExceededException(ProblemDetailException):
    def __init__(self, detail: str, instance: Optional[str] = None):
        super().__init__(
            status_code=429,
            type_uri="https://api.tross-profile-challenge.com/errors/rate-limit-exceeded",
            title="API Rate Limit Exceeded",
            detail=detail,
            instance=instance
        )
