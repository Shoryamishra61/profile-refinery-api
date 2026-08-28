from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from tross_linkedin_api.config import AppMode, Settings
from tross_linkedin_api.operation_registry import OperationRegistry
from tross_linkedin_api.validation import SchemaValidator


def test_live_mode_can_start_degraded_without_runtime_session_secrets() -> None:
    settings = Settings(app_api_keys=["caller"], app_mode="live")
    assert settings.linkedin_li_at is None
    assert settings.linkedin_jsessionid is None


def test_api_keys_are_required() -> None:
    with pytest.raises(ValidationError):
        Settings(app_api_keys=[])


def test_schema_missing_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        SchemaValidator(tmp_path / "missing.json")


def test_registry_missing_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        OperationRegistry.load(tmp_path / "missing.yaml", AppMode.FIXTURE)


def test_fixture_registry_has_no_active_operations_in_live_mode() -> None:
    registry = OperationRegistry.load(Path("config/operation_registry.yaml"), AppMode.LIVE)
    assert registry.enabled_names() == []
    with pytest.raises(ValueError, match="unavailable in the active evidence mode"):
        registry.get("profile_core")


def test_registry_rejects_unsafe_path(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        """version: 1
operations:
  - semantic_name: profile_core
    enabled: true
    evidence_status: fixture_verified
    method: POST
    path: /../evil
    transport_family: graphql
    query_id_env: null
    input_variables: [member_identity]
    parser: profile_core_v1
    observed_at: 2026-08-27T00:00:00Z
    viewer_context: synthetic_fixture
    fixture: core.json
    evidence_reference: test
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid operation registry"):
        OperationRegistry.load(registry, AppMode.FIXTURE)
