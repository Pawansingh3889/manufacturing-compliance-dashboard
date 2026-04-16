"""Tests for traceability.trace_batch and scoring."""
from __future__ import annotations

import pandas as pd


def test_empty_batch_code_returns_error():
    from modules.traceability import trace_batch

    result = trace_batch("")
    assert result["found"] is False
    assert "error" in result


def test_none_batch_code_returns_error():
    from modules.traceability import trace_batch

    result = trace_batch(None)
    assert result["found"] is False
    assert "error" in result


def test_short_batch_code_returns_error():
    from modules.traceability import trace_batch

    result = trace_batch("A")
    assert result["found"] is False
    assert "too short" in result["error"].lower()


def test_trace_batch_uppercases_and_finds_production(patched_db):
    from modules.traceability import trace_batch

    result = trace_batch("f0001a")
    assert result["batch_code"] == "F0001A"
    assert result["found"] is True
    assert "production" in result
    assert not result["production"].empty


def test_trace_batch_links_raw_materials_and_orders(patched_db):
    from modules.traceability import trace_batch

    result = trace_batch("F0001A")
    assert result["found"] is True
    assert isinstance(result["raw_materials"], pd.DataFrame)
    assert isinstance(result["orders"], pd.DataFrame)
    assert any(result["orders"]["customer"].str.contains("Customer"))


def test_trace_batch_not_found_returns_empty(patched_db):
    from modules.traceability import trace_batch

    result = trace_batch("ZZZZZZ")
    assert result["found"] is False


def test_traceability_score_handles_zero_rows(monkeypatch):
    from modules import traceability

    calls = iter([0, 0])
    monkeypatch.setattr(traceability, "scalar", lambda *a, **kw: next(calls))
    assert traceability.get_traceability_score() == 0.0


def test_traceability_score_computes_percentage(monkeypatch):
    from modules import traceability

    calls = iter([10, 9])
    monkeypatch.setattr(traceability, "scalar", lambda *a, **kw: next(calls))
    assert traceability.get_traceability_score() == 90.0
