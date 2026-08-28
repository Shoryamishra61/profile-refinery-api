from __future__ import annotations

from .config import AppMode, Settings
from .errors import UpstreamAuthRequired, UpstreamOperationUnavailable
from .operation_registry import OperationRegistry
from .orchestrator import ProfileOrchestrator
from .session import SessionProvider
from .transport import LinkedInTransport, Transport
from .validation import SchemaValidator


class Runtime:
    def __init__(self, settings: Settings, transport: Transport | None = None) -> None:
        self.settings = settings
        self.registry = OperationRegistry.load(settings.app_operation_registry_path)
        self.validator = SchemaValidator(settings.app_schema_path)
        self.session = SessionProvider(settings)
        if transport is not None:
            self.transport = transport
        else:
            self.transport = LinkedInTransport(settings, self.registry, self.session)
        self.orchestrator = ProfileOrchestrator(self.registry, self.transport, self.validator)

    @property
    def ready(self) -> bool:
        # Readiness means: the primary live operation is enabled AND a LinkedIn
        # session is actually configured. A live deployment without session
        # material is deliberately not ready.
        return (
            "profile_view" in self.registry.enabled_names()
            and self.settings.app_mode is AppMode.LIVE
            and self.session.available
        )

    def ensure_profile_available(self) -> None:
        if "profile_view" not in self.registry.enabled_names():
            raise UpstreamOperationUnavailable()
        if not self.session.available:
            raise UpstreamAuthRequired()

    async def aclose(self) -> None:
        await self.transport.aclose()
