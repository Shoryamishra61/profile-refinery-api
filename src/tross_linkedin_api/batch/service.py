from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from ..canonicalizer import CanonicalProfile
from ..errors import ProblemError
from ..models import ProfileResponse
from ..runtime import Runtime
from . import exports, ingest
from .discovery import Occurrence, dedupe, discover_in_text


class JobState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYABLE = "RETRYABLE"


class BatchState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PARTIAL = "PARTIAL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


MAX_JOB_ATTEMPTS = 2
RETRYABLE_CODES = {"UPSTREAM_TIMEOUT", "UPSTREAM_RATE_LIMITED", "UPSTREAM_CHALLENGE"}


@dataclass(slots=True)
class ProfileJob:
    canonical: CanonicalProfile
    occurrences: list[Occurrence]
    state: JobState = JobState.PENDING
    attempts: int = 0
    error_code: str | None = None
    error_detail: str | None = None
    response: ProfileResponse | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def public_dict(self, include_responses: bool) -> dict[str, Any]:
        document: dict[str, Any] = {
            "canonical_url": self.canonical.canonical_url,
            "state": self.state.value,
            "attempts": self.attempts,
            "error_code": self.error_code,
            "error_detail": self.error_detail,
            "occurrences": [occurrence.as_dict() for occurrence in self.occurrences],
        }
        if include_responses and self.response is not None:
            document["response"] = self.response.model_dump(mode="json")
        return document


@dataclass(slots=True)
class Batch:
    batch_id: str
    created_at: datetime
    jobs: list[ProfileJob]
    skipped_inputs: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def status(self) -> BatchState:
        states = {job.state for job in self.jobs}
        if not states or states == {JobState.PENDING}:
            return BatchState.QUEUED
        if states - {JobState.SUCCEEDED}:
            return BatchState.PARTIAL if states & {JobState.SUCCEEDED} else BatchState.RUNNING
        return BatchState.SUCCEEDED

    def summary(self) -> dict[str, Any]:
        status = self.status()
        succeeded = sum(1 for job in self.jobs if job.state is JobState.SUCCEEDED)
        failed = sum(1 for job in self.jobs if job.state is JobState.FAILED)
        pending = sum(1 for job in self.jobs if job.state is JobState.PENDING)
        return {
            "batch_id": self.batch_id,
            "created_at": self.created_at.isoformat(),
            "status": status.value,
            "statistics": {
                **self.stats,
                "unique_profiles": len(self.jobs),
                "succeeded": succeeded,
                "failed": failed,
                "pending": pending,
            },
            "skipped_inputs": self.skipped_inputs,
        }


class BatchNotFoundError(ProblemError):
    def __init__(self) -> None:
        super().__init__(
            404, "BATCH_NOT_FOUND", "Batch not found", "No batch exists with this identifier."
        )


class ProfileJobNotFoundError(ProblemError):
    def __init__(self) -> None:
        super().__init__(
            404,
            "PROFILE_JOB_NOT_FOUND",
            "Profile job not found",
            "No profile job with this identifier exists in the batch.",
        )


