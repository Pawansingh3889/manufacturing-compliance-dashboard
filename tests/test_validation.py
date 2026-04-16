"""Tests for the declarative data validation module."""
from __future__ import annotations

import pandas as pd

from modules.validation import (
    BATCH_RULES,
    TEMPERATURE_RULES,
    ValidationResult,
    Violation,
    validate,
)


def test_empty_dataframe_passes():
    result = validate(pd.DataFrame(), BATCH_RULES)
    assert isinstance(result, ValidationResult)
    assert result.total_rows == 0
    assert result.passed
    assert result.violations == []


def test_temperature_rules_flag_out_of_range():
    df = pd.DataFrame(
        [
            {"temperature": -5.0, "location": "Zone A", "timestamp": "2026-01-02T12:00"},
            {"temperature": 120.0, "location": "Zone A", "timestamp": "2026-01-02T12:00"},
            {"temperature": 1.5, "location": "Zone A", "timestamp": "2026-01-02T12:00"},
        ]
    )
    result = validate(df, TEMPERATURE_RULES)
    assert result.total_rows == 3
    assert result.failed_rows == 1
    assert result.passed_rows == 2
    assert any(v.rule == "numeric_range" for v in result.violations)


def test_temperature_rules_flag_missing_location():
    df = pd.DataFrame([{"temperature": 1.0, "location": "", "timestamp": "2026-01-02T12:00"}])
    result = validate(df, TEMPERATURE_RULES)
    assert result.failed_rows == 1
    assert any(v.field == "location" for v in result.violations)


def test_batch_rules_regex_fires():
    df = pd.DataFrame(
        [
            {"batch_code": "F1234A", "raw_input_kg": 100.0, "finished_output_kg": 90.0, "yield_pct": 90.0},
            {"batch_code": "lowercase", "raw_input_kg": 100.0, "finished_output_kg": 90.0, "yield_pct": 90.0},
        ]
    )
    result = validate(df, BATCH_RULES)
    assert result.failed_rows == 1
    bad = [v for v in result.violations if v.rule == "regex"]
    assert bad and bad[0].value == "lowercase"


def test_positive_and_range_checks():
    df = pd.DataFrame(
        [
            {"batch_code": "F1234A", "raw_input_kg": 0.0, "finished_output_kg": 5.0, "yield_pct": 50.0},
            {"batch_code": "F2345B", "raw_input_kg": 5.0, "finished_output_kg": 5.0, "yield_pct": 150.0},
        ]
    )
    result = validate(df, BATCH_RULES)
    rules_triggered = {v.rule for v in result.violations}
    assert "positive" in rules_triggered
    assert "numeric_range" in rules_triggered


def test_missing_column_is_skipped():
    df = pd.DataFrame([{"temperature": 2.0}])
    result = validate(df, TEMPERATURE_RULES)
    assert result.total_rows == 1
    # Only the temperature rule should be evaluated; row should pass.
    assert result.passed


def test_summary_string_is_informative():
    result = ValidationResult(total_rows=10, passed_rows=7, failed_rows=3, violations=[
        Violation(row=0, field="x", rule="not_null", value=None, message="x failed"),
    ])
    summary = result.summary()
    assert "FAIL" in summary
    assert "7/10" in summary
    assert "1 violation" in summary


def test_unknown_check_name_is_noop():
    rules = [{"field": "x", "check": "not_a_real_check"}]
    df = pd.DataFrame([{"x": 1}])
    result = validate(df, rules)
    assert result.passed
