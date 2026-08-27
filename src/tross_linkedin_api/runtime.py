from __future__ import annotations

from .config import AppMode, Settings
from .operation_registry import OperationRegistry
from .orchestrator import ProfileOrchestrator
from .session import SessionProvider
from .transport import FixtureTransport, LinkedInTransport, Transport
from .validation import SchemaValidator


class Runtime:
    def __init__(self, settings: Settings, transport: Transport | None = None) -> None:
        self.settings = settings
        self.registry = OperationRegistry.load(
            settings.app_operation_registry_path, settings.app_mode
        )
        self.validator = SchemaValidator(settings.app_schema_path)
        self.session = SessionProvider(settings)
        if transport is not None:
            self.transport = transport
        elif settings.app_mode is AppMode.FIXTURE:
            self.transport = FixtureTransport(self.registry, settings.app_fixture_root)
        else:
            self.transport = LinkedInTransport(settings, self.registry, self.session)
        self.orchestrator = ProfileOrchestrator(self.registry, self.transport, self.validator)

    @property
    def ready(self) -> bool:
        core_enabled = "profile_core" in self.registry.enabled_names()
        return core_enabled and (
            self.settings.app_mode is AppMode.FIXTURE or self.session.available
        )

    async def aclose(self) -> None:
        await self.transport.aclose()
