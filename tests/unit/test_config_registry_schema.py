from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from tross_linkedin_api.config import Settings
from tross_linkedin_api.operation_registry import OperationRegistry
from tross_linkedin_api.validation import SchemaValidator

REGISTRY = Path("config/operation_registry.yaml")


def test_live_settings_can_start_without_session_secrets() -> None:
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
        OperationRegistry.load(tmp_path / "missing.yaml")


def test_project_registry_enables_both_live_operations() -> None:
    registry = OperationRegistry.load(REGISTRY)
    # Section contracts are retired (live-observed 404, 2026-08-29); only the
    # core finder and page fallback serve live traffic.
    assert set(registry.enabled_names()) == {"profile_view", "profile_page"}


def test_disabled_or_unknown_evidence_is_never_active(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        """version: 1
operations:
  - semantic_name: unverified_op
    enabled: true
    evidence_status: unknown
    kind: restli
    method: GET
    path: /voyager/api/identity/dash/profileView
    transport_family: restli
    parser: full_profile_v1
    decoration_ids: [com.linkedin.voyager.dash.deco.identity.profile.WebTopCardCoreProfile-19]
    observed_at: 2026-08-28T00:00:00Z
    evidence_reference: none
""",
        encoding="utf-8",
    )
    loaded = OperationRegistry.load(registry)
    assert loaded.enabled_names() == []
    with pytest.raises(ValueError, match="unavailable in the active evidence mode"):
        loaded.get("unverified_op")


def test_restli_operation_without_decoration_ids_is_allowed(tmp_path: Path) -> None:
    # The live-observed memberIdentity finder answers with its default
    # projection, so a decoration list is optional configuration.
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        """version: 1
operations:
  - semantic_name: bare_op
    enabled: true
    evidence_status: historical
    kind: restli
    method: GET
    path: /voyager/api/identity/dash/profiles
    transport_family: restli
    parser: full_profile_v1
    decoration_ids: []
    observed_at: 2026-08-28T00:00:00Z
    evidence_reference: none
""",
        encoding="utf-8",
    )
    loaded = OperationRegistry.load(registry)
    assert loaded.enabled_names() == ["bare_op"]


def test_registry_rejects_unsafe_path(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        """version: 1
operations:
  - semantic_name: evil_op
    enabled: true
    evidence_status: historical
    kind: restli
    method: GET
    path: /../evil
    transport_family: restli
    parser: full_profile_v1
    decoration_ids: [some-deco-1]
    observed_at: 2026-08-28T00:00:00Z
    evidence_reference: test
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid operation registry"):
        OperationRegistry.load(registry)
