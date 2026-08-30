from __future__ import annotations

import json
from hashlib import sha256

import pytest

from profile_refinery_api.errors import UpstreamOperationDrift
from profile_refinery_api.rsc import (
    FlightDocument,
    build_profile_activity_body,
    build_profile_component_body,
    parse_rsc_core_payload,
    parse_rsc_section_payload,
)


def _record(record_id: str, value: object) -> str:
    return f"{record_id}:{json.dumps(value, separators=(',', ':'))}"


def _element(props: dict[str, object]) -> list[object]:
    return ["$", "section", None, props]


def test_component_body_reproduces_captured_contract() -> None:
    body = build_profile_component_body(
        "williamhgates", "ACoAAA8BYqEBCGLg_vT_ca6mMEqkpp9nVffJ3hc"
    )
    encoded = json.dumps(body, separators=(",", ":")).encode()
    assert len(encoded) == 3073
    assert sha256(encoded).hexdigest() == (
        "0c08dd2c7ea9427cfa30ad08c8f2a1bf2a1536ef4acc168521371f58ebf09542"
    )


def test_activity_body_reproduces_captured_contract() -> None:
    assert build_profile_activity_body("williamhgates") == {
        "clientArguments": {
            "payload": {"isSelfView": False, "vanityName": "williamhgates"},
            "states": [],
            "requestMetadata": {"$type": "proto.sdui.common.RequestMetadata"},
            "screenId": "com.linkedin.sdui.flagshipnav.home.Home",
            "knownTemplateIds": [],
        }
    }


def test_activity_core_uses_prioritized_target_and_semantic_states() -> None:
    def set_state(state_id: str, value: dict[str, object]) -> dict[str, object]:
        return {
            "$type": "proto.sdui.actions.core.SetState",
            "value": {
                "state": {
                    "key": {
                        "key": {
                            "value": {"$case": "id", "id": state_id},
                        },
                        "namespace": "LoadingNamespace",
                    },
                    "value": value,
                }
            },
        }

    text = _record(
        "0",
        {
            "resolver": {"prioritizedProfileId": "ACoTARGET"},
            "action": {
                "actions": [
                    set_state(
                        "profile_name_loading_state",
                        {"$case": "stringValue", "stringValue": "Captured Person"},
                    ),
                    set_state(
                        "profile_headline_loading_state",
                        {"$case": "stringValue", "stringValue": "Protocol Engineer"},
                    ),
                    set_state(
                        "profile_photo_loading_state",
                        {
                            "$case": "imageAssetValue",
                            "imageAssetValue": {
                                "source": {
                                    "renderPayload": {
                                        "rootUrl": "https://media.licdn.com/root-",
                                        "imageRenditions": [
                                            {"width": 100, "suffixUrl": "small"},
                                            {"width": 800, "suffixUrl": "large"},
                                        ],
                                    }
                                }
                            },
                        },
                    ),
                ]
            },
        },
    )
    result = parse_rsc_core_payload({"flight": text}, "captured-person")
    assert result["identity"] == {
        "member_urn": "urn:li:fsd_profile:ACoTARGET",
        "public_identifier": "captured-person",
    }
    assert result["name"] == "Captured Person"
    assert result["headline"] == "Protocol Engineer"
    assert result["profile_image"] == {"url": "https://media.licdn.com/root-large"}


def test_flight_document_resolves_lazy_model_references() -> None:
    text = "\n".join(
        [
            '1:I["module",[],"default"]',
            _record("0", {"children": "$L2"}),
            _record("2", {"children": ["Captured text"]}),
        ]
    )
    document = FlightDocument.parse(text)
    assert document.resolve(document.records["0"]) == {"children": {"children": ["Captured text"]}}


