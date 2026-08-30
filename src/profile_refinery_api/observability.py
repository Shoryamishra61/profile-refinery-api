from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass

logger = logging.getLogger("profile_refinery_api")


@dataclass(frozen=True, slots=True)
class OperationEvent:
    request_id: str
    operation: str
    duration_ms: float
    status_code: int
    parser_outcome: str
    attempt: int


def log_operation(event: OperationEvent) -> None:
    logger.info(json.dumps(asdict(event), separators=(",", ":"), sort_keys=True))
