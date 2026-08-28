from __future__ import annotations

import json
from pathlib import Path

import pytest

from tross_linkedin_api.errors import UpstreamOperationDrift
from tross_linkedin_api.parsers import (
    parse,
    parse_certifications,
    parse_core,
    parse_education,
    parse_experience,
    parse_full_profile,
    parse_languages,
    parse_skills,
)

FIXTURES = Path("tests/fixtures/raw")


def load(name: str) -> dict[str, object]:
    value = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_core_parses_localized_name_and_largest_media() -> None:
    result = parse_core(load("profile_core"))
    assert result["name"] == "Avery Raman"
    assert result["profile_image"]["url"].endswith("synthetic-800.jpg")
    assert result["background_image"] is None


def test_core_parses_public_identifier() -> None:
    result = parse_core(load("full_profile"))
    assert result["identity"]["public_identifier"] == "test-integration-profile"


def test_experience_resolves_company_reference_and_current_role() -> None:
    result = parse_experience(load("full_profile"))
    assert len(result) == 2
    assert result[0]["company_name"] == "Pipeline Validation Corp"
    assert result[0]["company_url"] == "https://www.linkedin.com/company/pipeline-validation-corp/"
    assert result[0]["is_current"] is True
    assert result[1]["is_current"] is False


def test_full_profile_extracts_every_section_from_one_payload() -> None:
    result = parse_full_profile(load("full_profile"))
    assert result["core"]["name"] == "Integration Check"
    assert len(result["experience"]) == 2
    assert len(result["education"]) == 1
    assert len(result["skills"]) == 2
    assert len(result["certifications"]) == 1
    assert result["certifications"][0]["authority"] == "Open Verification Institute"
    assert result["languages"][0]["proficiency"] == "NATIVE"


def test_all_required_section_parsers() -> None:
    assert parse_education(load("education"))[0]["degree_name"] == "Bachelor of Technology"
    assert [item["name"] for item in parse_skills(load("skills"))] == [
        "Python",
        "Distributed Systems",
    ]
    assert parse_certifications(load("certifications"))[0]["license_number"] == "SYNTHETIC-42"
    assert parse_languages(load("languages"))[0]["proficiency"] == "FULL_PROFESSIONAL"


@pytest.mark.parametrize(
    "payload",
    [
        {"included": {}},
        {"included": [{"$type": "unknown", "entityUrn": "urn:unknown"}]},
        {"data": []},
    ],
)
def test_core_shape_drift_is_controlled(payload: dict[str, object]) -> None:
    with pytest.raises(UpstreamOperationDrift):
        parse("profile_core", "profile_core_v1", payload)


def test_unknown_entities_do_not_break_section_parser() -> None:
    assert parse_skills({"included": [{"$type": "future.Unknown", "name": "ignored"}]}) == []


def test_unknown_parser_is_controlled() -> None:
    with pytest.raises(UpstreamOperationDrift):
        parse("profile_core", "missing_parser", {})
