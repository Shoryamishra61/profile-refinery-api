"""Adversarial NormalizedGraph tests (governing spec §7 REQUIRED ADVERSARIAL TEST).

The invariant: ownership comes from references rooted in the response's data
graph — never from globally collecting entities whose $type happens to match.
"""

from __future__ import annotations

import pytest

from tross_linkedin_api.graph import (
    AmbiguousTargetProfile,
    NormalizedGraph,
    TargetProfileMissing,
)

FOREIGN_PROFILE_URN = "urn:li:fsd_profile:ACoFOREIGN"
TARGET_PROFILE_URN = "urn:li:fsd_profile:ACoTARGET"
POSITION_GROUP_URN = "urn:li:fsd_profilePositionGroup:TARGET"
POSITION_1_URN = "urn:li:fsd_position:(ACoTARGET,1)"
POSITION_2_URN = "urn:li:fsd_position:(ACoTARGET,2)"
FOREIGN_POSITION_URN = "urn:li:fsd_position:(ACoFOREIGN,9)"
CERTIFICATE_URN = "urn:li:fsd_certification:(ACoTARGET,5)"


def _profile(urn: str, public_id: str) -> dict:
    return {
        "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
        "entityUrn": urn,
        "publicIdentifier": public_id,
        "firstName": "Foreign" if urn == FOREIGN_PROFILE_URN else "Target",
    }


def adversarial_payload() -> dict:
    """Foreign Profile FIRST, foreign Position, then the target's graph.

    Root references ONLY the target profile. The target profile references
    its position group; the group references its two positions. The foreign
    Position and foreign Profile are present in included[] but unreachable
    from the root/target graph.
    """
    return {
        "data": {
            "*elements": [TARGET_PROFILE_URN],
            "$type": "com.linkedin.restli.common.CollectionResponse",
        },
        "included": [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": FOREIGN_PROFILE_URN,
                "publicIdentifier": "foreign-person",
                "firstName": "Foreign",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Position",
                "entityUrn": FOREIGN_POSITION_URN,
                "title": "FOREIGN POSITION MUST NOT LEAK",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": TARGET_PROFILE_URN,
                "publicIdentifier": "target-person",
                "firstName": "Target",
                "*positionGroups": [POSITION_GROUP_URN],
                "*certifications": [CERTIFICATE_URN],
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.ProfilePositionGroup",
                "entityUrn": POSITION_GROUP_URN,
                "*positionReferences": [POSITION_2_URN, POSITION_1_URN],
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Position",
                "entityUrn": POSITION_1_URN,
                "title": "Target Role One",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Position",
                "entityUrn": POSITION_2_URN,
                "title": "Target Role Two",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Certification",
                "entityUrn": CERTIFICATE_URN,
                "name": "Target Cert",
            },
        ],
    }


def test_target_profile_is_resolved_by_root_reference_not_first_match() -> None:
    graph = NormalizedGraph(adversarial_payload(), slug="target-person")
    profile = graph.target_profile()
    assert profile["entityUrn"] == TARGET_PROFILE_URN
    assert profile["firstName"] == "Target"


def test_foreign_position_never_becomes_target_experience() -> None:
    graph = NormalizedGraph(adversarial_payload(), slug="target-person")
    profile = graph.target_profile()
    reachable = graph.collection_elements(profile)
    positions = [e for e in reachable if e["$type"].endswith(".Position")]
    urns = {e["entityUrn"] for e in positions}
    assert urns == {POSITION_1_URN, POSITION_2_URN}
    assert FOREIGN_POSITION_URN not in urns
    assert all(e["title"] != "FOREIGN POSITION MUST NOT LEAK" for e in positions)


def test_foreign_profile_is_unreachable_from_target() -> None:
    graph = NormalizedGraph(adversarial_payload(), slug="target-person")
    reachable_urns = {e["entityUrn"] for e in graph.collection_elements(graph.target_profile())}
    assert FOREIGN_PROFILE_URN not in reachable_urns


def test_multiple_positions_at_one_company_are_both_owned() -> None:
    graph = NormalizedGraph(adversarial_payload(), slug="target-person")
    positions = [
        e
        for e in graph.collection_elements(graph.target_profile())
        if e["$type"].endswith(".Position")
    ]
    assert len(positions) == 2