def test_experience_uses_semantic_collection_items_not_global_text() -> None:
    text = "\n".join(
        [
            _record(
                "0",
                _element(
                    {
                        "viewTrackingSpecs": {"viewName": "profile-card-experience"},
                        "children": "$L1",
                    }
                ),
            ),
            _record(
                "1",
                {
                    "initialItems": [
                        {"semanticId": "captured-exp-1", "item": "$L2"},
                    ]
                },
            ),
            _record(
                "2",
                _element(
                    {
                        "children": [
                            "Senior Engineer",
                            "Captured Systems · Full-time",
                            "Jan 2020 - Present · 6 yrs 8 mos",
                            "New Delhi, India · Remote",
                            "Built deterministic systems.",
                        ],
                        "action": {"url": "https://www.linkedin.com/company/captured-systems/"},
                    }
                ),
            ),
            _record("3", {"children": ["Foreign profile text"]}),
        ]
    )
    result = parse_rsc_section_payload({"flight": text}, "experience")
    assert result == [
        {
            "id": "captured-exp-1",
            "title": "Senior Engineer",
            "company_name": "Captured Systems",
            "company_urn": None,
            "company_url": "https://www.linkedin.com/company/captured-systems/",
            "employment_type": "Full-time",
            "start_date": {"year": 2020, "month": 1},
            "end_date": None,
            "is_current": True,
            "duration": "6 yrs 8 mos",
            "location": "New Delhi, India",
            "workplace_type": "Remote",
            "description": "Built deterministic systems.",
            "group_id": None,
        }
    ]


def test_experience_fallback_preserves_upstream_order() -> None:
    text = _record(
        "0",
        _element(
            {
                "viewTrackingSpecs": {"viewName": "profile-card-experience"},
                "children": [
                    _element(
                        {
                            "children": [
                                "First Role",
                                "First Company · Full-time",
                                "Jan 2024 - Present · 2 yrs",
                            ]
                        }
                    ),
                    _element(
                        {
                            "children": [
                                "Second Role",
                                "Second Company · Internship",
                                "Jan 2023 - Dec 2023 · 1 yr",
                            ]
                        }
                    ),
                ],
            }
        ),
    )
    result = parse_rsc_section_payload({"flight": text}, "experience")
    assert [item["title"] for item in result] == ["First Role", "Second Role"]


def test_part_one_decodes_education_and_certification_roots_independently() -> None:
    text = "\n".join(
        [
            _record(
                "0",
                _element(
                    {
                        "viewTrackingSpecs": {"viewName": "profile-card-education"},
                        "children": "$L1",
                    }
                ),
            ),
            _record(
                "1",
                {
                    "initialItems": [
                        {"semanticId": "captured-edu-1", "item": "$L2"},
                    ]
                },
            ),
            _record(
                "2",
                _element(
                    {
                        "children": [
                            "Captured University",
                            "Bachelor of Technology, Computer Science",
                            "2021 – 2025",
                            "Grade: A",
                            "Activities and societies: Computing Club",
                            "Built a research project.",
                        ],
                        "action": {"url": "https://www.linkedin.com/school/captured-university/"},
                    }
                ),
            ),
            _record(
                "a",
                _element(
                    {
                        "viewTrackingSpecs": {"viewName": "profile-card-certifications"},
                        "children": "$Lb",
                    }
                ),
            ),
            _record(
                "b",
                {
                    "initialItems": [
                        {"semanticId": "captured-cert-1", "item": "$Lc"},
                    ]
                },
            ),
            _record(
                "c",
                _element(
                    {
                        "children": [
                            "Certified Protocol Engineer",
                            "Captured Authority",
                            "Issued Jul 2024 · Expires Aug 2027",
                            "Credential ID CAPTURED-1",
                        ],
                        "action": {"url": "https://credentials.example/captured-1"},
                    }
                ),
            ),
        ]
    )
    education = parse_rsc_section_payload({"flight": text}, "education")
    certifications = parse_rsc_section_payload({"flight": text}, "certifications")
    assert education[0] == {
        "id": "captured-edu-1",
        "school_name": "Captured University",
        "school_urn": None,
        "school_url": "https://www.linkedin.com/school/captured-university/",
        "degree_name": "Bachelor of Technology",
        "field_of_study": "Computer Science",
        "start_date": {"year": 2021},
        "end_date": {"year": 2025},
        "grade": "A",
        "activities": "Computing Club",
        "description": "Built a research project.",
    }
    assert certifications[0] == {
        "id": "captured-cert-1",
        "name": "Certified Protocol Engineer",
        "authority": "Captured Authority",
        "license_number": "CAPTURED-1",
        "credential_url": "https://credentials.example/captured-1",
        "start_date": {"year": 2024, "month": 7},
        "end_date": {"year": 2027, "month": 8},
    }


