"""Minimal in-process metrics registry with Prometheus text exposition.

Counters and gauges only — enough for the observability contract (request
totals, upstream operation outcomes, breaker state, queue depth/age, retry
totals, jobs by state) without adding a dependency.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any


class Metrics:
    def __init__(self) -> None:
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = defaultdict(float)
        self._started = time.time()

    def increment(self, name: str, value: float = 1.0, **labels: str) -> None:
        self._counters[_key(name, labels)] += value

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        self._gauges[_key(name, labels)] = value

    def snapshot(self) -> dict[str, Any]:
        return {
            "uptime_seconds": round(time.time() - self._started, 1),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
        }

    def prometheus(self) -> str:
        lines: list[str] = []
        families: dict[str, list[tuple[dict[str, str], float]]] = defaultdict(list)
        for key, value in self._counters.items():
            name, labels = _split_key(key)
            families[f"profile_refinery_{name}_total"].append((labels, value))
        for key, value in self._gauges.items():
            name, labels = _split_key(key)
            families[f"profile_refinery_{name}"].append((labels, value))
        for family, series in sorted(families.items()):
            lines.append(f"# TYPE {family} gauge")
            for labels, value in sorted(series, key=lambda item: str(item[0])):
                label_text = ""
                if labels:
                    pairs = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                    label_text = "{" + pairs + "}"
                lines.append(f"{family}{label_text} {value}")
        return "\n".join(lines) + "\n"


def _key(name: str, labels: dict[str, str]) -> str:
    if not labels:
        return name
    rendered = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return f"{name}|{rendered}"


def _split_key(key: str) -> tuple[str, dict[str, str]]:
    if "|" not in key:
        return key, {}
    name, label_text = key.split("|", 1)
    labels: dict[str, str] = {}
    for pair in label_text.split(","):
        k, _, v = pair.partition("=")
        labels[k] = v
    return name, labels


METRICS = Metrics()
