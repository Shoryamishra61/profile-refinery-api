from __future__ import annotations

import os
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .config import AppMode


class EvidenceStatus(StrEnum):
    LIVE_VERIFIED = "live_verified"
    FIXTURE_VERIFIED = "fixture_verified"
    HISTORICAL = "historical"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class Operation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    semantic_name: str
    enabled: bool
    evidence_status: EvidenceStatus
    method: str
    path: str
    transport_family: str
    query_id_env: str | None = None
    input_variables: list[str]
    parser: str
    observed_at: datetime | None = None
    viewer_context: str
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
    def __init__(self, document: RegistryDocument, mode: AppMode) -> None:
        self.version = document.version
        self._operations = {operation.semantic_name: operation for operation in document.operations}
        self._active_names: set[str] = set()
        if len(self._operations) != len(document.operations):
            raise ValueError("operation registry contains duplicate semantic names")
        for operation in document.operations:
            if not operation.enabled:
                continue
            allowed = (
                operation.evidence_status is EvidenceStatus.LIVE_VERIFIED
                if mode is AppMode.LIVE
                else operation.evidence_status is EvidenceStatus.FIXTURE_VERIFIED
            )
            if not allowed:
                continue
            if not operation.observed_at or not operation.fixture:
                raise ValueError(
                    f"{operation.semantic_name}: enabled operation lacks observation metadata"
                )
            if (
                mode is AppMode.LIVE
                and operation.query_id_env
                and not os.getenv(operation.query_id_env)
            ):
                raise ValueError(f"{operation.semantic_name}: missing {operation.query_id_env}")
            self._active_names.add(operation.semantic_name)

    @classmethod
    def load(cls, path: Path, mode: AppMode) -> OperationRegistry:
        if not path.is_file():
            raise FileNotFoundError(f"operation registry is required: {path}")
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            document = RegistryDocument.model_validate(raw)
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise ValueError(f"invalid operation registry: {path}") from exc
        return cls(document, mode)

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
