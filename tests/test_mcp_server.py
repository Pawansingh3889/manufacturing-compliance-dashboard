"""Tests for the MCP server tool layer.

Tool callables are registered via the FastMCP decorator. We import the
server module and invoke the underlying Python functions through the
``.fn`` attribute (FastMCP) or by calling the wrapped callable directly.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

pytest.importorskip("fastmcp")


def _invoke(tool):
    """Return the underlying callable of a FastMCP tool wrapper."""
    for attr in ("fn", "func", "__wrapped__", "callable"):
        target = getattr(tool, attr, None)
        if callable(target):
            return target
    if callable(tool):
        return tool
    raise AttributeError("Cannot locate underlying callable for tool")


def test_trace_batch_tool_returns_json(monkeypatch):
    import mcp_server

    def fake_trace(code: str):
        return {
            "batch_code": code,
            "found": True,
            "production": pd.DataFrame([{"batch_code": code, "yield_pct": 88.0}]),
            "orders": pd.DataFrame([{"customer": "Customer Alpha"}]),
        }

    monkeypatch.setattr(mcp_server.traceability, "trace_batch", fake_trace)
    raw = _invoke(mcp_server.trace_batch)("F0001A")
    payload = json.loads(raw)
    assert payload["batch_code"] == "F0001A"
    assert payload["found"] is True


def test_excursions_tool_returns_json(monkeypatch):
    import mcp_server

    monkeypatch.setattr(
        mcp_server.temperature,
        "get_excursions",
        lambda days=7: pd.DataFrame([{"location": "Zone A", "temperature": 5.0}]),
    )
    raw = _invoke(mcp_server.get_temperature_excursions)(days=1)
    data = json.loads(raw)
    assert data[0]["location"] == "Zone A"


def test_allergen_matrix_tool(monkeypatch):
    import mcp_server

    monkeypatch.setattr(
        mcp_server.allergens,
        "get_allergen_matrix",
        lambda: pd.DataFrame([{"Product": "Synthetic Fillet", "Fish": "Y"}]),
    )
    raw = _invoke(mcp_server.get_allergen_matrix)()
    data = json.loads(raw)
    assert data[0]["Product"] == "Synthetic Fillet"


def test_compliance_score_tool(monkeypatch):
    import mcp_server

    monkeypatch.setattr(mcp_server.temperature, "get_compliance_score", lambda *a, **kw: 95.0)
    monkeypatch.setattr(mcp_server.traceability, "get_traceability_score", lambda *a, **kw: 92.0)
    monkeypatch.setattr(
        mcp_server,
        "load_config",
        lambda: {
            "scoring": {
                "temperature_weight": 0.5,
                "traceability_weight": 0.5,
                "passing_threshold": 85,
            }
        },
    )
    raw = _invoke(mcp_server.get_compliance_score)()
    data = json.loads(raw)
    assert data["temperature_score"] == 95.0
    assert data["status"] in ("PASS", "FAIL")


def test_expiring_batches_tool(monkeypatch):
    import mcp_server

    monkeypatch.setattr(
        mcp_server.shelf_life,
        "get_expiring_soon",
        lambda days=3: pd.DataFrame([{"batch_code": "F0002A", "days_remaining": 1}]),
    )
    raw = _invoke(mcp_server.get_expiring_batches)(days=3)
    data = json.loads(raw)
    assert data[0]["batch_code"] == "F0002A"


def test_tool_surfaces_exceptions_as_json(monkeypatch):
    import mcp_server

    def boom(*_a, **_kw):
        raise RuntimeError("db down")

    monkeypatch.setattr(mcp_server.temperature, "get_excursions", boom)
    raw = _invoke(mcp_server.get_temperature_excursions)(days=1)
    payload = json.loads(raw)
    assert "error" in payload
