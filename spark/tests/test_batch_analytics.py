"""Unit tests for compliance batch analytics."""

from pyspark.sql import Row

from spark.batch_analytics import (
    compute_daily_production,
    compute_shelf_life_risk,
    compute_temperature_report,
    compute_yield_analysis,
)


def _batch(**overrides):
    defaults = {
        "id": 1, "batch_code": "B-001", "production_date": "2026-03-15",
        "use_by_date": "2026-03-20", "shift": "morning", "line_number": 1,
        "raw_input_kg": 100.0, "finished_output_kg": 85.0, "waste_kg": 15.0,
        "yield_pct": 85.0, "age_days": 3, "life_days": 7,
        "status": "released", "alert_flag": False, "concession_required": False,
    }
    defaults.update(overrides)
    return Row(**defaults)


def _temp_log(**overrides):
    defaults = {
        "id": 1, "location": "Chiller-A", "temperature": 3.5,
        "timestamp": "2026-03-15 08:00:00", "recorded_by": "sensor-01",
        "is_excursion": False,
    }
    defaults.update(overrides)
    return Row(**defaults)


class TestYieldAnalysis:
    def test_calculates_waste_pct(self, spark):
        rows = [_batch(raw_input_kg=100, waste_kg=10, yield_pct=90)]
        df = spark.createDataFrame(rows)
        result = compute_yield_analysis(df)
        row = result.first()
        assert row["waste_pct"] == 10.0

    def test_groups_by_shift_and_line(self, spark):
        rows = [
            _batch(shift="morning", line_number=1),
            _batch(id=2, batch_code="B-002", shift="afternoon", line_number=2),
        ]
        df = spark.createDataFrame(rows)
        result = compute_yield_analysis(df)
        assert result.count() == 2

    def test_skips_zero_input(self, spark):
        rows = [_batch(raw_input_kg=0.0)]
        df = spark.createDataFrame(rows)
        result = compute_yield_analysis(df)
        assert result.count() == 0


class TestTemperatureReport:
    def test_calculates_excursion_rate(self, spark):
        rows = [
            _temp_log(is_excursion=False),
            _temp_log(id=2, is_excursion=False),
            _temp_log(id=3, is_excursion=True),
        ]
        df = spark.createDataFrame(rows)
        result = compute_temperature_report(df)
        row = result.first()
        assert row["excursion_rate_pct"] == 33.33
        assert row["total_readings"] == 3

    def test_groups_by_location(self, spark):
        rows = [
            _temp_log(location="Chiller-A"),
            _temp_log(id=2, location="Chiller-B"),
        ]
        df = spark.createDataFrame(rows)
        result = compute_temperature_report(df)
        assert result.count() == 2


class TestShelfLifeRisk:
    def test_flags_expired(self, spark):
        rows = [_batch(age_days=10, life_days=7)]
        df = spark.createDataFrame(rows)
        result = compute_shelf_life_risk(df)
        assert result.first()["risk_level"] == "EXPIRED"

    def test_flags_critical(self, spark):
        rows = [_batch(age_days=6, life_days=7)]
        df = spark.createDataFrame(rows)
        result = compute_shelf_life_risk(df)
        assert result.first()["risk_level"] == "CRITICAL"

    def test_skips_ok_batches(self, spark):
        rows = [_batch(age_days=1, life_days=14)]
        df = spark.createDataFrame(rows)
        result = compute_shelf_life_risk(df)
        assert result.count() == 0


class TestDailyProduction:
    def test_computes_quality_rate(self, spark):
        rows = [_batch(finished_output_kg=85, waste_kg=15)]
        df = spark.createDataFrame(rows)
        result = compute_daily_production(df)
        row = result.first()
        assert row["quality_rate"] == 0.85

    def test_counts_alerts(self, spark):
        rows = [
            _batch(alert_flag=True),
            _batch(id=2, batch_code="B-002", alert_flag=True),
            _batch(id=3, batch_code="B-003", alert_flag=False),
        ]
        df = spark.createDataFrame(rows)
        result = compute_daily_production(df)
        assert result.first()["alert_count"] == 2
