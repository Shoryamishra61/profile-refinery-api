"""Upstream control plane: rate budget, bounded concurrency, retry budget,
challenge-aware circuit breaker.

Every outbound LinkedIn operation flows through :class:`UpstreamGovernor`.
Application code never calls the transport directly and never makes its own
retry decision — the governor owns all scarce-upstream policy.

Patterns and the workload characteristics that justify them:

* Token bucket (rate budget) — LinkedIn tolerates only gentle sustained
  request rates; a burst of ~20 requests demonstrably triggers a soft
  challenge. The bucket bounds both burst size and sustained rate
  independently of concurrency.
* Semaphore (bounded concurrency) — concurrency controls in-flight work;
  the bucket controls arrival rate. Both are needed: concurrency alone
  would still allow N fast requests in the same instant.
* Circuit breaker (challenge-aware) — a challenge or repeated upstream
  failure is a global capacity event, not a per-request error. Opening the
  circuit stops *all* extraction traffic, lets queued jobs wait durably,
  and performs exactly one controlled probe after cooldown.
* Single-layer retry budget — retries are another upstream request. The
  governor is the only layer allowed to retry, with a bounded attempt
  count, exponential backoff and jitter. Deterministic failures
  (unavailable profile, drift, expired auth) are never retried.
"""
from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any, TypeVar

from .errors import (
    ProblemError,
    UpstreamChallenge,
    UpstreamRateLimited,
    UpstreamTimeout,
)

T = TypeVar("T")


