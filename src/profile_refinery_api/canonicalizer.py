from __future__ import annotations

import ipaddress
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import SplitResult, unquote, urlsplit

from .errors import InvalidProfileUrl

_SLUG = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,98}[A-Za-z0-9])?$")


@dataclass(frozen=True, slots=True)
class CanonicalProfile:
    input_url: str
    canonical_url: str
    slug: str


def canonicalize_profile_url(raw_url: str) -> CanonicalProfile:
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise InvalidProfileUrl("A LinkedIn profile URL is required.")
    raw = raw_url.strip()
    if len(raw) > 2048 or any(ord(char) < 32 for char in raw):
        raise InvalidProfileUrl("The profile URL is invalid or too long.")

    # The public input contract accepts the two unambiguous LinkedIn host
    # spellings without a scheme. Normalize them before the strict URL/SSRF
    # boundary so the remainder of the validation path stays identical.
    normalized_input = raw
    if raw.lower().startswith(("linkedin.com/", "www.linkedin.com/")):
        normalized_input = f"https://{raw}"

    try:
        parsed: SplitResult = urlsplit(normalized_input)
        host = parsed.hostname
        port = parsed.port
    except (UnicodeError, ValueError) as exc:
        raise InvalidProfileUrl("The profile URL is malformed.") from exc

    if parsed.scheme != "https":
        raise InvalidProfileUrl("Only HTTPS LinkedIn profile URLs are accepted.")
    if not host or parsed.username is not None or parsed.password is not None:
        raise InvalidProfileUrl("Credentials and missing hosts are not allowed in profile URLs.")
    if port not in (None, 443):
        raise InvalidProfileUrl("Non-standard ports are not allowed.")

    normalized_host = unicodedata.normalize("NFKC", host).rstrip(".").lower()
    if not host.isascii() or normalized_host != host.rstrip(".").lower():
        raise InvalidProfileUrl("Unicode or compatibility hostnames are not accepted.")
    try:
        ascii_host = normalized_host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise InvalidProfileUrl("The LinkedIn hostname is invalid.") from exc
    try:
        ipaddress.ip_address(ascii_host)
    except ValueError:
        pass
    else:
        raise InvalidProfileUrl("IP-address hosts are not accepted.")
    if ascii_host not in {"linkedin.com", "www.linkedin.com"}:
        raise InvalidProfileUrl("Only linkedin.com member profile URLs are accepted.")

    if parsed.fragment:
        raise InvalidProfileUrl("URL fragments are not accepted.")
    decoded_path = unquote(parsed.path)
    segments = [segment for segment in decoded_path.split("/") if segment]
    if len(segments) != 2 or segments[0] != "in" or not _SLUG.fullmatch(segments[1]):
        raise InvalidProfileUrl("Expected a LinkedIn member URL shaped as /in/{vanity-slug}.")
    if any(token in decoded_path for token in ("..", "\\", "@", ":")):
        raise InvalidProfileUrl("The profile path contains prohibited characters.")

    slug = segments[1]
    canonical = f"https://www.linkedin.com/in/{slug}"
    return CanonicalProfile(input_url=normalized_input, canonical_url=canonical, slug=slug)
