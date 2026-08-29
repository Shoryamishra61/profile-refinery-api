from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from ..canonicalizer import CanonicalProfile
from ..errors import ProblemError
from ..governor import CircuitOpen
from ..metrics import METRICS
from ..models import ProfileResponse
from ..parsers import PARSER_VERSION
from ..runtime import Runtime
from . import exports, ingest
from .discovery import Occurrence, dedupe, discover_in_text
from .store import JournalStore


class JobState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRY_WAIT = "RETRY_WAIT"
    BLOCKED_UPSTREAM = "BLOCKED_UPSTREAM"


class BatchState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    PARTIAL = "PARTIAL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


# Total executions per job (initial + at most one resume after a transient
# failure). Rejections by the circuit breaker do not consume this budget:
# that work never reached the upstream, so it is resumption, not retry.
MAX_JOB_ATTEMPTS = 2
# Transient application codes a later poll may resume. CircuitOpen is handled
# separately (BLOCKED_UPSTREAM). All other failures are deterministic.
RETRY_WAIT_CODES = {"UPSTREAM_TIMEOUT", "UPSTREAM_RATE_LIMITED"}


def deterministic_job_id(canonical_url: str) -> str:
    """Stable identity: same canonical profile + schema version ⇒ same job."""
    material = f"{canonical_url}|{PARSER_VERSION}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


@dataclass(slots=True)
class Attempt:
    started_at: str
    completed_at: str
    outcome: str  # succeeded | <error code> | blocked
    latency_ms: float
    breaker_state: str


