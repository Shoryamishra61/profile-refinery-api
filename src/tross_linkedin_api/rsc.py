"""Deterministic decoder for LinkedIn SDUI profile-card React Flight records.

The current profile page returns newline-framed Flight model records. This
module does not render React or inspect DOM/CSS. It resolves Flight chunk
references, selects section roots by LinkedIn's stable ``viewName`` semantics,
groups server-provided collection items, and normalizes their semantic content.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from .errors import UpstreamOperationDrift

RSC_PARSER_VERSION = "linkedin-sdui-flight-v1"
_CURRENT_DATE_LABEL = "Present"

_REFERENCE_RE = re.compile(r"^\$L?([0-9a-f]+)$")
_MONTHS = {
    name: index
    for index, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        start=1,
    )
}
_DATE_TOKEN_RE = re.compile(
    r"^(?:(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) )?"
    r"(?P<year>\d{4})$"
)
_DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)? ?\d{4})"
    r"\s*(?:-|–|—)\s*"
    r"(?P<end>Present|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)? ?\d{4})"
)
_ISSUED_RE = re.compile(
    r"Issued (?P<issued>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)? ?\d{4})"
)
_EXPIRES_RE = re.compile(
    r"Expires (?P<expires>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)? ?\d{4})"
)
_SKILL_ID_RE = re.compile(r"com\.linkedin\.sdui\.profile\.skill\([^,]+,\s*([^)]+)\)")
_LANGUAGE_ID_RE = re.compile(r"com\.linkedin\.sdui\.profile\.language\([^,]+,\s*([^)]+)\)")

_RESERVED_LEAVES = {"button", "div", "hr", "p", "section"}
_PROFICIENCIES = {
    "elementary proficiency",
    "limited working proficiency",
    "professional working proficiency",
    "full professional proficiency",
    "native or bilingual proficiency",
}
_SECTION_VIEW_FRAGMENTS = {
    "experience": "experience",
    "education": "education",
    "skills": "skill",
    "certifications": "certification",
    "languages": "language",
}
_SECTION_MARKERS = {
    "experience": "ExperienceTopLevelSection",
    "education": "EducationTopLevelSection",
    "skills": "Skills",
    "certifications": "CertificationTopLevel",
    "languages": "LanguageTopLevel",
}
_PROFILE_STATE_BINDINGS = {
    "shouldRefreshScreenOnReappear": "ProfileComponentStateShouldRefreshScreen",
    "shouldFetchFromCache": "ProfileComponentStateFetchFromCache",
    "shouldDisplayTabAnchors": "ProfileComponentStateShouldDisplayTabAnchors",
    "shouldReloadTopCardOnReappear": "ProfileComponentStateShouldReloadTopCardOnReappear",
    "deferredTopCardReloadProfileId": "ProfileComponentStateDeferredTopCardReloadProfileId",
    "shouldDisplayStickyHeader": "ProfileComponentStateShouldDisplayStickyHeader",
    "shouldRefreshLanguageDetailScreen": "ProfileComponentStateShouldRefreshLanguageDetails",
    "lastPerformedActionRef": "ProfileComponentStateLastPerformedActionRef",
    "shouldFocusOnReappear": "ProfileComponentStateShouldFocusOnReappear",
    "shouldFocusFeaturedOnReappear": "ProfileComponentStateShouldFocusFeaturedOnReappear",
    "lastFeaturedActionRef": "ProfileComponentStateLastFeaturedActionRef",
    "shouldHideProfileCards": "ProfileComponentStateProfileHideCards",
}


def build_profile_component_body(slug: str, viewee_id: str) -> dict[str, Any]:
    """Build the captured SDUI replaceable-section request contract."""

    def binding(key_prefix: str) -> dict[str, Any]:
        return {
            "type": "com.linkedin.sdui.components.core.BindingImpl",
            "value": {
                "key": f"{key_prefix}{slug}ProfileComponentState",
                "namespace": "MemoryNamespace",
            },
        }

    component_state: dict[str, Any] = {"profileId": slug}
    component_state.update(
        {field: binding(prefix) for field, prefix in _PROFILE_STATE_BINDINGS.items()}
    )
    return {
        "clientArguments": {
            "payload": {
                "isSelfView": False,
                "vanityName": slug,
                "replaceableSectionArgs": {
                    "vanityName": slug,
                    "hideCardsForGoldenGate": False,
                    "shouldSetupReplaceableComponent": True,
                    "vieweeProfileId": viewee_id,
                    "isSelfView": False,
                    "isSelfViewResolved": False,
                },
                "profileComponentState": component_state,
            },
            "states": [],
            "requestMetadata": {"$type": "proto.sdui.common.RequestMetadata"},
            "screenId": "com.linkedin.sdui.flagshipnav.profile.Profile",
            "knownTemplateIds": [],
        }
    }


def build_profile_activity_body(slug: str) -> dict[str, Any]:
    """Build the captured vanity-only Activity resolver request contract."""

    return {
        "clientArguments": {
            "payload": {"isSelfView": False, "vanityName": slug},
            "states": [],
            "requestMetadata": {"$type": "proto.sdui.common.RequestMetadata"},
            "screenId": "com.linkedin.sdui.flagshipnav.home.Home",
            "knownTemplateIds": [],
        }
    }


@dataclass(slots=True)
class FlightDocument:
    records: dict[str, Any]

    @classmethod
    def parse(cls, text: str) -> FlightDocument:
        records: dict[str, Any] = {}
        for line in text.splitlines():
            record_id, separator, payload = line.partition(":")
            if not separator or not record_id or payload.startswith("I"):
                continue
            try:
                records[record_id] = json.loads(payload)
            except json.JSONDecodeError:
                # Flight also supports non-model record tags. Profile-card
                # semantic data is carried by JSON model records only.
                continue
        if not records:
            raise UpstreamOperationDrift("profile_rsc", "No Flight model records were decoded.")
        return cls(records)

    def resolve(self, value: Any, stack: frozenset[str] = frozenset()) -> Any:
        if isinstance(value, str):
            match = _REFERENCE_RE.fullmatch(value)
            if not match:
                return value
            record_id = match.group(1)
            if record_id in stack or record_id not in self.records:
                return value
            return self.resolve(self.records[record_id], stack | {record_id})
        if isinstance(value, list):
            return [self.resolve(child, stack) for child in value]
        if isinstance(value, dict):
            return {key: self.resolve(child, stack) for key, child in value.items()}
        return value

    def section_root(self, section: str) -> Any | None:
        fragment = _SECTION_VIEW_FRAGMENTS[section]
        candidates: list[Any] = []
        resolved_records: list[Any] = []
        for record in self.records.values():
            resolved = self.resolve(record)
            resolved_records.append(resolved)
            for node in _objects(resolved):
                tracking = node.get("viewTrackingSpecs")
                view_name = tracking.get("viewName") if isinstance(tracking, dict) else None
                if (
                    isinstance(view_name, str)
                    and view_name.startswith("profile-card-")
                    and fragment in view_name
                ):
                    candidates.append(node)
        if not candidates:
            return None
        # Part1 emits education, certification, and project lockups as sibling
        # Flight records rather than guaranteed descendants of the profile-card
        # shell. Two scoping rules by live-observed shape:
        # - sibling lockup records present (viewName
        #   "license-certifications-lockup-view"): the full resolved record set
        #   is the semantic scope, and the parser prefers lockup-view matches.
        # - otherwise (shell-nested collections): the certification shell alone
        #   is the scope, so the education collection cannot leak in.
        if section == "certifications":
            has_lockup_views = any(
                isinstance(node, dict)
                and isinstance(node.get("viewTrackingSpecs"), dict)
                and node["viewTrackingSpecs"].get("viewName")
                == "license-certifications-lockup-view"
                for record in resolved_records
                for node in _objects(record)
            )
            if has_lockup_views:
                return resolved_records
            return candidates or resolved_records
        return max(candidates, key=lambda value: len(json.dumps(value, separators=(",", ":"))))

    def carries_marker(self, section: str) -> bool:
        marker = _SECTION_MARKERS[section]
        return any(
            marker in value for record in self.records.values() for value in _strings(record)
        )


def parse_rsc_section_payload(payload: dict[str, Any], section: str) -> list[dict[str, Any]]:
    text = payload.get("flight")
    if not isinstance(text, str):
        raise UpstreamOperationDrift(f"profile_{section}", "RSC payload lacks Flight text.")
    document = FlightDocument.parse(text)
    root = document.section_root(section)
    if root is None:
        if document.carries_marker(section):
            return []
        raise UpstreamOperationDrift(
            f"profile_{section}", f"Flight response lacks the {section} semantic component."
        )
    parser = {
        "experience": _parse_experience,
        "education": _parse_education,
        "skills": _parse_skills,
        "certifications": _parse_certifications,
        "languages": _parse_languages,
    }[section]
    return parser(root)


def describe_rsc_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return bounded semantic diagnostics without exposing raw Flight data."""

    text = payload.get("flight")
    if not isinstance(text, str):
        return {"bytes": 0, "models": 0, "view_names": [], "visible_leaves": []}
    document = FlightDocument.parse(text)
    resolved = [document.resolve(record) for record in document.records.values()]
    view_names = _stable_unique(
        [name for record in resolved for name in _values_for_key(record, "viewName")]
    )
    leaves = _stable_unique([text for record in resolved for text in _visible_text(record)])
    return {
        "bytes": len(text.encode()),
        "models": len(document.records),
        "view_names": view_names[:80],
        "visible_leaves": leaves[:80],
    }


