"""Unit tests for intensification features."""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "03_integration" / "src"))

from intensification_features import calculate_intensification_features


def test_max_intensification_detection():
    """Correctly identify rapid intensification events"""
    track = pd.DataFrame({
        'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 06:00', '2021-08-28 12:00', '2021-08-28 18:00', '2021-08-29 00:00']),
        'max_wind': [60, 70, 80, 90, 110],
    })
    features = calculate_intensification_features(track)
    assert features['max_intensification_rate_kt_per_24h'] == 50
    assert features['time_of_max_intensification'] == pd.to_datetime('2021-08-29 00:00')


def test_cat4_threshold_detection():
    """Find first time storm reaches Cat 4"""
    track = pd.DataFrame({
        'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 06:00', '2021-08-28 12:00', '2021-08-28 18:00']),
        'max_wind': [100, 110, 115, 120],
    })
    features = calculate_intensification_features(track)
    assert features['cat4_first_time'] == pd.to_datetime('2021-08-28 12:00')


def test_storms_that_never_reach_cat4():
    """Handle storms that stay below Cat 4"""
    track = pd.DataFrame({
        'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 06:00']),
        'max_wind': [60, 70],
    })
    features = calculate_intensification_features(track)
    assert features['cat4_first_time'] is None