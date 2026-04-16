"""Tests for shelf life, concession and batch code decoding."""
from __future__ import annotations

import pandas as pd

from modules.shelf_life import decode_batch_code


def test_decode_batch_code_fresh():
    info = decode_batch_code("F6001A")
    assert info is not None
    assert info["product_type"] == "Fresh"
    assert info["julian_day"] == 1
    assert info["shelf_life_days"] == 19
    assert info["year"] == 2026


def test_decode_batch_code_defrost():
    info = decode_batch_code("D6050C")
    assert info is not None
    assert info["product_type"] == "Defrost"
    assert info["julian_day"] == 50
    assert info["shelf_life_days"] == 11


def test_decode_batch_code_rejects_invalid_prefix():
    assert decode_batch_code("Z6001A") is None


def test_decode_batch_code_rejects_too_short():
    assert decode_batch_code("F6") is None


def test_decode_batch_code_case_insensitive():
    assert decode_batch_code("f6001a") == decode_batch_code("F6001A")


def test_get_expiring_soon_delegates_to_query(monkeypatch):
    from modules import shelf_life

    captured = {}

    def fake_query(sql, params=None):
        captured["params"] = params
        return pd.DataFrame([{"batch_code": "F0001A", "days_remaining": 2}])

    monkeypatch.setattr(shelf_life, "query", fake_query)
    df = shelf_life.get_expiring_soon(days_ahead=3)
    assert not df.empty
    assert captured["params"] == {"ahead": "+3 days"}


def test_get_shelf_life_summary_handles_zero(monkeypatch):
    from modules import shelf_life

    values = iter([0, 0])
    monkeypatch.setattr(shelf_life, "scalar", lambda *a, **kw: next(values))
    summary = shelf_life.get_shelf_life_summary()
    assert summary["total_batches"] == 0
    assert summary["compliance_pct"] == 100.0


def test_get_shelf_life_summary_computes_percentage(monkeypatch):
    from modules import shelf_life

    values = iter([10, 2])
    monkeypatch.setattr(shelf_life, "scalar", lambda *a, **kw: next(values))
    summary = shelf_life.get_shelf_life_summary()
    assert summary["total_batches"] == 10
    assert summary["concessions"] == 2
    assert summary["within_spec"] == 8
    assert summary["compliance_pct"] == 80.0
