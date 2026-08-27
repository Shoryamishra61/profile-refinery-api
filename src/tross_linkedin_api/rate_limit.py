from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from threading import Lock


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, caller_key: str) -> int | None:
        caller = hashlib.sha256(caller_key.encode()).hexdigest()[:16]
        now = time.monotonic()
        with self._lock:
            events = self._events[caller]
            while events and now - events[0] >= self._window:
                events.popleft()
            if len(events) >= self._limit:
                return max(1, int(self._window - (now - events[0])))
            events.append(now)
        return None
