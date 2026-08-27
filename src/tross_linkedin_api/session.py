from __future__ import annotations

from dataclasses import dataclass

from .config import Settings


@dataclass(frozen=True, slots=True)
class SessionMaterial:
    li_at: str
    jsessionid: str
    csrf_token: str


class SessionProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._available = True

    def load(self) -> SessionMaterial:
        if not self._available:
            raise RuntimeError("session is unavailable pending manual operator action")
        li_at = self._settings.linkedin_li_at
        jsessionid = self._settings.linkedin_jsessionid
        if not li_at or not jsessionid:
            raise RuntimeError("live session material is not configured")
        jsession_value = jsessionid.get_secret_value()
        return SessionMaterial(
            li_at=li_at.get_secret_value(),
            jsessionid=jsession_value,
            csrf_token=jsession_value.strip('"'),
        )

    def fail_closed(self) -> None:
        self._available = False

    @property
    def available(self) -> bool:
        return self._available
