from __future__ import annotations

import logging

from profile_refinery_api.observability import OperationEvent, log_operation


def test_operation_log_is_allowlisted(caplog: object) -> None:
    with caplog.at_level(logging.INFO, logger="profile_refinery_api"):  # type: ignore[attr-defined]
        log_operation(OperationEvent("safe-request", "profile_core", 1.5, 200, "ok", 1))
    text = caplog.text  # type: ignore[attr-defined]
    assert "profile_core" in text
    for secret in ("li_at", "JSESSIONID", "csrf-token", "X-API-Key", "Authorization"):
        assert secret not in text
