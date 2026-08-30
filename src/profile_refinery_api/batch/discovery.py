from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import unquote, urlsplit

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
_POST_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/"
    r"(?:posts/[A-Za-z0-9%._\-]+|feed/update/urn:li:(?:activity|ugcPost|share):[0-9]+)"
    r"(?:/)?(?:\?[^\s\"'<>\)]*)?",
    re.IGNORECASE,
)


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


@dataclass(slots=True)
class DiscoveredPost:
    canonical_url: str
    activity_urn: str | None = None
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


def canonicalize_post_url(raw_url: str) -> tuple[str, str | None]:
    """Canonicalize supported LinkedIn post URLs without inferring an author."""

    parsed = urlsplit(_ensure_scheme(raw_url.strip().rstrip(_TRAILING_PUNCTUATION)))
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").lower() not in {"linkedin.com", "www.linkedin.com"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or parsed.fragment
    ):
        raise InvalidProfileUrl("Unsupported LinkedIn post URL.")
    try:
        path = unquote(parsed.path)
    except ValueError as exc:
        raise InvalidProfileUrl("Malformed LinkedIn post URL encoding.") from exc
    if ".." in path or "\\" in path or "@" in path:
        raise InvalidProfileUrl("Unsafe LinkedIn post path.")
    normalized_path = path.rstrip("/")
    activity_urn: str | None = None
    if re.fullmatch(r"/posts/[A-Za-z0-9._%\-]+", normalized_path):
        pass
    else:
        match = re.fullmatch(
            r"/feed/update/(urn:li:(?:activity|ugcPost|share):[0-9]+)",
            normalized_path,
            re.IGNORECASE,
        )
        if match is None:
            raise InvalidProfileUrl("Unsupported LinkedIn post URL.")
        activity_urn = match.group(1)
    return f"https://www.linkedin.com{normalized_path}", activity_urn


def discover_posts_in_text(
    text: str,
    source_type: str,
    *,
    source_name: str | None = None,
    sheet: str | None = None,
    row: int | None = None,
    column: str | None = None,
) -> list[tuple[str, str | None, Occurrence]]:
    discovered: list[tuple[str, str | None, Occurrence]] = []
    for match in _POST_URL_RE.finditer(text):
        raw_url = match.group(0).rstrip(_TRAILING_PUNCTUATION)
        try:
            canonical_url, activity_urn = canonicalize_post_url(raw_url)
        except InvalidProfileUrl:
            continue
        discovered.append(
            (
                canonical_url,
                activity_urn,
                Occurrence(
                    source_type=source_type,
                    source_name=source_name,
                    sheet=sheet,
                    row=row,
                    column=column,
                    offset=match.start(),
                    original_text=raw_url,
                ),
            )
        )
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


def dedupe_posts(
    occurrences: list[tuple[str, str | None, Occurrence]],
) -> list[DiscoveredPost]:
    ordered: dict[str, DiscoveredPost] = {}
    for canonical_url, activity_urn, occurrence in occurrences:
        post = ordered.get(canonical_url)
        if post is None:
            post = DiscoveredPost(canonical_url=canonical_url, activity_urn=activity_urn)
            ordered[canonical_url] = post
        post.occurrences.append(occurrence)
    return list(ordered.values())
