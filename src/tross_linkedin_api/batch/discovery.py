from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..canonicalizer import CanonicalProfile, canonicalize_profile_url
from ..errors import InvalidProfileUrl

# Person-profile URLs only. Company/job/post/feed/school surfaces are ignored:
# they are different LinkedIn entities, not member profiles.
_PROFILE_URL_RE = re.compile(
    r"(?:https?://)?(?:[a-z0-9-]+\.)*linkedin\.com/in/"
    r"(?P<slug>[A-Za-z0-9%][A-Za-z0-9%_\-]*)?(?![A-Za-z0-9%._\-])(?:/)?(\?[^\s\"'<>\)]*)?",
    re.IGNORECASE,
)
_TRAILING_PUNCTUATION = ".,;:!?)\"']}"


@dataclass(frozen=True, slots=True)
class Occurrence:
    source_type: str  # pasted_text | file
    source_name: str | None
    sheet: str | None
    row: int | None
    column: str | None
    offset: int | None
    original_text: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "sheet": self.sheet,
            "row": self.row,
            "column": self.column,
            "offset": self.offset,
            "original_text": self.original_text,
        }


@dataclass(slots=True)
class DiscoveredProfile:
    canonical: CanonicalProfile
    occurrences: list[Occurrence] = field(default_factory=list)


def _clean_slug_tail(raw: str) -> str:
    value = raw
    while value and value[-1] in _TRAILING_PUNCTUATION:
        value = value[:-1]
    return value


def discover_in_text(
    text: str,
    source_type: str,
    *,
    source_name: str | None = None,
    sheet: str | None = None,
    row: int | None = None,
    column: str | None = None,
) -> list[tuple[str, Occurrence]]:
    """Find candidate profile URLs in a text blob with observed provenance.

    Occurrences that fail canonicalization (invalid slugs) are skipped here and
    reported by the caller as skipped inputs; they never become profile jobs.
    """
    discovered: list[tuple[str, Occurrence]] = []
    for match in _PROFILE_URL_RE.finditer(text):
        raw_match = match.group(0)
        slug_group = match.group("slug") or ""
        slug = _clean_slug_tail(slug_group)
        raw_url = raw_match[: len(raw_match) - (len(slug_group) - len(slug))]
        occurrence = Occurrence(
            source_type=source_type,
            source_name=source_name,
            sheet=sheet,
            row=row,
            column=column,
            offset=match.start(),
            original_text=raw_url,
        )
        try:
            canonical = canonicalize_profile_url(_ensure_scheme(raw_url))
        except InvalidProfileUrl:
            continue
        discovered.append((canonical.canonical_url, occurrence))
    return discovered


def _ensure_scheme(raw_url: str) -> str:
    if raw_url.lower().startswith("http://") or raw_url.lower().startswith("https://"):
        return raw_url
    return f"https://{raw_url}"


def dedupe(occurrences: list[tuple[str, Occurrence]]) -> list[DiscoveredProfile]:
    ordered: dict[str, DiscoveredProfile] = {}
    for canonical_url, occurrence in occurrences:
        profile = ordered.get(canonical_url)
        if profile is None:
            try:
                canonical = canonicalize_profile_url(canonical_url)
            except InvalidProfileUrl:  # pragma: no cover - URLs came from the canonicalizer
                continue
            profile = DiscoveredProfile(canonical=canonical)
            ordered[canonical_url] = profile
        profile.occurrences.append(occurrence)
    return list(ordered.values())