class BreakerState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpen(ProblemError):
    """The breaker is open: extraction is paused, jobs remain durable."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            503,
            "UPSTREAM_CIRCUIT_OPEN",
            "Upstream extraction paused",
            (
                "The LinkedIn circuit breaker is open. Queued jobs are retained "
                "and will resume after the cooldown probe succeeds."
            ),
            {"retry_after_seconds": retry_after_seconds},
        )


class TokenBucket:
    """Classic token bucket: burst capacity plus a sustained refill rate."""

    def __init__(self, capacity: int, refill_per_minute: float) -> None:
        if capacity < 1 or refill_per_minute <= 0:
            raise ValueError("token bucket requires capacity >= 1 and positive refill")
        self._capacity = float(capacity)
        self._refill_per_second = refill_per_minute / 60.0
        self._tokens = float(capacity)
        self._updated = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        self._tokens = min(
            self._capacity, self._tokens + (now - self._updated) * self._refill_per_second
        )
        self._updated = now

    def try_consume(self, tokens: float = 1.0) -> float:
        """Consume tokens; return 0.0 on success or the seconds to wait."""
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return 0.0
        deficit = tokens - self._tokens
        return max(0.0, deficit / self._refill_per_second)


class CircuitBreaker:
    """CLOSED → (threshold failures | challenge) → OPEN → cooldown → HALF_OPEN →
    one probe → CLOSED | OPEN."""

    def __init__(self, failure_threshold: int, cooldown_seconds: float) -> None:
        if failure_threshold < 1:
            raise ValueError("breaker threshold must be >= 1")
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self.state = BreakerState.CLOSED
        self.consecutive_failures = 0
        self.opened_at: float | None = None
        self.opens_total = 0
        self.last_challenge_at: float | None = None
        self._probe_in_flight = False

    def allow(self) -> tuple[bool, float]:
        """Return (allowed, seconds_until_retry). At most one HALF_OPEN probe."""
        if self.state is BreakerState.CLOSED:
            return True, 0.0
        assert self.opened_at is not None
        elapsed = time.monotonic() - self.opened_at
        remaining = max(0.0, self._cooldown - elapsed)
        if remaining > 0:
            return False, remaining
        if self._probe_in_flight:
            return False, 1.0
        self.state = BreakerState.HALF_OPEN
        self._probe_in_flight = True
        return True, 0.0

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self._probe_in_flight = False
        if self.state is not BreakerState.CLOSED:
            self.state = BreakerState.CLOSED
            self.opened_at = None

    def record_failure(self, *, challenge: bool = False) -> None:
        self._probe_in_flight = False
        if challenge:
            self.last_challenge_at = time.monotonic()
        self.consecutive_failures += 1
        if self.state is BreakerState.HALF_OPEN or self.consecutive_failures >= self._threshold:
            self._open()

    def abandon_probe(self) -> None:
        """Return to OPEN when the half-open probe is cancelled mid-flight.

        Without this, a cancelled probe would leave the breaker wedged in
        HALF_OPEN with `_probe_in_flight` set, rejecting all traffic forever.
        """
        if self.state is BreakerState.HALF_OPEN:
            self._probe_in_flight = False
            self._open()

    def record_challenge(self) -> None:
        """A challenge opens the breaker immediately regardless of threshold."""
        self.last_challenge_at = time.monotonic()
        self._open()

    def _open(self) -> None:
        self.state = BreakerState.OPEN
        self.opened_at = time.monotonic()
        self.opens_total += 1

    def observe(self) -> dict[str, Any]:
        retry_in = 0.0
        if self.state is BreakerState.OPEN and self.opened_at is not None:
            retry_in = max(0.0, self._cooldown - (time.monotonic() - self.opened_at))
        return {
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "opens_total": self.opens_total,
            "retry_in_seconds": round(retry_in, 1),
            "last_challenge_at": self.last_challenge_at,
        }


RETRYABLE_ERRORS = (UpstreamTimeout, UpstreamRateLimited)
BREAKER_ERRORS = (UpstreamChallenge,)


class UpstreamGovernor:
    """Single governed entry point for every LinkedIn operation."""

    def __init__(
        self,
        *,
        concurrency: int,
        bucket_capacity: int,
        refill_per_minute: float,
        max_retries: int,
        breaker_failure_threshold: int,
        breaker_cooldown_seconds: float,
        max_backoff_seconds: float = 8.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._semaphore = asyncio.Semaphore(concurrency)
        self._bucket = TokenBucket(bucket_capacity, refill_per_minute)
        self._max_retries = max(0, max_retries)
        self._max_backoff = max_backoff_seconds
        self.breaker = CircuitBreaker(breaker_failure_threshold, breaker_cooldown_seconds)
        self._clock = clock
        self.retries_total = 0
        self.operations_total = 0
        self.operations_failed_total = 0

    async def run(self, operation: str, call: Callable[[], Awaitable[T]]) -> T:
        """Execute one upstream operation under the full control plane."""
        attempt = 0
        probe_granted = False
        while True:
            allowed, retry_in = self.breaker.allow()
            if not allowed:
                raise CircuitOpen(max(1, int(retry_in)))
            probe_granted = self.breaker.state is BreakerState.HALF_OPEN
            wait = self._bucket.try_consume()
            while wait > 0:
                # Sleep, then actually acquire the token. Re-consuming in the
                # loop is essential: without it, concurrent waiters would all
                # sleep in parallel and proceed without ever reserving
                # capacity, defeating the rate budget.
                await asyncio.sleep(wait)
                wait = self._bucket.try_consume()
            async with self._semaphore:
                # Re-check the breaker after waiting in the queue: it may have
                # opened while this operation sat behind the semaphore. The
                # granted half-open probe passes its own gate; everyone else
                # is rejected while the probe is in flight.
                if probe_granted:
                    allowed = True
                else:
                    allowed, retry_in = self.breaker.allow()
                if not allowed:
                    raise CircuitOpen(max(1, int(retry_in)))
                attempt += 1
                self.operations_total += 1
                try:
                    result = await call()
                except BREAKER_ERRORS:
                    self.operations_failed_total += 1
                    self.breaker.record_challenge()
                    raise
                except ProblemError as exc:
                    self.operations_failed_total += 1
                    self.breaker.record_failure()
                    if isinstance(exc, RETRYABLE_ERRORS) and attempt <= self._max_retries:
                        self.retries_total += 1
                        await self._backoff(attempt)
                        continue
                    raise
                except asyncio.CancelledError:
                    self.breaker.abandon_probe()
                    raise
                except TimeoutError:
                    # Deliberately NOT asyncio.CancelledError: poll-budget
                    # cancellation must propagate so the job returns to the
                    # queue instead of being retried or miscounted.
                    self.operations_failed_total += 1
                    self.breaker.record_failure()
                    if attempt <= self._max_retries:
                        self.retries_total += 1
                        await self._backoff(attempt)
                        continue
                    raise UpstreamTimeout(operation) from None
                else:
                    self.breaker.record_success()
                    return result

    async def _backoff(self, attempt: int) -> None:
        base = min(self._max_backoff, 0.5 * (2 ** (attempt - 1)))
        jittered = base * random.uniform(0.8, 1.2)  # noqa: S311 - jitter, not crypto
        await asyncio.sleep(jittered)

    def observe(self) -> dict[str, Any]:
        return {
            "breaker": self.breaker.observe(),
            "operations_total": self.operations_total,
            "operations_failed_total": self.operations_failed_total,
            "retries_total": self.retries_total,
        }