def test_current_lockup_variant_decodes_without_initial_items() -> None:
    text = "\n".join(
        [
            _record(
                "0",
                _element(
                    {
                        "viewTrackingSpecs": {"viewName": "profile-card-education"},
                        "children": "$L1",
                    }
                ),
            ),
            _record(
                "1",
                _element(
                    {
                        "viewTrackingSpecs": {"viewName": "education-lockup-view"},
                        "componentKey": "captured-education-lockup",
                        "children": [
                            "Captured Institute",
                            "BTech, Computer Science",
                            "Jun 2023 – May 2027",
                        ],
                    }
                ),
            ),
            _record(
                "a",
                _element(
                    {
                        "viewTrackingSpecs": {
                            "viewName": "profile-card-licenses-and-certifications"
                        },
                        "children": "$Lb",
                    }
                ),
            ),
            _record(
                "b",
                _element(
                    {
                        "viewTrackingSpecs": {
                            "viewName": "license-certifications-lockup-view"
                        },
                        "componentKey": "captured-certification-lockup",
                        "children": [
                            "Captured Associate",
                            "Captured Issuer",
                            "Issued Jul 2026",
                        ],
                    }
                ),
            ),
        ]
    )
    assert parse_rsc_section_payload({"flight": text}, "education")[0]["school_name"] == (
        "Captured Institute"
    )
    assert parse_rsc_section_payload({"flight": text}, "certifications")[0]["name"] == (
        "Captured Associate"
    )


def test_skills_and_languages_use_section_local_semantic_content() -> None:
    skills = _record(
        "0",
        _element(
            {
                "viewTrackingSpecs": {"viewName": "profile-card-skills"},
                "children": [
                    "Skills",
                    "com.linkedin.sdui.profile.skill(ACoSANITIZED, 17)",
                    "Protocol Analysis",
                    "com.linkedin.sdui.profile.skill(ACoSANITIZED, 18)",
                    "Data Modeling",
                ],
            }
        ),
    )
    languages = _record(
        "0",
        _element(
            {
                "viewTrackingSpecs": {"viewName": "profile-card-languages"},
                "children": [
                    "Languages",
                    "English",
                    "Native or bilingual proficiency",
                    "Spanish",
                    "Limited working proficiency",
                ],
            }
        ),
    )
    assert parse_rsc_section_payload({"flight": skills}, "skills") == [
        {
            "id": "com.linkedin.sdui.profile.skill(ACoSANITIZED, 17)",
            "name": "Protocol Analysis",
        },
        {
            "id": "com.linkedin.sdui.profile.skill(ACoSANITIZED, 18)",
            "name": "Data Modeling",
        },
    ]
    assert parse_rsc_section_payload({"flight": languages}, "languages") == [
        {"id": None, "name": "English", "proficiency": "Native or bilingual proficiency"},
        {"id": None, "name": "Spanish", "proficiency": "Limited working proficiency"},
    ]


def test_known_section_marker_without_section_root_is_observed_empty() -> None:
    text = _record(
        "0",
        {"children": ["com.linkedin.sdui.profile.card.refACoSANITIZEDLanguageTopLevel"]},
    )
    assert parse_rsc_section_payload({"flight": text}, "languages") == []


def test_missing_section_identity_is_protocol_drift() -> None:
    with pytest.raises(UpstreamOperationDrift):
        parse_rsc_section_payload({"flight": _record("0", {"children": ["unrelated"]})}, "skills")
