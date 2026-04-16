"""Tests for the temperature module using the in-memory SQLite fixture."""
from __future__ import annotations

import pandas as pd
import pytest


def test_get_excursions_returns_only_out_of_range(patched_db, monkeypatch):
    from modules import temperature

    # Stub config loader so tests don't depend on config.yaml details.
    monkeypatch.setattr(
        temperature,
        "_get_thresholds",
        lambda: {
            "Zone A": {"min": -1.0, "max": 1.0},
            "Zone D": {"min": -22.0, "max": -18.0},
        },
    )

    # Replace the query function with one that accepts the synthetic SQL
    # dialect used by temperature.py (no recorded_at date filter in SQLite).
    def _simple_query(sql, params):
        df = pd.read_sql_query(
            "SELECT location, temperature, recorded_at, recorded_by FROM temp_logs WHERE location = ?",
            patched_db,
            params=(params["loc"],),
        )
        return df[(df["temperature"] < params["min_t"]) | (df["temperature"] > params["max_t"])]

    monkeypatch.setattr(temperature, "query", _simple_query)

    result = temperature.get_excursions(days=30)
    assert not result.empty
    locations = set(result["location"].tolist())
    assert "Zone A" in locations  # 3.5 reading flagged
    assert "Zone D" in locations  # -10.0 reading flagged


def test_get_compliance_score_handles_empty(monkeypatch, patched_db):
    from modules import temperature

    monkeypatch.setattr(temperature, "_get_thresholds", lambda: {"Nonexistent": {"min": 0.0, "max": 1.0}})
    monkeypatch.setattr(temperature, "scalar", lambda *a, **kw: 0)

    assert temperature.get_compliance_score() == 0.0


def test_get_compliance_score_percentage(monkeypatch):
    from modules import temperature

    monkeypatch.setattr(temperature, "_get_thresholds", lambda: {"Zone A": {"min": 0.0, "max": 4.0}})

    values = iter([10, 9, 10, 9])  # total=10, compliant=9 per call pair

    def fake_scalar(sql, params=None):
        return next(values)

    monkeypatch.setattr(temperature, "scalar", fake_scalar)
    assert temperature.get_compliance_score() == 90.0


def test_thresholds_missing_keys_raise(monkeypatch):
    from modules import temperature

    monkeypatch.setattr(temperature, "_get_config", lambda: {"temperature": {}})
    with pytest.raises(KeyError):
        temperature._get_thresholds()
