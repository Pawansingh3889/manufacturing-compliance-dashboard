"""Temperature monitoring and excursion detection."""
import os
import pandas as pd
import yaml
from modules.database import query, scalar


def _get_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def _get_thresholds():
    return _get_config()["temperature"]["locations"]


def get_latest_readings():
    """Get the most recent reading for each location."""
    return query("""
        SELECT t1.location, t1.temperature, t1.recorded_at, t1.recorded_by
        FROM temp_logs t1
        INNER JOIN (
            SELECT location, MAX(recorded_at) as max_time
            FROM temp_logs
            GROUP BY location
        ) t2 ON t1.location = t2.location AND t1.recorded_at = t2.max_time
        ORDER BY t1.location
    """)


def get_excursions(days=7):
    """Find all temperature readings outside acceptable ranges."""
    thresholds = _get_thresholds()
    all_excursions = []

    for location, limits in thresholds.items():
        excursions = query(
            "SELECT location, temperature, recorded_at, recorded_by "
            "FROM temp_logs "
            "WHERE location = :loc "
            "AND (temperature < :min_t OR temperature > :max_t) "
            "AND recorded_at >= date('now', :days_ago)",
            {"loc": location, "min_t": limits["min"], "max_t": limits["max"],
             "days_ago": f"-{days} days"}
        )
        if not excursions.empty:
            excursions["threshold_min"] = limits["min"]
            excursions["threshold_max"] = limits["max"]
            mid = (limits["min"] + limits["max"]) / 2
            span = limits["max"] - limits["min"]
            excursions["severity"] = excursions["temperature"].apply(
                lambda t: "CRITICAL" if abs(t - mid) > span else "WARNING"
            )
            all_excursions.append(excursions)

    if all_excursions:
        return pd.concat(all_excursions, ignore_index=True)
    return pd.DataFrame(columns=["location", "temperature", "recorded_at", "recorded_by",
                                  "threshold_min", "threshold_max", "severity"])


def get_temperature_trend(location, days=30):
    """Get temperature readings over time for a specific location."""
    return query(
        "SELECT temperature, recorded_at FROM temp_logs "
        "WHERE location = :loc AND recorded_at >= date('now', :days_ago) "
        "ORDER BY recorded_at",
        {"loc": location, "days_ago": f"-{days} days"}
    )


def get_compliance_score(days=30):
    """Calculate % of temperature readings within spec."""
    thresholds = _get_thresholds()
    total = 0
    compliant = 0

    for location, limits in thresholds.items():
        total_loc = scalar(
            "SELECT COUNT(*) FROM temp_logs "
            "WHERE location = :loc AND recorded_at >= date('now', :days_ago)",
            {"loc": location, "days_ago": f"-{days} days"}
        ) or 0

        compliant_loc = scalar(
            "SELECT COUNT(*) FROM temp_logs "
            "WHERE location = :loc "
            "AND temperature >= :min_t AND temperature <= :max_t "
            "AND recorded_at >= date('now', :days_ago)",
            {"loc": location, "min_t": limits["min"], "max_t": limits["max"],
             "days_ago": f"-{days} days"}
        ) or 0

        total += total_loc
        compliant += compliant_loc

    if total > 0:
        return round((compliant / total) * 100, 1)
    return 0.0