def test_section_scoped_root_collection_ownership() -> None:
    """profileCards responses: ownership is root-reachable entities of type."""
    payload = {
        "data": {
            "$type": "com.linkedin.voyager.dash.identity.profile.ProfileCard",
            "entityUrn": "urn:li:fsd_profileCard:(ACoTARGET,EXPERIENCE,en_US)",
            # NOTE: the foreign position exists in included[] but the card's
            # root graph does NOT reference it - a global $type scan would
            # leak it; root-reference ownership must not.
            "*elements": [POSITION_2_URN, POSITION_1_URN],
        },
        "included": [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Position",
                "entityUrn": POSITION_1_URN,
                "title": "Target Role One",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Position",
                "entityUrn": POSITION_2_URN,
                "title": "Target Role Two",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Position",
                "entityUrn": FOREIGN_POSITION_URN,
                "title": "FOREIGN MUST NOT LEAK",
            },
        ],
    }
    graph = NormalizedGraph(payload)
    owned = graph.root_collection(".position")
    titles = sorted(e["title"] for e in owned)
    assert titles == ["Target Role One", "Target Role Two"]


def test_root_referencing_multiple_profiles_disambiguates_by_slug() -> None:
    payload = adversarial_payload()
    payload["data"]["*elements"] = [FOREIGN_PROFILE_URN, TARGET_PROFILE_URN]
    graph = NormalizedGraph(payload, slug="target-person")
    assert graph.target_urn() == TARGET_PROFILE_URN


def test_ambiguous_root_profiles_without_slug_raise() -> None:
    payload = adversarial_payload()
    payload["data"]["*elements"] = [FOREIGN_PROFILE_URN, TARGET_PROFILE_URN]
    graph = NormalizedGraph(payload)
    with pytest.raises(AmbiguousTargetProfile):
        graph.target_urn()


def test_missing_target_profile_raises_typed_error() -> None:
    payload = {"data": {"*elements": ["urn:li:fsd_company:1"]}, "included": []}
    graph = NormalizedGraph(payload)
    with pytest.raises(TargetProfileMissing):
        graph.target_profile()


def test_dangling_references_are_ignored_safely() -> None:
    payload = {
        "data": {"*elements": [TARGET_PROFILE_URN]},
        "included": [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": TARGET_PROFILE_URN,
                "publicIdentifier": "target-person",
                "*positionReferences": ["urn:li:fsd_position:(ACoTARGET,404)"],
            }
        ],
    }
    graph = NormalizedGraph(payload, slug="target-person")
    owned = graph.collection_elements(graph.target_profile())
    assert owned == []  # dangling ref resolves to nothing; no crash, no invention


def test_unknown_entity_types_are_reported_not_corrupted() -> None:
    graph = NormalizedGraph(adversarial_payload(), slug="target-person")
    unknown = graph.unknown_entity_types()
    assert unknown == []  # all types in this fixture are known
    payload = adversarial_payload()
    payload["included"].append(
        {"$type": "com.linkedin.brand.new.Thing", "entityUrn": "urn:li:brandnew:1"}
    )
    graph2 = NormalizedGraph(payload, slug="target-person")
    assert "com.linkedin.brand.new.Thing" in graph2.unknown_entity_types()
    # and normalization is unaffected
    assert graph2.target_profile()["firstName"] == "Target"


def test_cycles_in_references_terminate() -> None:
    payload = {
        "data": {"*elements": [TARGET_PROFILE_URN]},
        "included": [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": TARGET_PROFILE_URN,
                "publicIdentifier": "target-person",
                "firstName": "Target",
                "*positionGroups": [POSITION_GROUP_URN],
                "*certifications": [CERTIFICATE_URN],
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.ProfilePositionGroup",
                "entityUrn": POSITION_GROUP_URN,
                "*positionReferences": [POSITION_1_URN],
                "*parentProfile": [TARGET_PROFILE_URN],
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Position",
                "entityUrn": POSITION_1_URN,
                "*group": [POSITION_GROUP_URN],
            },
        ],
    }
    graph = NormalizedGraph(payload, slug="target-person")
    owned = graph.collection_elements(graph.target_profile())
    # The reference cycle (profile -> group -> profile) terminates: no hang,
    # no duplication, and the target's own URN may reappear harmlessly.
    assert {e["entityUrn"] for e in owned} >= {POSITION_GROUP_URN, POSITION_1_URN}
    assert len(owned) == len({e["entityUrn"] for e in owned})


def test_attributed_and_localized_text_shapes() -> None:
    from tross_linkedin_api.parsers import _localized

    assert _localized("plain") == "plain"
    assert _localized({"text": "attributed"}) == "attributed"
    assert _localized({"localized": {"en_US": "localized"}}) == "localized"
    assert _localized({"localized": {"en_US": "a", "de_DE": "b"}}) == "a"
    assert _localized({"weird": {"nested": 1}}) is None  # never str(dict)
    assert _localized(123) is None
    assert _localized(None) is None
