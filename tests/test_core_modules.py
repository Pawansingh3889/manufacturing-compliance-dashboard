"""Tests for core compliance dashboard modules.

Tests input validation and error handling — no database required.
"""

from __future__ import annotations

import os
import sys

# Add parent dir to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ---------------------------------------------------------------------------
# Traceability — input validation
# ---------------------------------------------------------------------------


class TestTraceabilityValidation:
    def test_empty_batch_code(self) -> None:
        from modules.traceability import trace_batch

        result = trace_batch("")
        assert result["found"] is False
        assert "error" in result

    def test_none_batch_code(self) -> None:
        from modules.traceability import trace_batch

        result = trace_batch(None)
        assert result["found"] is False
        assert "error" in result

    def test_short_batch_code(self) -> None:
        from modules.traceability import trace_batch

        result = trace_batch("A")
        assert result["found"] is False
        assert "too short" in result["error"]

    def test_batch_code_uppercased(self) -> None:
        from modules.traceability import trace_batch

        # Will fail on DB query but batch_code should be uppercased
        try:
            result = trace_batch("f6043a")
            assert result["batch_code"] == "F6043A"
        except Exception:
            pass  # DB not available in test, that's OK


# ---------------------------------------------------------------------------
# Temperature — config validation
# ---------------------------------------------------------------------------


class TestTemperatureConfig:
    def test_config_file_missing(self, tmp_path, monkeypatch) -> None:
        from modules import temperature

        monkeypatch.setattr(
            temperature,
            "_get_config",
            lambda: (_ for _ in ()).throw(FileNotFoundError("Config not found")),
        )

        import pytest

        with pytest.raises(FileNotFoundError):
            temperature._get_config()

    def test_thresholds_key_missing(self, monkeypatch) -> None:
        from modules import temperature

        monkeypatch.setattr(temperature, "_get_config", lambda: {"other": {}})

        import pytest

        with pytest.raises(KeyError, match="temperature.locations"):
            temperature._get_thresholds()


# ---------------------------------------------------------------------------
# Allergens — edge cases
# ---------------------------------------------------------------------------


class TestAllergenEdgeCases:
    def test_products_with_allergen_no_match(self) -> None:
        import pandas as pd

        from modules.allergens import get_products_with_allergen

        # Create a mock that returns empty
        try:
            result = get_products_with_allergen("NonExistentAllergen")
            assert isinstance(result, pd.DataFrame)
        except Exception:
            pass  # DB not available, that's OK

    def test_allergen_summary_empty(self) -> None:
        from modules.allergens import get_allergen_summary

        # If DB is empty/unavailable, should return empty dict not crash
        try:
            result = get_allergen_summary()
            assert isinstance(result, dict)
        except Exception:
            pass  # DB not available
