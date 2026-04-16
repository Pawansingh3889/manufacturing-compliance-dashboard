"""Tests for the service level objective module."""
from __future__ import annotations

import time

from modules import slo


def test_measure_report_generation_meets_target():
    result = slo.measure_report_generation(lambda: None)
    assert result["name"] == "report_generation_time"
    assert result["target"] == slo.REPORT_GEN_TARGET_SECONDS
    assert result["met"] is True
    assert result["error"] is None
    assert result["actual"] >= 0.0


def test_measure_report_generation_captures_exception():
    def boom() -> None:
        raise RuntimeError("report broken")

    result = slo.measure_report_generation(boom)
    assert result["met"] is False
    assert result["error"] == "report broken"


def test_measure_report_generation_flags_slow_runs(monkeypatch):
    # Force the clock forward so a trivial call looks slow.
    times = iter([0.0, slo.REPORT_GEN_TARGET_SECONDS + 1.0])
    monkeypatch.setattr(time, "perf_counter", lambda: next(times))
    result = slo.measure_report_generation(lambda: None)
    assert result["met"] is False
    assert result["actual"] > slo.REPORT_GEN_TARGET_SECONDS


def test_slo_status_aggregates(monkeypatch):
    monkeypatch.setattr(slo, "check_temperature_slo", lambda: {"name": "temp", "met": True, "target": 95.0, "actual": 99.0})
    monkeypatch.setattr(slo, "check_traceability_slo", lambda: {"name": "trace", "met": True, "target": 90.0, "actual": 92.0})

    payload = slo.slo_status()
    assert payload["overall_met"] is True
    assert payload["targets"]["report_generation_seconds"] == slo.REPORT_GEN_TARGET_SECONDS
    assert len(payload["slos"]) == 2


def test_slo_status_marks_failure_when_any_slo_fails(monkeypatch):
    monkeypatch.setattr(slo, "check_temperature_slo", lambda: {"name": "temp", "met": False, "target": 95.0, "actual": 50.0})
    monkeypatch.setattr(slo, "check_traceability_slo", lambda: {"name": "trace", "met": True, "target": 90.0, "actual": 92.0})

    payload = slo.slo_status()
    assert payload["overall_met"] is False
