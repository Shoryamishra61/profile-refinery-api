"""Upstream shape → typed internal dicts.

Parsers consume a :class:`~profile_refinery_api.graph.NormalizedGraph` and never
perform I/O (invariant I1/I3). Entity ownership is decided by the graph —
target-reference traversal for profile payloads, root-reference traversal for
section (profileCards) payloads — never by global ``$type`` scans of
``included[]``.

Text normalization handles the observed shapes:

* plain string
* localized wrapper ``{"localized": {"en_US": ...}}``
* attributed wrapper ``{"text": ...}``

Unknown complex objects yield ``None`` plus a warning at the orchestrator
layer — never ``str(dict)`` in user-visible content.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .errors import UpstreamOperationDrift
from .graph import (
    AmbiguousTargetProfile,
    NormalizedGraph,
    TargetProfileMissing,
)
from .rsc import (
    RSC_PARSER_VERSION,
    parse_rsc_core_payload,
    parse_rsc_page_core_payload,
    parse_rsc_section_payload,
)

PARSER_VERSION = f"normalized-graph-v2+{RSC_PARSER_VERSION}"

SECTION_ENTITY_SUFFIXES = {
    "experience": ".position",
    "education": ".education",
    "skills": ".skill",
    "certifications": ".certification",
    "languages": ".language",
}


def _objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


def _localized(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if not isinstance(value, dict):
        return None
    if isinstance(value.get("text"), str):
        return value["text"].strip() or None
    localized = value.get("localized")
    if isinstance(localized, dict):
        values = [
            item.strip() for item in localized.values() if isinstance(item, str) and item.strip()
        ]
        return values[0] if values else None
    return None


def _date(value: Any) -> dict[str, int] | None:
    if not isinstance(value, dict) or not isinstance(value.get("year"), int):
        return None
    result = {"year": value["year"]}
    for key in ("month", "day"):
        if isinstance(value.get(key), int):
            result[key] = value[key]
    return result


def _media(value: Any) -> dict[str, Any] | None:
    """Extract the largest usable image from dash/legacy media shapes.

    Real dash shape (live-verified): profilePicture.displayImage.vectorImage
    with artifacts carrying fileIdentifyingUrlPathSegment plus a
    digitalmediaAsset urn; the public CDN url is
    https://media.licdn.com/dms/image/v2/{assetId}/{pathSegment}. Legacy
    fixtures expose ready-made downloadUrl nodes; both supported.
    """
    best_width = -1
    best_built: dict[str, Any] | None = None
    for node in _objects(value):
        if not isinstance(node, dict):
            continue
        artifacts = node.get("artifacts")
        asset = node.get("digitalmediaAsset")
        if isinstance(artifacts, list) and isinstance(asset, str):
            asset_id = asset.split(":")[-1]
            for artifact in artifacts:
                if not isinstance(artifact, dict):
                    continue
                segment = artifact.get("fileIdentifyingUrlPathSegment")
                raw_width = artifact.get("width")
                width = raw_width if isinstance(raw_width, int) else 0
                if isinstance(segment, str) and width > best_width:
                    built: dict[str, Any] = {
                        "url": f"https://media.licdn.com/dms/image/v2/{asset_id}/{segment}",
                        "artifact_id": asset_id,
                    }
                    if isinstance(artifact.get("expiresAt"), int):
                        built["expires_at"] = artifact["expiresAt"]
                    best_width = width
                    best_built = built
        elif isinstance(node.get("downloadUrl"), str):
            raw_width = node.get("width")
            width = raw_width if isinstance(raw_width, int) else 0
            if width > best_width:
                built = {"url": node["downloadUrl"]}
                expires = node.get("expiresAt") or node.get("downloadUrlExpiresAt")
                if isinstance(expires, int):
                    built["expires_at"] = expires
                best_width = width
                best_built = built
    return best_built


def _owned_entities(graph: NormalizedGraph, suffix: str) -> list[dict[str, Any]]:
    """Entities of ``suffix`` owned by the target, by graph references only.

    Profile payloads: entities reachable from the target profile (transitive
    through groups). Section payloads: entities referenced from the response
    root. A decorated payload may use both channels; results are de-duplicated
    by URN with stable order.
    """
    owned: dict[str, dict[str, Any]] = {}
    try:
        target = graph.target_profile()
    except (TargetProfileMissing, AmbiguousTargetProfile):
        # Section payloads reference their section entities from the root and
        # have no target Profile; the root-collection channel owns them.
        target = None
    if target is not None:
        for entity in graph.collection_elements(target):
            if _entity_type(entity).lower().endswith(suffix):
                urn = entity.get("entityUrn")
                if isinstance(urn, str):
                    owned[urn] = entity
    for entity in graph.root_collection(suffix):
        urn = entity.get("entityUrn")
        if isinstance(urn, str):
            owned.setdefault(urn, entity)
    return list(owned.values())


def _entity_type(entity: dict[str, Any]) -> str:
    kind = entity.get("$type")
    return kind if isinstance(kind, str) else ""


# -- core --------------------------------------------------------------------


def parse_core(graph: NormalizedGraph) -> dict[str, Any]:
    profile = graph.target_profile()
    first = _localized(profile.get("firstName"))
    last = _localized(profile.get("lastName"))
    full = " ".join(part for part in (first, last) if part) or _localized(profile.get("fullName"))
    member_urn = profile.get("entityUrn")
    location = _localized(profile.get("locationName")) or _localized(profile.get("geoLocationName"))
    return {
        "identity": {
            "member_urn": member_urn if isinstance(member_urn, str) else None,
            "public_identifier": _public_identifier(profile),
        },
        "first_name": first,
        "last_name": last,
        "name": full,
        "headline": _localized(profile.get("headline")),
        "location": location,
        "about": _localized(profile.get("summary")),
        "profile_image": _media(profile.get("profilePicture")),
        "background_image": _media(
            profile.get("backgroundPicture") or profile.get("backgroundPictures")
        ),
        "unknown_entity_types": graph.unknown_entity_types(),
    }


def _public_identifier(profile: dict[str, Any]) -> str | None:
    value = profile.get("publicIdentifier")
    return value if isinstance(value, str) else None


# -- sections ----------------------------------------------------------------


def parse_experience(graph: NormalizedGraph) -> list[dict[str, Any]]:
    companies = {
        str(e.get("entityUrn")): e
        for e in _owned_entities(graph, ".company") + _owned_entities(graph, ".organization")
        if e.get("entityUrn")
    }
    output = []
    for item in _owned_entities(graph, ".position"):
        company_urn = item.get("companyUrn") or item.get("*company")
        company = companies.get(str(company_urn), {})
        period = item.get("timePeriod") or item.get("dateRange") or {}
        start = _date(period.get("startDate") or period.get("start"))
        end = _date(period.get("endDate") or period.get("end"))
        universal_name = company.get("universalName") or company.get("universal-name")
        output.append(
            {
                "id": item.get("entityUrn"),
                "title": _localized(item.get("title")),
                "company_name": _localized(item.get("companyName"))
                or _localized(company.get("name")),
                "company_urn": company_urn if isinstance(company_urn, str) else None,
                "company_url": (
                    f"https://www.linkedin.com/company/{universal_name}/"
                    if isinstance(universal_name, str) and universal_name
                    else None
                ),
                "start_date": start,
                "end_date": end,
                "is_current": start is not None and end is None,
                "location": _localized(item.get("locationName")),
                "description": _localized(item.get("description")),
            }
        )
    return output


def parse_education(graph: NormalizedGraph) -> list[dict[str, Any]]:
    output = []
    for item in _owned_entities(graph, ".education"):
        period = item.get("timePeriod") or item.get("dateRange") or {}
        output.append(
            {
                "id": item.get("entityUrn"),
                "school_name": _localized(item.get("schoolName")),
                "school_urn": item.get("schoolUrn") or item.get("*school"),
                "degree_name": _localized(item.get("degreeName")),
                "field_of_study": _localized(item.get("fieldOfStudy")),
                "start_date": _date(period.get("startDate") or period.get("start")),
                "end_date": _date(period.get("endDate") or period.get("end")),
                "description": _localized(item.get("description")),
            }
        )
    return output


def parse_skills(graph: NormalizedGraph) -> list[dict[str, Any]]:
    return _named_owned(graph, ".skill")


def parse_languages(graph: NormalizedGraph) -> list[dict[str, Any]]:
    by_urn = {str(e.get("entityUrn")): e for e in _owned_entities(graph, ".language")}
    output = []
    for urn, item in by_urn.items():
        name = _localized(item.get("name"))
        if not name:
            continue
        output.append({"id": urn, "name": name, "proficiency": _localized(item.get("proficiency"))})
    return output


def parse_certifications(graph: NormalizedGraph) -> list[dict[str, Any]]:
    organizations = {
        str(e.get("entityUrn")): e
        for e in _owned_entities(graph, ".organization") + _owned_entities(graph, ".company")
        if e.get("entityUrn")
    }
    output = []
    for item in _owned_entities(graph, ".certification"):
        name = _localized(item.get("name"))
        if not name:
            continue
        period = item.get("timePeriod") or {}
        authority = _localized(item.get("authority"))
        if not authority:
            issuer = organizations.get(str(item.get("*authority")), {})
            authority = _localized(issuer.get("name"))
        output.append(
            {
                "id": item.get("entityUrn"),
                "name": name,
                "authority": authority,
                "license_number": item.get("licenseNumber"),
                "start_date": _date(period.get("startDate")),
                "end_date": _date(period.get("endDate")),
            }
        )
    return output


def _named_owned(graph: NormalizedGraph, suffix: str) -> list[dict[str, Any]]:
    output = []
    for item in _owned_entities(graph, suffix):
        name = _localized(item.get("name"))
        if name:
            output.append({"id": item.get("entityUrn"), "name": name})
    return output


# -- unified entry points ----------------------------------------------------


def parse_core_payload(payload: dict[str, Any], slug: str) -> dict[str, Any]:
    """Parse a profile-core response into the core dict (+ owned sections).

    A 200 whose graph carries no resolvable target Profile is schema drift:
    typed failure, never a guessed profile.
    """
    if "flight" in payload:
        return {
            "core": parse_rsc_core_payload(payload, slug),
            "sections": {name: [] for name in SECTION_ENTITY_SUFFIXES},
        }
    if "page_flight" in payload:
        return {
            "core": parse_rsc_page_core_payload(payload, slug),
            "sections": {name: [] for name in SECTION_ENTITY_SUFFIXES},
        }
    graph = NormalizedGraph(payload, slug=slug)
    try:
        core = parse_core(graph)
    except (TargetProfileMissing, AmbiguousTargetProfile) as exc:
        raise UpstreamOperationDrift(
            "profile_core", "the response graph carries no resolvable target profile"
        ) from exc
    sections = {name: _owned_section(graph, name) for name in SECTION_ENTITY_SUFFIXES}
    return {"core": core, "sections": sections}


def parse_section_payload(payload: dict[str, Any], section: str) -> list[dict[str, Any]]:
    """Parse an RSC or historical normalized profile-card response."""
    if "flight" in payload:
        return parse_rsc_section_payload(payload, section)
    graph = NormalizedGraph(payload)
    parser = {
        "experience": parse_experience,
        "education": parse_education,
        "skills": parse_skills,
        "certifications": parse_certifications,
        "languages": parse_languages,
    }[section]
    return parser(graph)


def _owned_section(graph: NormalizedGraph, section: str) -> list[dict[str, Any]]:
    parser = {
        "experience": parse_experience,
        "education": parse_education,
        "skills": parse_skills,
        "certifications": parse_certifications,
        "languages": parse_languages,
    }[section]
    return parser(graph)


# -- legacy compatibility ----------------------------------------------------
# Kept for the fixture-driven unit tests and the benchmark tooling. The graph
# is constructed internally from the payload; ownership rules are identical.


def parse_full_profile(payload: dict[str, Any], slug: str | None = None) -> dict[str, Any]:
    graph = NormalizedGraph(payload, slug=slug)
    core = parse_core(graph)
    return {
        "core": core,
        **{name: _owned_section(graph, name) for name in SECTION_ENTITY_SUFFIXES},
    }
