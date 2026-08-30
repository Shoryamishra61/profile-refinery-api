from __future__ import annotations

import pytest

from tross_linkedin_api.canonicalizer import canonicalize_profile_url
from tross_linkedin_api.errors import InvalidProfileUrl


@pytest.mark.parametrize(
    ("url", "slug"),
    [
        ("https://linkedin.com/in/valid-slug", "valid-slug"),
        ("https://www.linkedin.com/in/a_1/", "a_1"),
        ("https://www.linkedin.com:443/in/alpha?trk=public", "alpha"),
        ("linkedin.com/in/scheme-less", "scheme-less"),
        ("www.linkedin.com/in/scheme-less-www/", "scheme-less-www"),
    ],
)
def test_accepts_only_supported_profile_shapes(url: str, slug: str) -> None:
    profile = canonicalize_profile_url(url)
    assert profile.slug == slug
    assert profile.canonical_url == f"https://www.linkedin.com/in/{slug}"
    assert profile.input_url.startswith("https://")


@pytest.mark.parametrize(
    "url",
    [
        "http://linkedin.com/in/test",
        "https://linkedin.com.evil.test/in/test",
        "https://evil.test/linkedin.com/in/test",
        "https://user:pass@linkedin.com/in/test",
        "https://127.0.0.1/in/test",
        "https://www.linkedin.com:444/in/test",
        "https://www.linkedin.com/pub/test",
        "https://www.linkedin.com/in/test/extra",
        "https://www.linkedin.com/in/../admin",
        "https://www.linkedin.com/in/test%2Fextra",
        "https://www.linkedin.com/in/test#fragment",
        "https://linkedin。com/in/test",
        "https://www.linkedin.com/in/-invalid",
        "https://www.linkedin.com/in/invalid-",
        "https://www.linkedin.com/in/a" + "x" * 100,
        "https://[::1]/in/test",
    ],
)
def test_rejects_ssrf_and_ambiguous_urls(url: str) -> None:
    with pytest.raises(InvalidProfileUrl):
        canonicalize_profile_url(url)
