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

    return TestClient(api.app)


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
