"""Temperature monitoring and excursion detection."""
import pandas as pd
import yaml
from modules.database import query, scalar


def _get_thresholds():
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    return config["temperature"]["locations"]


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
        excursions = query(f"""
            SELECT location, temperature, recorded_at, recorded_by
            FROM temp_logs
            WHERE location = '{location}'
            AND (temperature < {limits['min']} OR temperature > {limits['max']})
            AND recorded_at >= date('now', '-{days} days')
            ORDER BY recorded_at DESC
        """)
        if not excursions.empty:
            excursions["threshold_min"] = limits["min"]
            excursions["threshold_max"] = limits["max"]
            excursions["severity"] = excursions["temperature"].apply(
                lambda t: "CRITICAL" if abs(t - (limits["min"] + limits["max"]) / 2) > (limits["max"] - limits["min"])
                else "WARNING"
            )
            all_excursions.append(excursions)

    if all_excursions:
        return pd.concat(all_excursions, ignore_index=True)
    return pd.DataFrame(columns=["location", "temperature", "recorded_at", "recorded_by",
                                  "threshold_min", "threshold_max", "severity"])


def get_temperature_trend(location, days=30):
    """Get temperature readings over time for a specific location."""
    return query(f"""
        SELECT temperature, recorded_at
        FROM temp_logs
        WHERE location = '{location}'
        AND recorded_at >= date('now', '-{days} days')
        ORDER BY recorded_at
    """)


def get_compliance_score(days=30):
    """Calculate % of temperature readings within spec."""
    thresholds = _get_thresholds()
    total = 0
    compliant = 0

    for location, limits in thresholds.items():
        total_loc = scalar(f"""
            SELECT COUNT(*) FROM temp_logs
            WHERE location = '{location}'
            AND recorded_at >= date('now', '-{days} days')
        """) or 0

        compliant_loc = scalar(f"""
            SELECT COUNT(*) FROM temp_logs
            WHERE location = '{location}'
            AND temperature >= {limits['min']}
            AND temperature <= {limits['max']}
            AND recorded_at >= date('now', '-{days} days')
        """) or 0

        total += total_loc
        compliant += compliant_loc

    if total > 0:
        return round((compliant / total) * 100, 1)
    return 0.0
