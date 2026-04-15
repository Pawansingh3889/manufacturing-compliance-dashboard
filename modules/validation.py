"""Declarative data validation for compliance pipeline.

Rules are data (list of dicts), not code. New rules are added by appending
to the list. Inspired by PyCon DE 2026: "Ship Data with Confidence" (Sequeira).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

EU_14_ALLERGENS = frozenset({
    "fish", "crustaceans", "molluscs", "milk", "eggs", "gluten",
    "soya", "sulphites", "mustard", "celery", "sesame", "lupin",
    "nuts", "peanuts",
})


@dataclass
class Violation:
    row: int
    field: str
    rule: str
    value: Any
    message: str


@dataclass
class ValidationResult:
    total_rows: int = 0
    passed_rows: int = 0
    failed_rows: int = 0
    violations: list[Violation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.failed_rows == 0

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.passed_rows}/{self.total_rows} rows passed, {len(self.violations)} violations"


def _check_not_null(series: pd.Series, **_: Any) -> pd.Series:
    return series.notna() & (series.astype(str).str.strip() != "")


def _check_numeric_range(series: pd.Series, *, min_val: float, max_val: float, **_: Any) -> pd.Series:
    num = pd.to_numeric(series, errors="coerce")
    return num.notna() & (num >= min_val) & (num <= max_val)


def _check_positive(series: pd.Series, **_: Any) -> pd.Series:
    num = pd.to_numeric(series, errors="coerce")
    return num.notna() & (num > 0)


def _check_regex(series: pd.Series, *, pattern: str, **_: Any) -> pd.Series:
    pat = re.compile(pattern)
    return series.astype(str).apply(lambda x: bool(pat.match(x)))


def _check_in_set(series: pd.Series, *, allowed: frozenset, **_: Any) -> pd.Series:
    return series.astype(str).str.lower().isin({v.lower() for v in allowed})


def _check_not_future(series: pd.Series, **_: Any) -> pd.Series:
    now = datetime.now(timezone.utc)
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.isna() | (parsed <= now)


_CHECKERS = {
    "not_null": _check_not_null,
    "numeric_range": _check_numeric_range,
    "positive": _check_positive,
    "regex": _check_regex,
    "in_set": _check_in_set,
    "not_future": _check_not_future,
}

TEMPERATURE_RULES = [
    {"field": "temperature", "check": "numeric_range", "min_val": -30.0, "max_val": 30.0},
    {"field": "location", "check": "not_null"},
    {"field": "timestamp", "check": "not_future"},
]

BATCH_RULES = [
    {"field": "batch_code", "check": "regex", "pattern": r"^[DF]\d{4}[A-Z]$"},
    {"field": "raw_input_kg", "check": "positive"},
    {"field": "finished_output_kg", "check": "positive"},
    {"field": "yield_pct", "check": "numeric_range", "min_val": 0.0, "max_val": 100.0},
]

ALLERGEN_RULES = [
    {"field": "name", "check": "not_null"},
]


def validate(df: pd.DataFrame, rules: list[dict]) -> ValidationResult:
    """Run declarative rules against a DataFrame."""
    result = ValidationResult(total_rows=len(df))
    if df.empty:
        return result

    row_failed = pd.Series(False, index=df.index)

    for rule in rules:
        col = rule["field"]
        if col not in df.columns:
            continue

        check_name = rule["check"]
        checker = _CHECKERS.get(check_name)
        if checker is None:
            continue

        params = {k: v for k, v in rule.items() if k not in ("field", "check")}
        mask = checker(df[col], **params)
        failures = ~mask

        for idx in df.index[failures]:
            result.violations.append(Violation(
                row=int(idx),
                field=col,
                rule=check_name,
                value=df.at[idx, col],
                message=f"{col} failed {check_name} check",
            ))
        row_failed = row_failed | failures

    result.failed_rows = int(row_failed.sum())
    result.passed_rows = result.total_rows - result.failed_rows
    return result
