from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class EvidenceStatus(StrEnum):
    LIVE_VERIFIED = "live_verified"
    HISTORICAL = "historical"
    FIXTURE_VERIFIED = "fixture_verified"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class TransportKind(StrEnum):
    RESTLI = "restli"
    HTML = "html"


class Operation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    semantic_name: str
    enabled: bool
    evidence_status: EvidenceStatus
    kind: TransportKind = TransportKind.RESTLI
    method: str
    path: str
    transport_family: str
    parser: str
    decoration_ids: list[str] = Field(default_factory=list)
    observed_at: datetime | None = None
    fixture: str | None = None
    evidence_reference: str

    @model_validator(mode="after")
    def validate_safe_target(self) -> Operation:
        if self.method not in {"GET", "POST"}:
            raise ValueError("operation method must be GET or POST")
        path = PurePosixPath(self.path)
        if not self.path.startswith("/") or ".." in path.parts or "//" in self.path:
            raise ValueError("operation path must be an absolute safe LinkedIn path")
        if self.enabled and not self.parser:
            raise ValueError("enabled operations require a parser")
        return self


class RegistryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    operations: list[Operation]


class OperationRegistry:
    """Config-driven description of the direct HTTP operations used against LinkedIn.

    An operation may serve live traffic in one of two evidence states: LIVE_VERIFIED
    (validated against a real authenticated session) or HISTORICAL (documented,
    community-corroborated protocol shape that has not yet been re-verified live).
    Anything else is unusable, which keeps the system fail-closed against
    unverified endpoint guesses.
    """

    def __init__(self, document: RegistryDocument) -> None:
        self.version = document.version
        self._operations = {operation.semantic_name: operation for operation in document.operations}
        self._active_names: set[str] = set()
        if len(self._operations) != len(document.operations):
            raise ValueError("operation registry contains duplicate semantic names")
        for operation in document.operations:
            if not operation.enabled:
                continue
            if operation.evidence_status not in {
                EvidenceStatus.LIVE_VERIFIED,
                EvidenceStatus.HISTORICAL,
            }:
                continue
            if not operation.observed_at:
                raise ValueError(
                    f"{operation.semantic_name}: enabled operation lacks observation metadata"
                )
            self._active_names.add(operation.semantic_name)

    @classmethod
    def load(cls, path: Path) -> OperationRegistry:
        if not path.is_file():
            raise FileNotFoundError(f"operation registry is required: {path}")
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            document = RegistryDocument.model_validate(raw)
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise ValueError(f"invalid operation registry: {path}") from exc
        return cls(document)

    def get(self, semantic_name: str) -> Operation:
        try:
            operation = self._operations[semantic_name]
        except KeyError as exc:
            raise KeyError(f"unregistered operation: {semantic_name}") from exc
        if semantic_name not in self._active_names:
            raise ValueError(f"operation is unavailable in the active evidence mode: {semantic_name}")
        return operation

    def enabled_names(self) -> list[str]:
        return [name for name in self._operations if name in self._active_names]