def parse_rsc_core_payload(payload: dict[str, Any], slug: str) -> dict[str, Any]:
    """Resolve target-owned core fields from the Activity Flight component.

    Activity can contain many post actors. Ownership is established by the
    server's ``prioritizedProfileId`` resolver argument. The smallest resolved
    model containing that argument and the profile loading-state actions is
    selected; no unrelated actor is accepted as the profile owner.
    """

    text = payload.get("flight")
    if not isinstance(text, str):
        raise UpstreamOperationDrift("profile_view", "RSC payload lacks Flight text.")
    document = FlightDocument.parse(text)
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for record in document.records.values():
        raw_prioritized = {
            node["prioritizedProfileId"]
            for node in _objects(record)
            if isinstance(node.get("prioritizedProfileId"), str)
        }
        if not raw_prioritized:
            continue
        resolved = document.resolve(record)
        for node in _objects(resolved):
            prioritized = {
                child["prioritizedProfileId"]
                for child in _objects(node)
                if isinstance(child.get("prioritizedProfileId"), str)
            }
            if not prioritized:
                continue
            states = _profile_loading_states(node)
            if "profile_name_loading_state" not in states:
                continue
            for profile_id in prioritized:
                candidates.append(
                    (len(json.dumps(node, separators=(",", ":"))), profile_id, states)
                )
    if not candidates:
        first_model = next(iter(document.records.values()))
        signature = _safe_model_signature(first_model)
        raise UpstreamOperationDrift(
            "profile_view",
            (
                "Flight response lacks a target-owned profile identity resolver "
                f"(bytes={len(text.encode())}, models={len(document.records)}, "
                f"prioritized={text.count('prioritizedProfileId')}, "
                f"name_state={text.count('profile_name_loading_state')}, "
                f"signature={signature})."
            ),
        )
    _, profile_id, states = min(candidates, key=lambda candidate: candidate[0])
    name = _state_string(states.get("profile_name_loading_state"))
    if not name:
        raise UpstreamOperationDrift("profile_view", "Identity resolver lacks a profile name.")
    return {
        "identity": {
            "member_urn": f"urn:li:fsd_profile:{profile_id}",
            "public_identifier": slug,
        },
        "first_name": None,
        "last_name": None,
        "name": name,
        "headline": _state_string(states.get("profile_headline_loading_state")),
        "location": None,
        "about": None,
        "profile_image": _state_image(states.get("profile_photo_loading_state")),
        "background_image": None,
        "unknown_entity_types": [],
    }


