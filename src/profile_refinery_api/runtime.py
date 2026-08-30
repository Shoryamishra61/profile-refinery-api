from __future__ import annotations

from .config import AppMode, Settings
from .errors import UpstreamAuthRequired, UpstreamOperationUnavailable
from .governor import BreakerState, UpstreamGovernor
from .operation_registry import OperationRegistry
from .orchestrator import ProfileOrchestrator
from .session import SessionProvider
from .transport import LinkedInTransport, Transport
from .validation import SchemaValidator


class Runtime:
    """Composition root: config → auth context → governed transport → orchestrator."""

    def __init__(self, settings: Settings, transport: Transport | None = None) -> None:
        self.settings = settings
        self.registry = OperationRegistry.load(settings.app_operation_registry_path)
        self.validator = SchemaValidator(settings.app_schema_path)
        # Authentication context provider: the only component aware of raw
        # session material. Extraction code receives contexts through it.
        self.session = SessionProvider(settings)
        if transport is not None:
            self.transport = transport
        else:
            self.transport = LinkedInTransport(settings, self.registry, self.session)
        # Control plane: every LinkedIn operation is governed.
        self.governor = UpstreamGovernor(
            concurrency=settings.app_upstream_concurrency,
            bucket_capacity=settings.app_upstream_bucket_capacity,
            refill_per_minute=settings.app_upstream_refill_per_minute,
            max_retries=settings.app_upstream_retries,
            breaker_failure_threshold=settings.app_breaker_failure_threshold,
            breaker_cooldown_seconds=settings.app_breaker_cooldown_seconds,
        )
        self.orchestrator = ProfileOrchestrator(
            self.registry, self.transport, self.validator, self.governor
        )
        self._live_extraction_confirmed = False
        self._live_failure_code: str | None = None

    @property
    def ready(self) -> bool:
        return (
            "profile_view" in self.registry.enabled_names()
            and self.settings.app_mode is AppMode.LIVE
            and self.session.available
            and self._live_extraction_confirmed
            and self._live_failure_code is None
            and self.governor.breaker.state is BreakerState.CLOSED
        )

    def extraction_capability(self) -> dict[str, object]:
        """Separate capability signal: readiness ≠ upstream capacity."""
        if not self.session.available:
            state = "UNAVAILABLE"
            detail = "No LinkedIn session configured."
        elif self._live_failure_code is not None:
            state = "UNUSABLE"
            detail = f"The latest live profile extraction failed: {self._live_failure_code}."
        else:
            breaker = self.governor.breaker
            state = breaker.state.value
            if state == "OPEN":
                detail = "Circuit open after challenge/failures; cooldown in progress."
            elif state == "HALF_OPEN":
                detail = "Controlled probe in progress after cooldown."
            elif not self._live_extraction_confirmed:
                state = "UNVERIFIED"
                detail = "No successful live profile extraction has been observed in this process."
            else:
                detail = "Extraction available under rate budget."
        return {
            "state": state,
            "detail": detail,
            "governor": self.governor.observe(),
        }

    def mark_live_success(self) -> None:
        self._live_extraction_confirmed = True
        self._live_failure_code = None

    def mark_live_failure(self, code: str) -> None:
        self._live_extraction_confirmed = False
        self._live_failure_code = code

    def ensure_profile_available(self) -> None:
        if "profile_view" not in self.registry.enabled_names():
            raise UpstreamOperationUnavailable()
        if not self.session.available:
            raise UpstreamAuthRequired()

    async def aclose(self) -> None:
        await self.transport.aclose()
