"""SLO measurement functions for compliance dashboard.

Inspired by PyCon DE 2026: "Data Pipeline Operations Maturity Model" (Cakir).
"""
from __future__ import annotations

from datetime import datetime, timezone

from modules.database import scalar


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
