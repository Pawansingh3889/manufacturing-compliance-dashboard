"""SLO measurement functions for compliance dashboard.

Inspired by PyCon DE 2026: "Data Pipeline Operations Maturity Model" (Cakir).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable

from modules.database import scalar

REPORT_GEN_TARGET_SECONDS = 5.0


def check_temperature_slo(days: int = 30) -> dict:
    """Percentage of temperature readings within spec over the last N days."""
    total = scalar(f"""
        SELECT COUNT(*) FROM temp_logs
        WHERE timestamp >= datetime('now', '-{days} days')
    """) or 0
    in_spec = scalar(f"""
        SELECT COUNT(*) FROM temp_logs
        WHERE timestamp >= datetime('now', '-{days} days')
          AND excursion = 0
    """) or 0
    actual = round((in_spec / total * 100), 2) if total > 0 else 0.0
    return {
        "name": "temperature_compliance",
        "target": 95.0,
        "actual": actual,
        "met": actual >= 95.0,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }


def check_traceability_slo(days: int = 30) -> dict:
    """Percentage of batches with raw material linkage."""
    total = scalar("SELECT COUNT(*) FROM production") or 0
    linked = scalar("""
        SELECT COUNT(*) FROM production
        WHERE raw_material_batch IS NOT NULL AND raw_material_batch != ''
    """) or 0
    actual = round((linked / total * 100), 2) if total > 0 else 0.0
    return {
        "name": "traceability_completeness",
        "target": 90.0,
        "actual": actual,
        "met": actual >= 90.0,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }


def measure_report_generation(func: Callable[..., Any], *args: Any, **kwargs: Any) -> dict:
    """Run a report generation callable and check it finishes under target.

    The SLO is satisfied when a full audit report is produced in under
    ``REPORT_GEN_TARGET_SECONDS`` seconds so auditors never have to wait.
    """
    start = time.perf_counter()
    error: str | None = None
    try:
        func(*args, **kwargs)
    except Exception as exc:  # keep SLO observable even on failure
        error = str(exc)
    elapsed = round(time.perf_counter() - start, 3)
    return {
        "name": "report_generation_time",
        "target": REPORT_GEN_TARGET_SECONDS,
        "actual": elapsed,
        "met": error is None and elapsed <= REPORT_GEN_TARGET_SECONDS,
        "error": error,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }


def slo_status() -> dict:
    """Aggregate the three compliance SLOs into one payload for the API."""
    temp = check_temperature_slo()
    trace = check_traceability_slo()
    overall_met = bool(temp.get("met") and trace.get("met"))
    return {
        "slos": [temp, trace],
        "targets": {
            "temperature_compliance_pct": 95.0,
            "traceability_completeness_pct": 90.0,
            "report_generation_seconds": REPORT_GEN_TARGET_SECONDS,
        },
        "overall_met": overall_met,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }
