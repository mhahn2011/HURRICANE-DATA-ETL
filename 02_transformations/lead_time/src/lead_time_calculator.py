"""Lead time feature calculator for hurricane warning time analysis.

Calculates warning lead times by measuring the interval between when a storm
first reached various Saffir-Simpson category thresholds and when it made
closest approach to each census tract.

Positive lead times indicate warning time; negative values indicate the storm
intensified after passing the tract.
"""

from typing import Dict, Optional
import pandas as pd
from datetime import datetime


# Saffir-Simpson Hurricane Wind Scale thresholds (knots)
CATEGORY_THRESHOLDS = {
    'cat1': 64,   # Tropical Storm -> Category 1 Hurricane
    'cat2': 83,   # Category 1 -> Category 2
    'cat3': 96,   # Category 2 -> Category 3 (Major Hurricane)
    'cat4': 113,  # Category 3 -> Category 4
    'cat5': 137   # Category 4 -> Category 5
}


def find_category_threshold_time(
    track_df: pd.DataFrame,
    threshold_kt: int
) -> Optional[pd.Timestamp]:
    """Find the first time a storm reached a given wind speed threshold.

    Args:
        track_df: Storm track DataFrame with 'date' and 'max_wind' columns
        threshold_kt: Wind speed threshold in knots

    Returns:
        First timestamp when max_wind >= threshold_kt, or None if never reached

    Example:
        >>> track = pd.DataFrame({
        ...     'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 12:00']),
        ...     'max_wind': [80, 115]
        ... })
        >>> find_category_threshold_time(track, 113)  # Cat 4
        Timestamp('2021-08-28 12:00:00')
    """

    # Filter to observations where wind >= threshold
    threshold_obs = track_df[track_df['max_wind'] >= threshold_kt]

    if threshold_obs.empty:
        return None

    # Return earliest observation
    return threshold_obs['date'].min()


def calculate_lead_times(
    track_df: pd.DataFrame,
    nearest_approach_time: pd.Timestamp
) -> Dict[str, Optional[float]]:
    """Calculate lead times for all Saffir-Simpson category thresholds.

    Lead time = time between storm reaching category threshold and closest approach.

    Args:
        track_df: Storm track DataFrame with 'date' and 'max_wind' columns
        nearest_approach_time: Time when storm made closest approach to tract

    Returns:
        Dictionary with lead time in hours for each category:
        {
            'lead_time_cat1_hours': float or None,
            'lead_time_cat2_hours': float or None,
            'lead_time_cat3_hours': float or None,
            'lead_time_cat4_hours': float or None,
            'lead_time_cat5_hours': float or None
        }

    Interpretation:
        - Positive: Tract had warning time after threshold was reached
        - Negative: Storm intensified to category after passing tract
        - None: Storm never reached that category

    Example for Hurricane Ida at New Orleans (landfall 2021-08-29 18:00):
        {
            'lead_time_cat1_hours': 48.5,   # ~2 days warning after Cat 1
            'lead_time_cat2_hours': 42.0,
            'lead_time_cat3_hours': 36.5,
            'lead_time_cat4_hours': 12.0,   # Only 12 hours after Cat 4
            'lead_time_cat5_hours': None    # Never reached Cat 5 (peaked at 130kt)
        }
    """

    lead_times = {}

    for category, threshold_kt in CATEGORY_THRESHOLDS.items():
        # Find when storm first reached this category
        threshold_time = find_category_threshold_time(track_df, threshold_kt)

        if threshold_time is None:
            # Storm never reached this category
            lead_times[f'lead_time_{category}_hours'] = None
        else:
            # Calculate time difference in hours
            time_diff = nearest_approach_time - threshold_time
            lead_time_hours = time_diff.total_seconds() / 3600.0

            lead_times[f'lead_time_{category}_hours'] = lead_time_hours

    return lead_times


def validate_lead_times(lead_times: Dict[str, Optional[float]]) -> bool:
    """Validate lead time calculations for logical consistency.

    Checks:
    1. Higher categories should have shorter lead times (storm intensifies over time)
    2. If a category is None, all higher categories should also be None

    Args:
        lead_times: Dictionary from calculate_lead_times()

    Returns:
        True if lead times are logically consistent, False otherwise

    Note:
        This is a sanity check. Some edge cases (e.g., storm weakening and
        re-intensifying) may legitimately fail these checks.
    """

    categories = ['cat1', 'cat2', 'cat3', 'cat4', 'cat5']
    values = [lead_times[f'lead_time_{cat}_hours'] for cat in categories]

    # Check 1: If a category is None, all higher categories should be None
    found_none = False
    for val in values:
        if found_none and val is not None:
            return False  # Found non-None after None
        if val is None:
            found_none = True

    # Check 2: Non-None lead times should generally decrease
    # (allow some tolerance for observation timing)
    non_none_values = [v for v in values if v is not None]
    if len(non_none_values) >= 2:
        for i in range(len(non_none_values) - 1):
            # Allow 6-hour tolerance for observation timing
            if non_none_values[i] < non_none_values[i + 1] - 6.0:
                return False  # Lead time increased significantly (unlikely)

    return True
