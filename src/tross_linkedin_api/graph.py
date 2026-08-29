"""Normalized entity graph for LinkedIn Voyager/Dash responses.

Core invariant (governing spec §7):

    Ownership is determined by references from the target/root graph, not by
    globally collecting entities that happen to have a given ``$type``.

A response's ``included[]`` array may contain entities belonging to other
members or unrelated surfaces (LinkedIn interning is additive). Therefore:

* the target profile is the ``Profile`` entity referenced from the *root*
  ``data`` object (never "the first Profile in included[]");
* section entities (positions, education, ...) are the entities reachable
  from the root/target through URN reference keys (``*``-prefixed keys),
  transitively through group/collection entities, with depth and cycle
  bounds.

This module is a pure transformation: no I/O, deterministic order.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Iterable, Iterator
from typing import Any

_URN_SCHEME = "urn:li:"
_MAX_TRAVERSAL_DEPTH = 6


def _looks_like_urn(value: str) -> bool:
    return value.startswith(_URN_SCHEME)


def _refs_of(entity_or_data: dict[str, Any]) -> Iterator[str]:
    """Yield URN references held by a data/entity object.

    LinkedIn encodes references as ``*``-prefixed keys (single URN string or
    list of URN strings). ``entityUrn`` is an object's own identity, not a
    reference, and is skipped.
    """
    for key, value in entity_or_data.items():
        if not key.startswith("*"):
            continue
        if isinstance(value, str):
            if _looks_like_urn(value):
                yield value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and _looks_like_urn(item):
                    yield item


def _entity_type(entity: dict[str, Any]) -> str:
    kind = entity.get("$type")
    return kind if isinstance(kind, str) else ""


def _public_identifier(entity: dict[str, Any]) -> str | None:
    value = entity.get("publicIdentifier")
    return value if isinstance(value, str) else None


class AmbiguousTargetProfile(Exception):
    """The root graph references profiles that cannot be disambiguated."""


class TargetProfileMissing(Exception):
    """No Profile entity is reachable from the root graph."""


class NormalizedGraph:
    """Indexed view over one Voyager/Dash response payload."""

    def __init__(self, payload: dict[str, Any], slug: str | None = None) -> None:
        self.slug = slug
        self._by_urn: dict[str, dict[str, Any]] = {}
        included = payload.get("included", [])
        if isinstance(included, list):
            for entity in included:
                if not isinstance(entity, dict):
                    continue
                urn = entity.get("entityUrn")
                if isinstance(urn, str) and _looks_like_urn(urn):
                    self._by_urn.setdefault(urn, entity)
        self._root_refs = list(_refs_of(payload.get("data", {})))

    # -- resolution ----------------------------------------------------------

    def resolve(self, urn: str) -> dict[str, Any] | None:
        return self._by_urn.get(urn)

    def resolve_many(self, refs: Iterable[str]) -> list[dict[str, Any]]:
        resolved = []
        for urn in refs:
            entity = self._by_urn.get(urn)
            if entity is not None:
                resolved.append(entity)
        return resolved

    # -- target ownership ----------------------------------------------------

    def _referenced(self, urns: Iterable[str], type_suffix: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for urn in urns:
            entity = self._by_urn.get(urn)
            if entity is not None and _entity_type(entity).lower().endswith(type_suffix):
                out.append(entity)
        return out

    def target_urn(self) -> str:
        """The Profile URN referenced from the root graph.

        Multiple root-referenced profiles are disambiguated by the requested
        slug (public identifier comparison is case-insensitive; URN-embedded
        identifiers are url-decoded before comparison). Ambiguity is an error,
        never a guess.
        """
        candidates = self._referenced(self._root_refs, ".profile")
        if not candidates:
            raise TargetProfileMissing("root graph references no Profile entity")
        if len(candidates) == 1:
            urn = candidates[0].get("entityUrn")
            return urn if isinstance(urn, str) else ""
        if self.slug:
            wanted = self.slug.lower()
            for entity in candidates:
                public = _public_identifier(entity)
                if public and public.lower() == wanted:
                    urn = entity.get("entityUrn")
                    if isinstance(urn, str):
                        return urn
            for entity in candidates:
                urn_value = entity.get("entityUrn")
                if isinstance(urn_value, str) and wanted in urllib.parse.unquote(urn_value).lower():
                    return urn_value
        raise AmbiguousTargetProfile(
            f"root graph references {len(candidates)} Profile entities; "
            "the target could not be disambiguated"
        )

    def target_profile(self) -> dict[str, Any]:
        urn = self.target_urn()
        entity = self.resolve(urn)
        if entity is None:  # pragma: no cover - target_urn resolves from the index
            raise TargetProfileMissing(urn)
        return entity

    def collection_elements(self, ref_or_object: str | dict[str, Any]) -> list[dict[str, Any]]:
        """Entities reachable from an entity (or a URN) via reference keys.

        Traversal is transitive through group/collection entities (a
        PositionGroup referencing Positions, for example), depth-bounded and
        cycle-safe. Self-references are skipped; the traversal only follows
        ``*`` reference keys, so unrelated entities in ``included[]`` are
        unreachable by construction.
        """
        root_urn = (
            ref_or_object
            if isinstance(ref_or_object, str)
            else str(ref_or_object.get("entityUrn") or "")
        )
        root = self._by_urn.get(root_urn) if isinstance(ref_or_object, str) else ref_or_object
        if not isinstance(root, dict):
            return []
        owned: dict[str, dict[str, Any]] = {}
        visited: set[str] = set()

        def walk(entity: dict[str, Any], depth: int) -> None:
            if depth > _MAX_TRAVERSAL_DEPTH:
                return
            for urn in _refs_of(entity):
                if urn in visited:
                    continue
                visited.add(urn)
                resolved = self._by_urn.get(urn)
                if resolved is None:
                    continue
                owned[urn] = resolved
                walk(resolved, depth + 1)

        walk(root, 0)
        return list(owned.values())

    def root_collection(self, type_suffix: str) -> list[dict[str, Any]]:
        """Entities of ``type_suffix`` referenced from the payload root.

        Used by section responses (profileCards): the endpoint is already
        section-scoped, so ownership is the set of entities reachable from
        the root graph — never the full ``included[]`` array.
        """
        owned: dict[str, dict[str, Any]] = {}

        def visit(urn: str, depth: int) -> None:
            entity = self._by_urn.get(urn)
            if entity is None:
                return
            if _entity_type(entity).lower().endswith(type_suffix) and urn not in owned:
                owned[urn] = entity
            if depth >= _MAX_TRAVERSAL_DEPTH:
                return
            for child_urn in _refs_of(entity):
                visit(child_urn, depth + 1)

        for urn in self._root_refs:
            visit(urn, 0)
        return list(owned.values())

    def unknown_entity_types(self) -> list[str]:
        """Distinct included[] $types outside the known dash profile family.

        Surfaced as telemetry/warnings only — unknown types must never
        corrupt normalization.
        """
        known_prefixes = (
            "com.linkedin.voyager.dash.identity.profile.",
            "com.linkedin.voyager.dash.organization.",
            "com.linkedin.voyager.dash.company.",
            "com.linkedin.voyager.identity.profile.",
            "com.linkedin.voyager.common.",
        )
        unknown = {
            _entity_type(entity)
            for entity in self._by_urn.values()
            if _entity_type(entity) and not _entity_type(entity).lower().startswith(known_prefixes)
        }
        return sorted(unknown)
