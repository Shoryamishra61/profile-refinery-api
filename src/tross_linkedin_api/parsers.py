from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .errors import UpstreamOperationDrift

PARSER_VERSION = "normalized-entities-v1"


def _objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


def _entities(payload: dict[str, Any]) -> list[dict[str, Any]]:
    included = payload.get("included", [])
    if not isinstance(included, list):
        raise ValueError("included must be an array")
    entities = [item for item in included if isinstance(item, dict)]
    for candidate in _objects(payload.get("data", {})):
        if candidate.get("entityUrn") and candidate not in entities:
            entities.append(candidate)
    return entities


def _type(entity: dict[str, Any]) -> str:
    return str(entity.get("$type", "")).lower()


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
    if not isinstance(value, dict):
        return None
    candidates = list(_objects(value))
    artifacts = [node for node in candidates if isinstance(node.get("downloadUrl"), str)]
    if not artifacts:
        return None
    artifact = artifacts[-1]
    result: dict[str, Any] = {"url": artifact["downloadUrl"]}
    asset = value.get("vectorArtifact") or value.get("displayImage") or value.get("originalImage")
    if isinstance(asset, str):
        result["artifact_id"] = asset
    expires = artifact.get("expiresAt") or artifact.get("downloadUrlExpiresAt")
    if isinstance(expires, int):
        result["expires_at"] = expires
    return result


def parse_core(payload: dict[str, Any]) -> dict[str, Any]:
    entities = _entities(payload)
    profile = next((item for item in entities if _type(item).endswith(".profile")), None)
    if profile is None:
        raise ValueError("profile entity not found")
    first = _localized(profile.get("firstName"))
    last = _localized(profile.get("lastName"))
    name = " ".join(part for part in (first, last) if part) or _localized(profile.get("name"))
    location = profile.get("geoLocationName") or profile.get("locationName")
    if isinstance(location, dict):
        location = _localized(location)
    public_identifier = profile.get("publicIdentifier")
    return {
        "identity": {
            "member_urn": profile.get("entityUrn"),
            "public_identifier": public_identifier if isinstance(public_identifier, str) else None,
        },
        "name": name,
        "headline": _localized(profile.get("headline")),
        "location": location if isinstance(location, str) else None,
        "about": _localized(profile.get("summary")),
        "profile_image": _media(profile.get("profilePicture")),
        "background_image": _media(profile.get("backgroundPicture")),
    }


def parse_experience(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entities = _entities(payload)
    companies = {
        str(item.get("entityUrn")): item
        for item in entities
        if _type(item).endswith(".company") and item.get("entityUrn")
    }
    output = []
    for item in entities:
        if not _type(item).endswith(".position"):
            continue
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
                "company_urn": company_urn,
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
                "group_id": item.get("multiLocaleCompanyNameInfo", {}).get("groupId")
                if isinstance(item.get("multiLocaleCompanyNameInfo"), dict)
                else None,
            }
        )
    return output


def parse_education(payload: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for item in _entities(payload):
        if not _type(item).endswith(".education"):
            continue
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


def _parse_named(payload: dict[str, Any], suffix: str) -> list[dict[str, Any]]:
    return [
        {"id": item.get("entityUrn"), "name": _localized(item.get("name"))}
        for item in _entities(payload)
        if _type(item).endswith(suffix) and _localized(item.get("name"))
    ]


def parse_skills(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return _parse_named(payload, ".skill")


def parse_certifications(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entities = _entities(payload)
    organizations = {
        str(item.get("entityUrn")): item
        for item in entities
        if (_type(item).endswith(".organization") or _type(item).endswith(".company"))
        and item.get("entityUrn")
    }
    output = []
    for item in entities:
        if not _type(item).endswith(".certification"):
            continue
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


def parse_languages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    output = _parse_named(payload, ".language")
    by_urn = {str(item.get("entityUrn")): item for item in _entities(payload)}
    for item in output:
        source = by_urn.get(str(item.get("id")), {})
        item["proficiency"] = _localized(source.get("proficiency")) or source.get("proficiency")
    return output


def parse_full_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the core identity and every section from one profile payload.

    Both the dash profileView resource and the embedded page JSON return a
    single entity graph, so all sections are derived from the same response —
    the minimal request set LinkedIn itself requires.
    """
    return {
        "core": parse_core(payload),
        "experience": parse_experience(payload),
        "education": parse_education(payload),
        "skills": parse_skills(payload),
        "certifications": parse_certifications(payload),
        "languages": parse_languages(payload),
    }


PARSERS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "profile_core_v1": parse_core,
    "experience_v1": parse_experience,
    "education_v1": parse_education,
    "skills_v1": parse_skills,
    "certifications_v1": parse_certifications,
    "languages_v1": parse_languages,
    "full_profile_v1": parse_full_profile,
}


def parse(operation: str, parser_name: str, payload: dict[str, Any]) -> Any:
    try:
        parser = PARSERS[parser_name]
    except KeyError as exc:
        raise UpstreamOperationDrift(
            operation, "No parser is registered for this operation."
        ) from exc
    try:
        return parser(payload)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise UpstreamOperationDrift(
            operation, "The upstream payload failed its parser contract."
        ) from exc
