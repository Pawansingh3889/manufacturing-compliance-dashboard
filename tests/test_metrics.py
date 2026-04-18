"""Tests for ``modules.metrics.MetricsCollector``.

Covers the observable contract of the collector independently of the FastAPI
wiring — record / prune / snapshot / per-route breakdown / edge-case shapes.
``/metrics`` endpoint wiring is exercised in ``test_api.py``.
"""
from __future__ import annotations

import time

import pytest

from modules.metrics import MetricsCollector, _percentile


# ---------------------------------------------------------------------------
# Percentile helper
# ---------------------------------------------------------------------------

class TestPercentile:
    def test_empty_list_returns_zero(self) -> None:
        assert _percentile([], 50) == 0.0
        assert _percentile([], 95) == 0.0

    def test_single_value(self) -> None:
        assert _percentile([42.0], 50) == 42.0
        assert _percentile([42.0], 95) == 42.0

    def test_ten_values_p50(self) -> None:
        # Median of 1..10 is between 5 and 6.
        assert _percentile([float(x) for x in range(1, 11)], 50) == pytest.approx(5.5)

    def test_ten_values_p95(self) -> None:
        # p95 of 1..10 sits near the top of the range.
        result = _percentile([float(x) for x in range(1, 11)], 95)
        assert 9.0 < result <= 10.0


# ---------------------------------------------------------------------------
# Recording + snapshot basics
# ---------------------------------------------------------------------------

class TestRecordAndSnapshot:
    def test_fresh_collector_reports_zero_traffic(self) -> None:
        mc = MetricsCollector(window_seconds=60)
        snap = mc.snapshot()
        assert snap["traffic"]["total_requests"] == 0
        assert snap["traffic"]["rps"] == 0.0
        assert snap["errors"]["count"] == 0
        # Latency percentiles return 0 when no data — callers should
        # display "no traffic yet" rather than special-case None.
        assert snap["latency_ms"]["p50"] == 0.0

    def test_record_increases_traffic(self) -> None:
        mc = MetricsCollector(window_seconds=60)
        for _ in range(5):
            mc.record("/health", duration_ms=1.0, status_code=200)
        snap = mc.snapshot()
        assert snap["traffic"]["total_requests"] == 5

    def test_error_rate_counted_on_5xx_not_4xx(self) -> None:
        mc = MetricsCollector(window_seconds=60)
        mc.record("/batches", duration_ms=10.0, status_code=500)
        mc.record("/batches", duration_ms=10.0, status_code=404)  # client error
        mc.record("/batches", duration_ms=10.0, status_code=200)
        snap = mc.snapshot()
        # Only the 500 counts as an error — 404 is caller's mistake.
        assert snap["errors"]["count"] == 1
        assert snap["errors"]["rate"] == pytest.approx(1 / 3, abs=1e-3)

    def test_metrics_endpoint_excluded_from_by_route(self) -> None:
        """``/metrics`` polling must not drown out real traffic."""
        mc = MetricsCollector(window_seconds=60)
        mc.record("/batches", duration_ms=20.0, status_code=200)
        mc.record("/metrics", duration_ms=1.0, status_code=200)
        mc.record("/metrics", duration_ms=1.0, status_code=200)
        snap = mc.snapshot()
        assert "/metrics" not in snap["by_route"]
        assert "/batches" in snap["by_route"]
        # Top-level traffic also ignores /metrics calls.
        assert snap["traffic"]["total_requests"] == 1


# ---------------------------------------------------------------------------
# Window pruning
# ---------------------------------------------------------------------------

class TestWindowPruning:
    def test_old_events_dropped_on_snapshot(self) -> None:
        mc = MetricsCollector(window_seconds=1)
        mc.record("/health", duration_ms=1.0, status_code=200)
        time.sleep(1.1)
        mc.record("/health", duration_ms=1.0, status_code=200)
        snap = mc.snapshot()
        # Only the second record survived the window.
        assert snap["traffic"]["total_requests"] == 1


# ---------------------------------------------------------------------------
# Per-route breakdown
# ---------------------------------------------------------------------------

class TestPerRoute:
    def test_routes_aggregated_separately(self) -> None:
        mc = MetricsCollector(window_seconds=60)
        mc.record("/a", duration_ms=10.0, status_code=200)
        mc.record("/a", duration_ms=12.0, status_code=200)
        mc.record("/b", duration_ms=99.0, status_code=500)
        snap = mc.snapshot()
        assert snap["by_route"]["/a"]["count"] == 2
        assert snap["by_route"]["/a"]["error_count"] == 0
        assert snap["by_route"]["/b"]["count"] == 1
        assert snap["by_route"]["/b"]["error_count"] == 1
        assert snap["by_route"]["/b"]["error_rate"] == 1.0

    def test_per_route_latency_reflects_actual_durations(self) -> None:
        mc = MetricsCollector(window_seconds=60)
        for d in (5.0, 10.0, 20.0, 80.0, 200.0):
            mc.record("/slow", duration_ms=d, status_code=200)
        snap = mc.snapshot()
        # Median of those five values is 20.
        assert snap["by_route"]["/slow"]["latency_ms"]["p50"] == 20.0
        # p95 sits near the 200 outlier, not near the median.
        assert snap["by_route"]["/slow"]["latency_ms"]["p95"] > 80.0


# ---------------------------------------------------------------------------
# Saturation
# ---------------------------------------------------------------------------

class TestSaturation:
    def test_saturation_field_always_present(self) -> None:
        """Whether psutil is installed or not, the key must be there so
        dashboards don't crash on missing fields."""
        mc = MetricsCollector(window_seconds=60)
        snap = mc.snapshot()
        assert "saturation" in snap
        assert "available" in snap["saturation"]
        assert isinstance(snap["saturation"]["available"], bool)


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_events(self) -> None:
        mc = MetricsCollector(window_seconds=60)
        mc.record("/health", duration_ms=1.0, status_code=200)
        mc.reset()
        snap = mc.snapshot()
        assert snap["traffic"]["total_requests"] == 0