def _safe_model_signature(value: Any) -> str:
    """Return a bounded, non-payload diagnostic for protocol drift."""

    if isinstance(value, dict):
        keys = ",".join(sorted(value)[:12])
        semantic: list[str] = []
        for node in _objects(value):
            for key in ("$type", "code", "status", "viewName"):
                item = node.get(key)
                if isinstance(item, (str, int)):
                    semantic.append(f"{key}:{str(item)[:80]}")
            if len(semantic) >= 5:
                break
        return f"dict[{keys}]/{'|'.join(semantic[:5])}"
    if isinstance(value, list):
        parts = [
            (item[:60] if item.startswith("$") else f"str[{len(item)}]")
            if isinstance(item, str)
            else type(item).__name__
            for item in value[:8]
        ]
        semantic = [
            f"{key}:{str(node[key])[:80]}"
            for node in _objects(value)
            for key in ("$type", "code", "status", "viewName")
            if isinstance(node.get(key), (str, int))
        ][:5]
        return f"list[{len(value)}]/{','.join(parts)}/{'|'.join(semantic)}"
    if isinstance(value, str):
        return f"str[{len(value)}]"
    return type(value).__name__


def _profile_loading_states(value: Any) -> dict[str, Any]:
    states: dict[str, Any] = {}
    for node in _objects(value):
        if node.get("$type") != "proto.sdui.actions.core.SetState":
            continue
        wrapper = node.get("value")
        state = wrapper.get("state") if isinstance(wrapper, dict) else None
        if not isinstance(state, dict):
            continue
        key = state.get("key")
        inner_key = key.get("key") if isinstance(key, dict) else None
        key_value = inner_key.get("value") if isinstance(inner_key, dict) else None
        state_id = key_value.get("id") if isinstance(key_value, dict) else None
        if isinstance(state_id, str) and state_id.startswith("profile_"):
            states[state_id] = state.get("value")
    return states


