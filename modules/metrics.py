"""Four Golden Signals collector for the compliance FastAPI service.

Implements the SRE-book "Four Golden Signals" (latency, traffic, errors,
saturation) in-process so ``/metrics`` returns useful numbers without a
Prometheus pushgateway, a Grafana Cloud subscription, or any other external
service. The pattern is deliberately small — this is a factory-local
dashboard, not a multi-region SaaS, so a single-process rolling window is
the right fit.

Pattern reference: Stefan Dienst, "Building Trust in Your Data Pipelines
with Observability", PyCon DE 2026. Three take-aways the module tries to
honour:

1. **Actionable, reliable, contextual** — if an emitted number doesn't
   help an on-call shift lead decide what to do, it isn't emitted.
2. **Latency as distribution, not average** — p50 and p95 are exposed
   instead of a mean, because averages hide the outliers that matter.
3. **Cheap in normal operation** — a bounded deque, one lock, O(1) record
   / O(N) snapshot (N bounded by the time window).

Saturation is reported as a best-effort process memory number when
``psutil`` is installed, and as a ``null`` field otherwise — the module
never makes it a hard dependency because the deployment target is a
Streamlit-Cloud-style container where pip-installing extras costs more
than the signal is worth.
"""
from __future__ import annotations

import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque

# Default rolling window — 10 minutes is long enough to smooth over
# per-minute noise, short enough that a fresh deploy's metrics appear in
# under an hour even under steady load.
DEFAULT_WINDOW_SECONDS = 600


@dataclass
class _Event:
    timestamp: float
    route: str
    duration_ms: float
    status_code: int


def _percentile(values: list[float], pct: float) -> float:
    """Linear-interpolated percentile. Returns 0.0 for an empty list so
    callers can display "no data yet" without special-casing ``None``
    throughout the JSON schema."""
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * (pct / 100.0)
    lower = int(k)
    upper = min(lower + 1, len(values) - 1)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (k - lower)


class MetricsCollector:
    """Thread-safe rolling-window collector.

    One instance per FastAPI app. Tests use the ``reset`` method to isolate
    runs; production callers shouldn't need to touch it.
    """

    def __init__(self, window_seconds: int = DEFAULT_WINDOW_SECONDS) -> None:
        self._window = window_seconds
        self._events: Deque[_Event] = deque()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, route: str, duration_ms: float, status_code: int) -> None:
        """Append one request. Called from FastAPI middleware on every hit."""
        now = time.time()
        with self._lock:
            self._events.append(
                _Event(
                    timestamp=now,
                    route=route,
                    duration_ms=duration_ms,
                    status_code=status_code,
                )
            )
            self._prune_locked(now)

    def reset(self) -> None:
        """Drop every recorded event. Tests only."""
        with self._lock:
            self._events.clear()

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """Return the current Four Golden Signals view as a dict."""
        now = time.time()
        with self._lock:
            self._prune_locked(now)
            events = list(self._events)

        # Skip ``/metrics`` itself from the per-route report — a dashboard
        # polling every 30 s would otherwise drown out genuine traffic.
        observable = [e for e in events if e.route != "/metrics"]

        window = self._window
        total = len(observable)
        errors = sum(1 for e in observable if e.status_code >= 500)
        per_route = self._per_route(observable)

        return {
            "window_seconds": window,
            "observed_at": int(now),
            "traffic": {
                "total_requests": total,
                "rps": round(total / window, 4) if window else 0.0,
            },
            "errors": {
                "count": errors,
                "rate": round(errors / total, 4) if total else 0.0,
            },
            "latency_ms": {
                "p50": round(_percentile([e.duration_ms for e in observable], 50), 2),
                "p95": round(_percentile([e.duration_ms for e in observable], 95), 2),
                "p99": round(_percentile([e.duration_ms for e in observable], 99), 2),
            },
            "saturation": _saturation_best_effort(),
            "by_route": per_route,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _prune_locked(self, now: float) -> None:
        """Drop events older than the rolling window. Caller holds the lock."""
        cutoff = now - self._window
        while self._events and self._events[0].timestamp < cutoff:
            self._events.popleft()

    @staticmethod
    def _per_route(events: list[_Event]) -> dict:
        grouped: dict[str, list[_Event]] = {}
        for ev in events:
            grouped.setdefault(ev.route, []).append(ev)

        out: dict[str, dict] = {}
        for route, group in grouped.items():
            durations = [e.duration_ms for e in group]
            errs = sum(1 for e in group if e.status_code >= 500)
            out[route] = {
                "count": len(group),
                "error_count": errs,
                "error_rate": round(errs / len(group), 4) if group else 0.0,
                "latency_ms": {
                    "p50": round(statistics.median(durations), 2),
                    "p95": round(_percentile(durations, 95), 2),
                },
            }
        return out


def _saturation_best_effort() -> dict:
    """Process memory + CPU% when ``psutil`` is installed, otherwise
    ``{"available": false}``. Never raises — if anything goes wrong the
    response is just "no data"."""
    try:
        import psutil  # type: ignore[import-not-found]
    except ImportError:
        return {"available": False, "reason": "psutil not installed"}

    try:
        process = psutil.Process()
        mem = process.memory_info()
        return {
            "available": True,
            "rss_bytes": int(mem.rss),
            "cpu_percent": float(process.cpu_percent(interval=None)),
        }
    except Exception as exc:  # noqa: BLE001 — saturation is best-effort
        return {"available": False, "reason": f"psutil error: {exc}"}
