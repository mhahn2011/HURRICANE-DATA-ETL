"""Calculate storm-level intensification metrics."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd


def calculate_intensification_features(track_df: pd.DataFrame) -> dict:
    """
    Calculate storm-level intensification metrics.

    Note: These are STORM-level features (same for all tracts of a given storm)

    Steps:
    1. Calculate 24-hour rolling wind change: max_wind[t] - max_wind[t-24h]
    2. Find maximum intensification rate
    3. Find first time storm reached Cat 4 (113 kt)

    Returns:
        {
            'max_intensification_rate_kt_per_24h': float,
            'time_of_max_intensification': datetime,
            'cat4_first_time': datetime or None
        }
    """
    if track_df.empty:
        return {
            'max_intensification_rate_kt_per_24h': None,
            'time_of_max_intensification': None,
            'cat4_first_time': None,
        }

    df = track_df.sort_values('date').set_index('date')
    df['wind_change'] = df['max_wind'].diff(periods=4)  # Assuming 6-hour intervals

    max_intensification_rate = df['wind_change'].max()
    time_of_max_intensification = df['wind_change'].idxmax()

    cat4_df = df[df['max_wind'] >= 113]
    cat4_first_time = cat4_df.index.min() if not cat4_df.empty else None

    return {
        'max_intensification_rate_kt_per_24h': max_intensification_rate,
        'time_of_max_intensification': time_of_max_intensification,
        'cat4_first_time': cat4_first_time,
    }


def calculate_lead_time(
    cat4_time: datetime,
    nearest_approach_time: datetime
) -> float:
    """
    Calculate warning time between Cat 4 and max impact.

    Positive value = had warning time
    Negative value = storm intensified after passing
    """
    if cat4_time is None or nearest_approach_time is None:
        return None
    return (nearest_approach_time - cat4_time).total_seconds() / 3600.0  # hours