def _state_string(value: Any) -> str | None:
    if not isinstance(value, dict) or value.get("$case") != "stringValue":
        return None
    text = value.get("stringValue")
    return text.strip() if isinstance(text, str) and text.strip() else None


def _state_image(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or value.get("$case") != "imageAssetValue":
        return None
    asset = value.get("imageAssetValue")
    source = asset.get("source") if isinstance(asset, dict) else None
    render = source.get("renderPayload") if isinstance(source, dict) else None
    if not isinstance(render, dict):
        return None
    root_url = render.get("rootUrl")
    renditions = render.get("imageRenditions")
    if not isinstance(root_url, str) or not isinstance(renditions, list):
        return None
    candidates = [
        rendition
        for rendition in renditions
        if isinstance(rendition, dict) and isinstance(rendition.get("suffixUrl"), str)
    ]
    if not candidates:
        return None
    best = max(candidates, key=_rendition_width)
    return {"url": root_url + best["suffixUrl"]}


def _rendition_width(rendition: dict[str, Any]) -> int:
    width = rendition.get("width")
    return width if isinstance(width, int) else 0


def _objects(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _values_for_key(value: Any, key: str) -> list[str]:
    output: list[str] = []
    for node in _objects(value):
        candidate = node.get(key)
        if isinstance(candidate, str):
            output.append(candidate)
    return output


def _collection_items(root: Any) -> list[tuple[str | None, Any]]:
    collections = [
        node["initialItems"]
        for node in _objects(root)
        if isinstance(node.get("initialItems"), list)
    ]
    if not collections:
        return []
    items: list[tuple[str | None, Any]] = []
    seen: set[str] = set()
    for collection in collections:
        for entry in collection:
            if not isinstance(entry, dict):
                continue
            semantic_id = entry.get("semanticId")
            identity = (
                semantic_id if isinstance(semantic_id, str) else json.dumps(entry, sort_keys=True)
            )
            if identity in seen:
                continue
            seen.add(identity)
            items.append((semantic_id if isinstance(semantic_id, str) else None, entry.get("item")))
    return items


def _semantic_lockups(root: Any, view_name: str) -> list[tuple[str | None, Any]]:
    candidates: list[tuple[int, str | None, Any, tuple[str, ...]]] = []
    for node in _objects(root):
        tracking = node.get("viewTrackingSpecs")
        if not isinstance(tracking, dict) or tracking.get("viewName") != view_name:
            continue
        texts = tuple(_visible_text(node))
        if not texts:
            continue
        component_key = node.get("componentKey") or node.get("componentkey")
        semantic_id = component_key if isinstance(component_key, str) else None
        candidates.append((len(json.dumps(node, separators=(",", ":"))), semantic_id, node, texts))
    output: list[tuple[str | None, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for _, semantic_id, node, texts in sorted(candidates, reverse=True, key=lambda item: item[0]):
        if texts in seen:
            continue
        seen.add(texts)
        output.append((semantic_id, node))
    return output


def _section_items(root: Any, lockup_view: str) -> list[tuple[str | None, Any]]:
    items = _collection_items(root)
    return items if items else _semantic_lockups(root, lockup_view)


def _dated_semantic_items(root: Any) -> list[tuple[str | None, Any]]:
    """Find current SDUI lockups that expose no collection or lockup view name."""

    candidates: list[tuple[int, int, tuple[str, ...], Any]] = []
    for node in _objects(root):
        texts = tuple(_visible_text(node))
        if len(texts) < 3:
            continue
        date_hits = sum(bool(_DATE_RANGE_RE.search(text)) for text in texts)
        if date_hits != 1:
            continue
        date_index, *_ = _date_range(list(texts))
        if date_index is None or date_index < 2:
            continue
        candidates.append(
            (
                len(candidates),
                len(json.dumps(node, separators=(",", ":"))),
                texts,
                node,
            )
        )
    # A Flight lockup can appear through several nested wrappers. Select the
    # smallest node for each identical semantic text sequence, but emit it at
    # that sequence's first traversal position so LinkedIn ordering survives.
    best: dict[tuple[str, ...], tuple[int, int, Any]] = {}
    for order, size, texts, node in candidates:
        current = best.get(texts)
        if current is None or size < current[1]:
            best[texts] = (order if current is None else current[0], size, node)
    return [(None, node) for _, _, node in sorted(best.values(), key=lambda item: item[0])]


def _visible_text(value: Any) -> list[str]:
    output: list[str] = []
    for node in _objects(value):
        children = node.get("children")
        if not isinstance(children, list):
            continue
        for child in children:
            if not isinstance(child, str):
                continue
            text = child.strip()
            if (
                not text
                or text.startswith("$")
                or text in _RESERVED_LEAVES
                or text.startswith("com.linkedin.sdui.profile.card.ref")
            ):
                continue
            output.append(text)
    return _stable_unique(output)


def _urls(value: Any, path_fragment: str | None = None) -> list[str]:
    output = []
    for node in _objects(value):
        for key in ("url", "urlValue"):
            candidate = node.get(key)
            if isinstance(candidate, str) and candidate.startswith(("/", "https://")):
                if path_fragment is None or path_fragment in candidate:
                    output.append(candidate)
    return _stable_unique(output)


def _stable_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _date(token: str | None) -> dict[str, int] | None:
    if not token:
        return None
    match = _DATE_TOKEN_RE.fullmatch(token.strip())
    if not match:
        return None
    result = {"year": int(match.group("year"))}
    month = match.group("month")
    if month:
        result["month"] = _MONTHS[month]
    return result


def _date_range(
    texts: list[str],
) -> tuple[int | None, dict[str, int] | None, dict[str, int] | None, bool | None, str | None]:
    for index, text in enumerate(texts):
        match = _DATE_RANGE_RE.search(text)
        if not match:
            continue
        end_token = match.group("end")
        duration_parts = [part.strip() for part in text.split("·")]
        duration = duration_parts[1] if len(duration_parts) > 1 else None
        return (
            index,
            _date(match.group("start")),
            None if end_token == _CURRENT_DATE_LABEL else _date(end_token),
            end_token == _CURRENT_DATE_LABEL,
            duration,
        )
    return None, None, None, None, None


def _parse_experience(root: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    items = _collection_items(root) or _semantic_lockups(root, "experience-lockup-view")
    if not items:
        items = _dated_semantic_items(root)
    for semantic_id, item in items:
        texts = _visible_text(item)
        if len(texts) < 2:
            continue
        date_index, start, end, current, duration = _date_range(texts)
        company_parts = [part.strip() for part in texts[1].split("·", 1)]
        company_url = next(iter(_urls(item, "/company/")), None)
        location = None
        workplace_type = None
        description_start = len(texts)
        if date_index is not None and date_index + 1 < len(texts):
            location_parts = [part.strip() for part in texts[date_index + 1].split("·", 1)]
            location = location_parts[0] or None
            workplace_type = location_parts[1] if len(location_parts) > 1 else None
            description_start = date_index + 2
        description = "\n\n".join(texts[description_start:]) or None
        output.append(
            {
                "id": semantic_id,
                "title": texts[0],
                "company_name": company_parts[0] or None,
                "company_urn": None,
                "company_url": company_url,
                "employment_type": company_parts[1] if len(company_parts) > 1 else None,
                "start_date": start,
                "end_date": end,
                "is_current": current,
                "duration": duration,
                "location": location,
                "workplace_type": workplace_type,
                "description": description,
                "group_id": None,
            }
        )
    return output


def _parse_education(root: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for semantic_id, item in _section_items(root, "education-lockup-view"):
        texts = _visible_text(item)
        if not texts:
            continue
        date_index, start, end, _, _ = _date_range(texts)
        pre_date = texts[1:date_index] if date_index is not None else texts[1:]
        degree = pre_date[0] if pre_date else None
        field = None
        if degree and ", " in degree:
            degree, field = degree.split(", ", 1)
        remainder = texts[(date_index + 1) if date_index is not None else len(texts) :]
        grade = next(
            (text.removeprefix("Grade: ") for text in remainder if text.startswith("Grade: ")), None
        )
        activities = next(
            (
                text.removeprefix("Activities and societies: ")
                for text in remainder
                if text.startswith("Activities and societies: ")
            ),
            None,
        )
        descriptions = [
            text
            for text in remainder
            if not text.startswith(("Grade: ", "Activities and societies: "))
        ]
        output.append(
            {
                "id": semantic_id,
                "school_name": texts[0],
                "school_urn": None,
                "school_url": next(iter(_urls(item, "/school/")), None),
                "degree_name": degree,
                "field_of_study": field,
                "start_date": start,
                "end_date": end,
                "grade": grade,
                "activities": activities,
                "description": "\n\n".join(descriptions) or None,
            }
        )
    return output


def _parse_skills(root: Any) -> list[dict[str, Any]]:
    texts = [
        text
        for text in _visible_text(root)
        if text.casefold() != "skills"
        and not _SKILL_ID_RE.fullmatch(text)
        and not text.endswith("-divider")
    ]
    ids = []
    for value in _strings(root):
        match = _SKILL_ID_RE.fullmatch(value)
        if match:
            ids.append(value)
    ids = _stable_unique(ids)
    return [
        {"id": ids[index] if index < len(ids) else None, "name": name}
        for index, name in enumerate(texts)
    ]


def _parse_certifications(root: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for semantic_id, item in _section_items(root, "license-certifications-lockup-view"):
        texts = _visible_text(item)
        if not texts:
            continue
        issued_text = next((text for text in texts if text.startswith("Issued ")), "")
        issued = _ISSUED_RE.search(issued_text)
        expires = _EXPIRES_RE.search(issued_text)
        credential_id = next(
            (
                text.removeprefix("Credential ID ")
                for text in texts
                if text.startswith("Credential ID ")
            ),
            None,
        )
        urls = [url for url in _urls(item) if "/company/" not in url]
        output.append(
            {
                "id": semantic_id,
                "name": texts[0],
                "authority": texts[1] if len(texts) > 1 and texts[1] != issued_text else None,
                "license_number": credential_id,
                "credential_url": urls[0] if urls else None,
                "start_date": _date(issued.group("issued")) if issued else None,
                "end_date": _date(expires.group("expires")) if expires else None,
            }
        )
    return output


def _parse_languages(root: Any) -> list[dict[str, Any]]:
    texts = [text for text in _visible_text(root) if text.casefold() != "languages"]
    ids = _stable_unique([value for value in _strings(root) if _LANGUAGE_ID_RE.fullmatch(value)])
    output = []
    index = 0
    language_index = 0
    while index < len(texts):
        name = texts[index]
        proficiency = None
        if index + 1 < len(texts) and texts[index + 1].casefold() in _PROFICIENCIES:
            proficiency = texts[index + 1]
            index += 1
        output.append(
            {
                "id": ids[language_index] if language_index < len(ids) else None,
                "name": name,
                "proficiency": proficiency,
            }
        )
        language_index += 1
        index += 1
    return output
