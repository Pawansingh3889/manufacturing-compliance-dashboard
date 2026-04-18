"""Tests for the FastAPI extended endpoints.

These tests use FastAPI's TestClient and monkeypatch the underlying modules
so the API layer is exercised without needing a populated SQLite file.
"""
from __future__ import annotations

import pandas as pd
import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
TestClient = fastapi_testclient.TestClient


@pytest.fixture
def client():
    import api  # imports the FastAPI app

    # Reset metrics between tests so one test's traffic doesn't pollute
    # another's assertions when they check totals.
    api.metrics_collector.reset()
    return TestClient(api.app)


# ---------------------------------------------------------------------------
# /metrics — Four Golden Signals endpoint (Stefan Dienst, PyCon DE 2026)
# ---------------------------------------------------------------------------


def test_metrics_endpoint_returns_expected_schema(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    for key in ("window_seconds", "observed_at", "traffic", "errors",
                "latency_ms", "saturation", "by_route"):
        assert key in data, f"missing top-level key: {key}"
    for key in ("p50", "p95", "p99"):
        assert key in data["latency_ms"]


def test_metrics_endpoint_reflects_prior_requests(client):
    # Drive some traffic, then check /metrics saw it.
    client.get("/health")
    client.get("/health")
    client.get("/health")

    data = client.get("/metrics").json()
    # /metrics itself is excluded from the per-route breakdown, but /health
    # should appear with count >= 3.
    assert "/health" in data["by_route"]
    assert data["by_route"]["/health"]["count"] >= 3


def test_metrics_records_error_on_unknown_batch(monkeypatch, client):
    """A 5xx response must register in the error counter — the signal an
    on-call reader needs to decide "something is broken now"."""
    # Force an unexpected exception to produce a 500 via the global handler.
    from modules import traceability

    def blow_up(code: str):
        raise RuntimeError("simulated backend failure")

    monkeypatch.setattr(traceability, "trace_batch", blow_up)
    resp = client.get("/batches/NO_SUCH/trace")
    assert resp.status_code == 500

    data = client.get("/metrics").json()
    assert data["errors"]["count"] >= 1
    # The failing route should show up in the per-route breakdown with
    # error_count > 0.
    failing = {r: v for r, v in data["by_route"].items() if v["error_count"] > 0}
    assert failing, "/metrics should isolate the failing route"


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert "status" in payload
    assert "db_connected" in payload


def test_compliance_score_endpoint(monkeypatch, client):
    from modules import temperature, traceability

    monkeypatch.setattr(temperature, "get_compliance_score", lambda *a, **kw: 98.0)
    monkeypatch.setattr(traceability, "get_traceability_score", lambda *a, **kw: 91.0)

    response = client.get("/compliance/score")
    assert response.status_code == 200
    data = response.json()
    assert data["temperature_score"] == 98.0
    assert data["traceability_score"] == 91.0
    assert data["status"] in ("PASS", "FAIL")


def test_batches_trace_404_on_unknown(monkeypatch, client):
    from modules import traceability

    monkeypatch.setattr(
        traceability,
        "trace_batch",
        lambda code: {"batch_code": code, "found": False, "error": "not found"},
    )
    response = client.get("/batches/XXXXXX/trace")
    assert response.status_code == 404


def test_batches_trace_ok(monkeypatch, client):
    from modules import traceability

    def fake_trace(code: str):
        return {
            "batch_code": code,
            "found": True,
            "production": pd.DataFrame([{"batch_code": code, "yield_pct": 88.0}]),
            "raw_materials": pd.DataFrame([{"batch_code": "RM-1"}]),
            "orders": pd.DataFrame([{"customer": "Customer Alpha"}]),
        }

    monkeypatch.setattr(traceability, "trace_batch", fake_trace)
    response = client.get("/batches/F0001A/trace")
    assert response.status_code == 200
    data = response.json()
    assert data["batch_code"] == "F0001A"
    assert data["production"][0]["yield_pct"] == 88.0


def test_allergens_matrix_endpoint(monkeypatch, client):
    from modules import allergens

    monkeypatch.setattr(
        allergens,
        "get_allergen_matrix",
        lambda *a, **kw: pd.DataFrame([{"Product": "Synthetic Fillet", "Fish": "Y", "Total Allergens": 1}]),
    )
    response = client.get("/allergens/matrix")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["Product"] == "Synthetic Fillet"


def test_batches_expiring_endpoint(monkeypatch, client):
    from modules import shelf_life

    monkeypatch.setattr(
        shelf_life,
        "get_expiring_soon",
        lambda days_ahead=3: pd.DataFrame([{"batch_code": "F0002A", "days_remaining": 2}]),
    )
    response = client.get("/shelf-life/expiring?days=5")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["batch_code"] == "F0002A"


def test_slo_status_endpoint(monkeypatch, client):
    from modules import slo

    monkeypatch.setattr(
        slo,
        "slo_status",
        lambda: {"slos": [], "targets": {}, "overall_met": True, "measured_at": "now"},
    )
    response = client.get("/slo/status")
    assert response.status_code == 200
    assert response.json()["overall_met"] is True


def test_compliance_score_handles_module_exception(monkeypatch, client):
    from modules import temperature

    def _boom(*_a, **_kw):
        raise RuntimeError("db down")

    monkeypatch.setattr(temperature, "get_compliance_score", _boom)
    response = client.get("/compliance/score")
    assert response.status_code == 500
