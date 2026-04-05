"""Time-series anomaly detection for temperature monitoring.

Detects temperature excursions using rolling statistics
and z-score based anomaly detection on sensor data.
"""

import pandas as pd
import numpy as np


def detect_anomalies(
    df: pd.DataFrame,
    column: str = "temperature",
    window: int = 24,
    threshold: float = 2.5,
) -> pd.DataFrame:
    """Detect anomalies using rolling z-score method.

    Args:
        df: DataFrame with timestamp index and temperature column
        column: Column to analyze
        window: Rolling window size (number of readings)
        threshold: Z-score threshold for anomaly flag

    Returns:
        DataFrame with added columns: rolling_mean, rolling_std, z_score, is_anomaly
    """
    result = df.copy()
    result["rolling_mean"] = result[column].rolling(window=window, min_periods=1).mean()
    result["rolling_std"] = result[column].rolling(window=window, min_periods=1).std()
    result["z_score"] = (
        (result[column] - result["rolling_mean"]) / result["rolling_std"]
    ).fillna(0)
    result["is_anomaly"] = result["z_score"].abs() > threshold
    return result


def compute_excursion_duration(
    df: pd.DataFrame,
    min_temp: float = 0.0,
    max_temp: float = 5.0,
) -> pd.DataFrame:
    """Calculate duration of temperature excursions outside safe range.

    Args:
        df: DataFrame with timestamp and temperature columns
        min_temp: Minimum safe temperature (Celsius)
        max_temp: Maximum safe temperature (Celsius)

    Returns:
        DataFrame with excursion events, start/end times, and duration
    """
    df = df.sort_values("timestamp")
    df["out_of_range"] = (df["temperature"] < min_temp) | (df["temperature"] > max_temp)
    df["excursion_group"] = (df["out_of_range"] != df["out_of_range"].shift()).cumsum()

    excursions = (
        df[df["out_of_range"]]
        .groupby("excursion_group")
        .agg(
            start_time=("timestamp", "first"),
            end_time=("timestamp", "last"),
            peak_temp=("temperature", lambda x: x.loc[x.abs().idxmax()]),
            readings=("temperature", "count"),
            location=("location", "first"),
        )
        .reset_index(drop=True)
    )
    excursions["duration_minutes"] = (
        (pd.to_datetime(excursions["end_time"]) - pd.to_datetime(excursions["start_time"]))
        .dt.total_seconds() / 60
    ).round(1)
    return excursions


def forecast_trend(
    df: pd.DataFrame,
    column: str = "temperature",
    periods: int = 24,
) -> pd.DataFrame:
    """Simple linear trend forecast for temperature data.

    Args:
        df: DataFrame with timestamp index and temperature column
        column: Column to forecast
        periods: Number of periods to forecast ahead

    Returns:
        DataFrame with forecasted values
    """
    df = df.copy().reset_index(drop=True)
    x = np.arange(len(df))
    y = df[column].values
    mask = ~np.isnan(y)
    if mask.sum() < 2:
        return pd.DataFrame()

    coeffs = np.polyfit(x[mask], y[mask], 1)
    future_x = np.arange(len(df), len(df) + periods)
    forecast = np.polyval(coeffs, future_x)

    return pd.DataFrame({
        "period": range(1, periods + 1),
        "forecast_temp": forecast.round(2),
        "trend_direction": "rising" if coeffs[0] > 0 else "falling",
        "slope_per_reading": round(coeffs[0], 4),
    })