@dataclass(slots=True)
class ProfileJob:
    canonical: CanonicalProfile
    occurrences: list[Occurrence]
    job_id: str
    state: JobState = JobState.PENDING
    attempts: int = 0
    error_code: str | None = None
    error_detail: str | None = None
    response: ProfileResponse | None = None
    history: list[Attempt] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def public_dict(self, include_responses: bool) -> dict[str, Any]:
        document: dict[str, Any] = {
            "job_id": self.job_id,
            "canonical_url": self.canonical.canonical_url,
            "state": self.state.value,
            "attempts": self.attempts,
            "error_code": self.error_code,
            "error_detail": self.error_detail,
            "occurrences": [occurrence.as_dict() for occurrence in self.occurrences],
            "attempt_history": [
                {
                    "started_at": item.started_at,
                    "completed_at": item.completed_at,
                    "outcome": item.outcome,
                    "latency_ms": round(item.latency_ms, 1),
                    "breaker_state": item.breaker_state,
                }
                for item in self.history
            ],
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
    idempotency_key: str | None = None

    def status(self) -> BatchState:
        states = {job.state for job in self.jobs}
        if not states or states == {JobState.PENDING}:
            return BatchState.QUEUED
        if states == {JobState.SUCCEEDED}:
            return BatchState.SUCCEEDED
        if states <= {JobState.FAILED}:
            return BatchState.FAILED
        if JobState.BLOCKED_UPSTREAM in states and JobState.RUNNING not in states:
            return BatchState.DEGRADED
        unfinished = states & {
            JobState.PENDING,
            JobState.RUNNING,
            JobState.RETRY_WAIT,
            JobState.BLOCKED_UPSTREAM,
        }
        if unfinished:
            return BatchState.RUNNING
        if JobState.SUCCEEDED in states and JobState.FAILED in states:
            return BatchState.PARTIAL
        return BatchState.RUNNING

    def summary(self) -> dict[str, Any]:
        counts = {state: 0 for state in JobState}
        for job in self.jobs:
            counts[job.state] += 1
        return {
            "batch_id": self.batch_id,
            "created_at": self.created_at.isoformat(),
            "status": self.status().value,
            "statistics": {
                **self.stats,
                "unique_profiles": len(self.jobs),
                "succeeded": counts[JobState.SUCCEEDED],
                "failed": counts[JobState.FAILED],
                "pending": counts[JobState.PENDING] + counts[JobState.RUNNING],
                "retry_wait": counts[JobState.RETRY_WAIT],
                "blocked_upstream": counts[JobState.BLOCKED_UPSTREAM],
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
    """Pull-driven, durable batch extraction behind the upstream governor.

    Serverless runtimes cannot keep background workers alive between requests,
    so batch jobs advance inside polling calls: every read of a batch performs
    extraction work until a small time budget is exhausted, then reports
    status. State transitions are journalled to disk; identical profiles
    across concurrent work share one in-flight extraction (single-flight
    coalescing); one failing profile never affects its siblings.
    """

    def __init__(self, runtime: Runtime) -> None:
        self._runtime = runtime
        self._store = JournalStore(runtime.settings.app_store_dir)
        self._batches: dict[str, Batch] = {}
        self._idempotency: dict[str, str] = {}
        # Request coalescing: one in-flight extraction per deterministic job id.
        self._inflight: dict[str, asyncio.Task[Any]] = {}
        # Verified-success cache for coalescing concurrent duplicates.
        self._completed: dict[str, ProfileResponse] = {}
        self._lock = asyncio.Lock()
        self._restore()

    def _restore(self) -> None:
        for document in self._store.load_all():
            try:
                batch = self._deserialize(document)
            except (KeyError, ValueError):
                continue
            self._batches[batch.batch_id] = batch
            if batch.idempotency_key:
                self._idempotency[batch.idempotency_key] = batch.batch_id

    def _serialize(self, batch: Batch) -> dict[str, Any]:
        return {
            "batch_id": batch.batch_id,
            "created_at": batch.created_at.isoformat(),
            "idempotency_key": batch.idempotency_key,
            "stats": batch.stats,
            "skipped_inputs": batch.skipped_inputs,
            "jobs": [
                {
                    "job_id": job.job_id,
                    "input_url": job.canonical.input_url,
                    "canonical_url": job.canonical.canonical_url,
                    "state": job.state.value,
                    "attempts": job.attempts,
                    "error_code": job.error_code,
                    "error_detail": job.error_detail,
                    "occurrences": [occurrence.as_dict() for occurrence in job.occurrences],
                    "history": [
                        {
                            "started_at": item.started_at,
                            "completed_at": item.completed_at,
                            "outcome": item.outcome,
                            "latency_ms": item.latency_ms,
                            "breaker_state": item.breaker_state,
                        }
                        for item in job.history
                    ],
                    "response": (
                        job.response.model_dump(mode="json") if job.response else None
                    ),
                }
                for job in batch.jobs
            ],
        }

    def _deserialize(self, document: dict[str, Any]) -> Batch:
        from ..canonicalizer import canonicalize_profile_url

        jobs = []
        for item in document.get("jobs", []):
            response = None
            if item.get("response"):
                response = ProfileResponse.model_validate(item["response"])
            jobs.append(
                ProfileJob(
                    canonical=canonicalize_profile_url(item["canonical_url"]),
                    occurrences=[Occurrence(**occ) for occ in item.get("occurrences", [])],
                    job_id=item["job_id"],
                    state=JobState(item.get("state", "PENDING")),
                    attempts=item.get("attempts", 0),
                    error_code=item.get("error_code"),
                    error_detail=item.get("error_detail"),
                    response=response,
                    history=[
                        Attempt(
                            started_at=h["started_at"],
                            completed_at=h["completed_at"],
                            outcome=h["outcome"],
                            latency_ms=h["latency_ms"],
                            breaker_state=h["breaker_state"],
                        )
                        for h in item.get("history", [])
                    ],
                )
            )
        batch = Batch(
            batch_id=document["batch_id"],
            created_at=datetime.fromisoformat(document["created_at"]),
            jobs=jobs,
            skipped_inputs=document.get("skipped_inputs", []),
            stats=document.get("stats", {}),
            idempotency_key=document.get("idempotency_key"),
        )
        return batch

    def _persist(self, batch: Batch) -> None:
        try:
            self._store.save(batch.batch_id, self._serialize(batch))
        except OSError:
            # Persistence is best-effort on ephemeral disks; the in-memory
            # copy remains authoritative for the life of the process.
            METRICS.increment("journal_write_failed_total")

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
            findings = discover_in_text(pasted_text, "pasted_text")
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
        stats["duplicates_removed"] = max(0, stats["url_occurrences_discovered"] - len(profiles))
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
            jobs=[
                ProfileJob(
                    canonical=p.canonical,
                    occurrences=p.occurrences,
                    job_id=deterministic_job_id(p.canonical.canonical_url),
                )
                for p in profiles
            ],
            skipped_inputs=skipped,
            stats=stats,
            idempotency_key=idempotency_key,
        )
        async with self._lock:
            self._batches[batch.batch_id] = batch
            if idempotency_key:
                self._idempotency[idempotency_key] = batch.batch_id
        self._persist(batch)
        METRICS.increment("batches_created_total")
        return batch

    def queue_stats(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        pending = running = blocked = 0
        oldest: datetime | None = None
        for batch in self._batches.values():
            for job in batch.jobs:
                if job.state in (JobState.PENDING, JobState.RETRY_WAIT):
                    pending += 1
                    if oldest is None or job.updated_at < oldest:
                        oldest = job.updated_at
                elif job.state is JobState.RUNNING:
                    running += 1
                elif job.state is JobState.BLOCKED_UPSTREAM:
                    blocked += 1
        return {
            "batches_tracked": len(self._batches),
            "queue_depth": pending + blocked,
            "jobs_running": running,
            "jobs_blocked_upstream": blocked,
            "queue_oldest_age_seconds": round((now - oldest).total_seconds(), 1) if oldest else 0.0,
        }

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
        resumable = [
            job
            for job in batch.jobs
            if job.state
            in {JobState.PENDING, JobState.RETRY_WAIT, JobState.BLOCKED_UPSTREAM}
        ]
        if resumable:
            semaphore = asyncio.Semaphore(self._runtime.settings.app_batch_concurrency)

            async def worker(job: ProfileJob) -> None:
                async with semaphore:
                    if job.state is JobState.SUCCEEDED:
                        return
                    await self._execute_job(batch, job)

            tasks = []
            for job in resumable:
                task = None
                existing = self._inflight.get(job.job_id)
                if existing is not None and not existing.done():
                    # Request coalescing: this profile is already being
                    # extracted elsewhere; share that result.
                    task = asyncio.create_task(self._share(existing, job, batch))
                elif job.job_id in self._completed:
                    self._adopt(batch, job, self._completed[job.job_id])
                else:
                    task = asyncio.create_task(worker(job))
                    self._inflight[job.job_id] = task
                if task is not None:
                    tasks.append(task)
            _, unfinished = await asyncio.wait(tasks, timeout=max(0.0, budget))
            for task in unfinished:
                task.cancel()
            if unfinished:
                await asyncio.gather(*unfinished, return_exceptions=True)
            for job in resumable:
                self._inflight.pop(job.job_id, None)
        self._persist(batch)
        return batch

    async def _share(self, inflight: asyncio.Task[ProfileResponse], job: ProfileJob, batch: Batch) -> None:
        try:
            response = await inflight
        except Exception:  # noqa: BLE001 - the primary owner records the failure
            return
        self._adopt(batch, job, response)

    def _adopt(self, batch: Batch, job: ProfileJob, response: ProfileResponse) -> None:
        if job.state is JobState.SUCCEEDED:
            return
        job.response = response
        job.state = JobState.SUCCEEDED
        job.updated_at = datetime.now(UTC)
        METRICS.increment("jobs_coalesced_total")

    async def _execute_job(self, batch: Batch, job: ProfileJob) -> None:
        job.state = JobState.RUNNING
        self._persist(batch)
        started = datetime.now(UTC)
        started_monotonic = asyncio.get_running_loop().time()
        try:
            response = await self._runtime.orchestrator.fetch(
                job.canonical, f"batch:{batch.batch_id[:8]}:{job.job_id[:8]}"
            )
        except CircuitOpen as exc:
            # Rejected before any upstream traffic: resumption, not retry.
            job.state = JobState.BLOCKED_UPSTREAM
            job.error_code = exc.code
            job.error_detail = exc.detail
            job.history.append(
                Attempt(
                    started_at=started.isoformat(),
                    completed_at=datetime.now(UTC).isoformat(),
                    outcome="blocked_circuit_open",
                    latency_ms=(asyncio.get_running_loop().time() - started_monotonic) * 1000,
                    breaker_state=self._runtime.governor.breaker.state.value,
                )
            )
            METRICS.increment("jobs_blocked_total")
        except ProblemError as exc:
            if exc.code == "UPSTREAM_CHALLENGE":
                # A challenge is a capacity event (the breaker just opened):
                # the job is retained and resumed after recovery, and the
                # attempt budget is not consumed by upstream refusals.
                job.state = JobState.BLOCKED_UPSTREAM
                job.error_code = exc.code
                job.error_detail = exc.detail
                job.history.append(
                    Attempt(
                        started_at=started.isoformat(),
                        completed_at=datetime.now(UTC).isoformat(),
                        outcome="blocked_challenge",
                        latency_ms=(asyncio.get_running_loop().time() - started_monotonic) * 1000,
                        breaker_state=self._runtime.governor.breaker.state.value,
                    )
                )
                METRICS.increment("jobs_blocked_total")
                job.updated_at = datetime.now(UTC)
                self._persist(batch)
                return
            job.attempts += 1
            job.error_code = exc.code
            job.error_detail = exc.detail
            job.state = (
                JobState.RETRY_WAIT
                if exc.code in RETRY_WAIT_CODES and job.attempts < MAX_JOB_ATTEMPTS
                else JobState.FAILED
            )
            job.history.append(
                Attempt(
                    started_at=started.isoformat(),
                    completed_at=datetime.now(UTC).isoformat(),
                    outcome=exc.code,
                    latency_ms=(asyncio.get_running_loop().time() - started_monotonic) * 1000,
                    breaker_state=self._runtime.governor.breaker.state.value,
                )
            )
            METRICS.increment("jobs_failed_total", 1.0, code=exc.code)
        except asyncio.CancelledError:
            # Poll budget expired mid-flight: back to the queue, budget intact.
            job.state = JobState.PENDING
            raise
        except Exception as exc:  # noqa: BLE001 - job isolation is the contract
            job.attempts += 1
            job.error_code = "INTERNAL_ERROR"
            job.error_detail = type(exc).__name__
            job.state = JobState.FAILED
            job.history.append(
                Attempt(
                    started_at=started.isoformat(),
                    completed_at=datetime.now(UTC).isoformat(),
                    outcome="INTERNAL_ERROR",
                    latency_ms=(asyncio.get_running_loop().time() - started_monotonic) * 1000,
                    breaker_state=self._runtime.governor.breaker.state.value,
                )
            )
            METRICS.increment("jobs_failed_total", 1.0, code="INTERNAL_ERROR")
        else:
            job.response = response
            job.state = JobState.SUCCEEDED
            self._completed[job.job_id] = response
            job.history.append(
                Attempt(
                    started_at=started.isoformat(),
                    completed_at=datetime.now(UTC).isoformat(),
                    outcome="succeeded",
                    latency_ms=(asyncio.get_running_loop().time() - started_monotonic) * 1000,
                    breaker_state=self._runtime.governor.breaker.state.value,
                )
            )
            METRICS.increment("jobs_succeeded_total")
        job.updated_at = datetime.now(UTC)
        self._persist(batch)

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
                    document["report"] = exports.profile_report(
                        job.response.model_dump(mode="json")
                    )
                return document
        raise ProfileJobNotFoundError()

    def aggregate(self, batch_id: str) -> dict[str, Any]:
        batch = self._batches.get(batch_id)
        if batch is None:
            raise BatchNotFoundError()
        return exports.aggregate(batch)

    def _export_rows(self, batch: Batch) -> list[dict[str, Any]]:
        rows = []
        for job in batch.jobs:
            response = job.response.model_dump(mode="json") if job.response else None
            rows.append(exports.flatten(response, job.state.value, job.error_code))
        return rows

    def report(self, batch_id: str) -> dict[str, Any]:
        """Deterministic grounded report with a stable content hash (spec §10.9)."""
        batch = self._batches.get(batch_id)
        if batch is None:
            raise BatchNotFoundError()
        report = exports.aggregate(batch)
        return {
            "batch_id": batch.batch_id,
            "report": report,
            "report_hash": exports.report_hash(report, PARSER_VERSION),
            "generator_version": PARSER_VERSION,
        }

    def export(self, batch_id: str, export_format: str) -> Any:
        from fastapi.responses import JSONResponse, Response

        batch = self._batches.get(batch_id)
        if batch is None:
            raise BatchNotFoundError()
        rows = self._export_rows(batch)
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
        sections_by_url: dict[str, dict[str, list[dict[str, Any]]]] = {}
        provenance_by_url: dict[str, list[dict[str, Any]]] = {}
        failures: list[dict[str, Any]] = []
        for job in batch.jobs:
            url = job.canonical.canonical_url
            if job.response is not None:
                dump = job.response.model_dump(mode="json")
                profile = dump.get("profile", {})
                sections_by_url[url] = {
                    name: exports.field_value(profile, name) or []
                    for name in ("experience", "education", "skills", "certifications", "languages")
                }
            provenance_by_url[url] = [o.as_dict() for o in job.occurrences]
            if job.state is JobState.FAILED:
                failures.append(
                    {
                        "linkedin_url": url,
                        "status": job.state.value,
                        "error_code": job.error_code,
                        "error_detail": job.error_detail,
                    }
                )
        return Response(
            content=exports.xlsx_bytes(rows, sections_by_url, provenance_by_url, failures),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{batch_id}.xlsx"'},
        )