class BatchService:
    """Pull-driven batch extraction with bounded concurrency.

    Serverless runtimes cannot keep background workers alive between requests,
    so batch jobs advance inside polling calls: every read of a batch performs
    extraction work until a small time budget is exhausted, then reports
    status. One failing profile never affects its siblings.
    """

    def __init__(self, runtime: Runtime) -> None:
        self._runtime = runtime
        self._batches: dict[str, Batch] = {}
        self._idempotency: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, pasted_text: str | None, files: list[Any], idempotency_key: str | None = None
    ) -> Batch:
        if idempotency_key:
            async with self._lock:
                existing = self._idempotency.get(idempotency_key)
            if existing and existing in self._batches:
                return self._batches[existing]

        occurrences: list[tuple[str, Occurrence]] = []
        skipped: list[dict[str, Any]] = []
        stats: dict[str, int] = {"url_occurrences_discovered": 0}

        if pasted_text:
            findings = discover_in_text(pasted_text, source_type="pasted_text")
            stats["url_occurrences_discovered"] += len(findings)
            occurrences.extend(findings)

        max_bytes = self._runtime.settings.app_batch_max_file_bytes
        for upload in files:
            name = ingest.sanitize_filename(upload.filename)
            payload = await upload.read(max_bytes + 1)
            if len(payload) > max_bytes:
                skipped.append({"source_name": name, "reason": "file_too_large"})
                continue
            try:
                findings = ingest.ingest(payload, name, name)
            except ingest.IngestError as exc:
                skipped.append({"source_name": name, "reason": exc.detail})
                continue
            stats["url_occurrences_discovered"] += len(findings)
            occurrences.extend(findings)

        profiles = dedupe(occurrences)
        stats["duplicates_removed"] = max(
            0, stats["url_occurrences_discovered"] - len(profiles)
        )
        limit = self._runtime.settings.app_batch_max_urls
        overflow = profiles[limit:]
        for profile in overflow:
            skipped.append(
                {"source_name": profile.canonical.canonical_url, "reason": "batch_url_limit"}
            )
        profiles = profiles[:limit]

        batch = Batch(
            batch_id=str(uuid.uuid4()),
            created_at=datetime.now(UTC),
            jobs=[ProfileJob(canonical=p.canonical, occurrences=p.occurrences) for p in profiles],
            skipped_inputs=skipped,
            stats=stats,
        )
        async with self._lock:
            self._batches[batch.batch_id] = batch
            if idempotency_key:
                self._idempotency[idempotency_key] = batch.batch_id
        return batch

    async def advance(self, batch_id: str, wait_seconds: float | None) -> Batch:
        batch = self._batches.get(batch_id)
        if batch is None:
            raise BatchNotFoundError()
        budget = (
            wait_seconds
            if wait_seconds is not None
            else self._runtime.settings.app_batch_time_budget_seconds
        )
        budget = min(budget, self._runtime.settings.app_batch_time_budget_seconds * 3)
        pending = [job for job in batch.jobs if job.state in {JobState.PENDING, JobState.RETRYABLE}]
        if pending:
            semaphore = asyncio.Semaphore(self._runtime.settings.app_batch_concurrency)

            async def worker(job: ProfileJob) -> None:
                async with semaphore:
                    if job.state is JobState.SUCCEEDED:
                        return
                    job.state = JobState.RUNNING
                    try:
                        job.response = await self._runtime.orchestrator.fetch(
                            job.canonical, f"batch:{batch.batch_id[:8]}"
                        )
                        job.state = JobState.SUCCEEDED
                    except ProblemError as exc:
                        job.attempts += 1
                        job.error_code = exc.code
                        job.error_detail = exc.detail
                        job.state = (
                            JobState.RETRYABLE
                            if exc.code in RETRYABLE_CODES and job.attempts < MAX_JOB_ATTEMPTS
                            else JobState.FAILED
                        )
                    except asyncio.CancelledError:
                        # The poll budget expired mid-flight; the job returns to
                        # the queue and the next poll retries it.
                        job.state = JobState.PENDING
                        raise
                    except Exception as exc:  # noqa: BLE001 - job isolation is the contract
                        job.attempts += 1
                        job.error_code = "INTERNAL_ERROR"
                        job.error_detail = type(exc).__name__
                        job.state = JobState.FAILED
                    job.updated_at = datetime.now(UTC)

            tasks = [asyncio.create_task(worker(job)) for job in pending]
            _, unfinished = await asyncio.wait(tasks, timeout=max(0.0, budget))
            for task in unfinished:
                task.cancel()
            if unfinished:
                await asyncio.gather(*unfinished, return_exceptions=True)
        return batch

    def profiles(self, batch_id: str, include_responses: bool) -> dict[str, Any]:
        batch = self._batches.get(batch_id)
        if batch is None:
            raise BatchNotFoundError()
        return {
            **batch.summary(),
            "report": exports.aggregate(batch),
            "profiles": [
                job.public_dict(include_responses=include_responses) for job in batch.jobs
            ],
        }

    def profile(self, batch_id: str, profile_id: str) -> dict[str, Any]:
        batch = self._batches.get(batch_id)
        if batch is None:
            raise BatchNotFoundError()
        for job in batch.jobs:
            if job.canonical.slug == profile_id or job.canonical.canonical_url == profile_id:
                document = job.public_dict(include_responses=True)
                if job.response is not None:
                    document["report"] = exports.profile_report(job.response.model_dump(mode="json"))
                return document
        raise ProfileJobNotFoundError()

    def aggregate(self, batch_id: str) -> dict[str, Any]:
        batch = self._batches.get(batch_id)
        if batch is None:
            raise BatchNotFoundError()
        return exports.aggregate(batch)

    def export(self, batch_id: str, export_format: str) -> Any:
        from fastapi.responses import JSONResponse, Response

        batch = self._batches.get(batch_id)
        if batch is None:
            raise BatchNotFoundError()
        rows = []
        for job in batch.jobs:
            response = job.response.model_dump(mode="json") if job.response else None
            rows.append(exports.flatten(response, job.state.value, job.error_code))
        if export_format == "json":
            payload = json.loads(exports.json_document(batch.summary(), rows).decode("utf-8"))
            return JSONResponse(
                payload,
                headers={"Content-Disposition": f'attachment; filename="{batch_id}.json"'},
            )
        if export_format == "csv":
            return Response(
                content=exports.csv_bytes(rows),
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{batch_id}.csv"'},
            )
        return Response(
            content=exports.xlsx_bytes(rows),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{batch_id}.xlsx"'},
        )
