"""Graph-based parser tests, including the live-observed dash shapes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tross_linkedin_api.errors import UpstreamOperationDrift
from tross_linkedin_api.graph import NormalizedGraph
from tross_linkedin_api.parsers import (
    parse_certifications,
    parse_core_payload,
    parse_education,
    parse_experience,
    parse_full_profile,
    parse_languages,
    parse_section_payload,
    parse_skills,
)

FIXTURES = Path("tests/fixtures/raw")


def load(name: str) -> dict[str, object]:
    value = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_core_parses_live_collection_shape() -> None:
    parsed = parse_core_payload(load("full_profile"), "test-integration-profile")
    core = parsed["core"]
    assert core["name"] == "Integration Check"
    assert core["first_name"] == "Integration"
    assert core["last_name"] == "Check"
    assert core["headline"] == "Staff Engineer at Pipeline Validation Corp"
    assert core["location"] == "Berlin, Germany"
    assert core["about"].startswith("Verifies")
    assert core["identity"]["public_identifier"] == "test-integration-profile"
    assert core["profile_image"]["url"].startswith(
        "https://media.licdn.com/dms/image/v2/TESTIMG/800_800/"
    )
    assert core["background_image"] is None


def test_experience_ownership_and_fields() -> None:
    result = parse_experience(NormalizedGraph(load("full_profile")))
    assert len(result) == 2
    assert result[0]["company_name"] == "Pipeline Validation Corp"
    assert result[0]["company_url"] == "https://www.linkedin.com/company/pipeline-validation-corp/"
    assert result[0]["is_current"] is True
    assert result[1]["is_current"] is False


def test_all_sections_parse_from_decorated_payload() -> None:
    parsed = parse_full_profile(load("full_profile"), slug="test-integration-profile")
    assert parsed["experience"][0]["title"] == "Staff Engineer"
    assert parsed["education"][0]["degree_name"] == "MSc"
    assert [s["name"] for s in parsed["skills"]] == ["HTTP protocol analysis", "Rest.li"]
    assert parsed["certifications"][0]["authority"] == "Open Verification Institute"
    assert parsed["languages"][0]["proficiency"] == "NATIVE"


def test_section_payload_ownership_excludes_unreferenced_entities() -> None:
    """profileCards: included[] may carry unrelated entities; root refs own."""
    payload = {
        "data": {
            "$type": "com.linkedin.voyager.dash.identity.profile.ProfileCard",
            "entityUrn": "urn:li:fsd_profileCard:(ACoX,SKILLS,en_US)",
            "*elements": ["urn:li:fsd_skill:(ACoX,1)"],
        },
        "included": [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Skill",
                "entityUrn": "urn:li:fsd_skill:(ACoX,1)",
                "name": {"localized": {"en_US": "Owned"}},
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Skill",
                "entityUrn": "urn:li:fsd_skill:(ACoFOREIGN,9)",
                "name": {"localized": {"en_US": "LEAK"}},
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Position",
                "entityUrn": "urn:li:fsd_position:(ACoFOREIGN,2)",
                "title": {"localized": {"en_US": "LEAK"}},
            },
        ],
    }
    skills = parse_section_payload(payload, "skills")
    assert [s["name"] for s in skills] == ["Owned"]


def test_200_with_wrong_projection_is_controlled_drift() -> None:
    """A 200 whose graph has no target Profile must fail typed, not invent."""
    with pytest.raises(UpstreamOperationDrift):
        parse_core_payload(
            {
                "included": [
                    {
                        "$type": "com.linkedin.voyager.dash.company.Company",
                        "entityUrn": "urn:li:fsd_company:1",
                    }
                ]
            },
            "someone",
        )


def test_missing_section_semantics_observed_empty() -> None:
    """A section that parsed successfully but is genuinely empty is []."""
    payload = {
        "data": {"*elements": ["urn:li:fsd_profile:u1"]},
        "included": [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": "urn:li:fsd_profile:u1",
                "publicIdentifier": "u1",
            },
        ],
    }
    parsed = parse_full_profile(payload, slug="u1")
    assert parsed["skills"] == []
    assert parsed["experience"] == []


def test_unknown_entity_types_surfaced() -> None:
    parsed = parse_full_profile(load("full_profile"), slug="test-integration-profile")
    assert parsed["core"]["unknown_entity_types"] == []


def test_legacy_localized_fixture_shapes_still_parse() -> None:
    """The older per-section fixtures use localized wrappers; still owned."""
    result = parse_education(NormalizedGraph(load("education")))
    assert result and result[0]["degree_name"] == "Bachelor of Technology"
    assert [s["name"] for s in parse_skills(NormalizedGraph(load("skills")))] == [
        "Python",
        "Distributed Systems",
    ]
    assert (
        parse_certifications(NormalizedGraph(load("certifications")))[0]["license_number"]
        == "SYNTHETIC-42"
    )
    assert (
        parse_languages(NormalizedGraph(load("languages")))[0]["proficiency"] == "FULL_PROFESSIONAL"
    )


def test_core_parses_legacy_core_fixture() -> None:
    graph = NormalizedGraph(load("profile_core"))
    from tross_linkedin_api.parsers import parse_core

    core = parse_core(graph)
    assert core["name"] == "Avery Raman"
    assert core["profile_image"]["url"].endswith("synthetic-800.jpg")
