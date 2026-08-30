"""Durable job journal: crash-safe batch/job persistence as JSON files.

Each batch is one atomic JSON document rewritten on state transitions
(temp file + os.replace). On process start, :meth:`JournalStore.load_all`
restores every batch, so warm restarts resume pending jobs instead of
losing them. On Vercel the store directory lives on the instance's
ephemeral disk — see docs/adr-0005-deployment-runtime.md for the honest
tradeoff and the upgrade path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class JournalStore:
    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, batch_id: str) -> Path:
        # batch ids are server-generated UUIDs; the safe-name check guards the
        # directory against any non-uuid identifier reaching the store.
        if not batch_id or any(ch in batch_id for ch in "/\\.:"):
            raise ValueError("invalid batch id for journal storage")
        return self._dir / f"batch-{batch_id}.json"

    def save(self, batch_id: str, document: dict[str, Any]) -> None:
        path = self._path(batch_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def load(self, batch_id: str) -> dict[str, Any] | None:
        path = self._path(batch_id)
        if not path.is_file():
            return None
        try:
            document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # A corrupt journal entry is discarded rather than fatal; the
            # in-memory copy remains authoritative while the process lives.
            return None
        return document if isinstance(document, dict) else None

    def load_all(self) -> list[dict[str, Any]]:
        documents = []
        for path in sorted(self._dir.glob("batch-*.json")):
            batch_id = path.stem.removeprefix("batch-")
            document = self.load(batch_id)
            if document is not None:
                documents.append(document)
        return documents

    def delete(self, batch_id: str) -> None:
        path = self._path(batch_id)
        if path.is_file():
            path.unlink()
