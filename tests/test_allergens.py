"""Tests for the allergen matrix module."""
from __future__ import annotations

import pandas as pd


def _fake_products() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"id": 1, "name": "Synthetic Fillet", "species": "Salmon", "category": "Fresh", "allergens": "Fish"},
            {"id": 2, "name": "Synthetic Portion", "species": "Cod", "category": "Defrost", "allergens": "Fish, Sulphites"},
            {"id": 3, "name": "Plain Mix", "species": "N/A", "category": "Ambient", "allergens": ""},
        ]
    )


def test_get_allergen_matrix_builds_columns(monkeypatch):
    from modules import allergens

    monkeypatch.setattr(allergens, "query", lambda *a, **kw: _fake_products())

    matrix = allergens.get_allergen_matrix()
    assert not matrix.empty
    assert "Fish" in matrix.columns
    assert "Sulphites" in matrix.columns
    assert "Total Allergens" in matrix.columns
    fillet_row = matrix[matrix["Product"] == "Synthetic Fillet"].iloc[0]
    assert fillet_row["Fish"] == "Y"
    assert fillet_row["Sulphites"] == ""
    assert fillet_row["Total Allergens"] == 1


def test_get_allergen_matrix_empty_when_no_products(monkeypatch):
    from modules import allergens

    monkeypatch.setattr(allergens, "query", lambda *a, **kw: pd.DataFrame())
    assert allergens.get_allergen_matrix().empty


def test_get_allergen_matrix_handles_query_failure(monkeypatch):
    from modules import allergens

    def _boom(*_a, **_kw):
        raise RuntimeError("db down")

    monkeypatch.setattr(allergens, "query", _boom)
    # The module swallows query errors and returns an empty frame.
    assert allergens.get_allergen_matrix().empty


def test_get_allergen_summary_counts(monkeypatch):
    from modules import allergens

    monkeypatch.setattr(allergens, "query", lambda *a, **kw: _fake_products())
    summary = allergens.get_allergen_summary()
    assert summary["Fish"] == 2
    assert summary["Sulphites"] == 1


def test_get_products_with_allergen_filters(monkeypatch):
    from modules import allergens

    monkeypatch.setattr(allergens, "query", lambda *a, **kw: _fake_products())
    result = allergens.get_products_with_allergen("Sulphites")
    assert len(result) == 1
    assert result.iloc[0]["name"] == "Synthetic Portion"
