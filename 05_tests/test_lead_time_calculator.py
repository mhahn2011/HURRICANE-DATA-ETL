"""Unit tests for lead time calculator."""

import pandas as pd
import pytest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "02_transformations" / "lead_time" / "src"))

from lead_time_calculator import (
    find_category_threshold_time,
    calculate_lead_times,
    validate_lead_times,
    CATEGORY_THRESHOLDS,
)


class TestFindCategoryThresholdTime:
    """Test finding the first time a storm reaches a category threshold."""

    def test_threshold_reached_at_first_observation(self):
        """Storm already at threshold in first observation."""
        track = pd.DataFrame({
            'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 06:00']),
            'max_wind': [115, 120]
        })

        result = find_category_threshold_time(track, threshold_kt=113)

        assert result == pd.Timestamp('2021-08-28 00:00')

    def test_threshold_reached_midway(self):
        """Storm reaches threshold in middle of track."""
        track = pd.DataFrame({
            'date': pd.to_datetime([
                '2021-08-27 00:00',
                '2021-08-27 12:00',
                '2021-08-28 00:00',
                '2021-08-28 12:00'
            ]),
            'max_wind': [80, 100, 115, 120]
        })

        result = find_category_threshold_time(track, threshold_kt=113)

        assert result == pd.Timestamp('2021-08-28 00:00')

    def test_threshold_never_reached(self):
        """Storm never reaches threshold."""
        track = pd.DataFrame({
            'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 06:00']),
            'max_wind': [60, 75]
        })

        result = find_category_threshold_time(track, threshold_kt=113)

        assert result is None

    def test_threshold_exactly_at_boundary(self):
        """Storm reaches exactly the threshold value."""
        track = pd.DataFrame({
            'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 06:00']),
            'max_wind': [80, 113]
        })

        result = find_category_threshold_time(track, threshold_kt=113)

        # Uses >= so exact match counts
        assert result == pd.Timestamp('2021-08-28 06:00')


class TestCalculateLeadTimes:
    """Test calculating lead times for all categories."""

    def test_positive_lead_time(self):
        """Storm reached threshold before closest approach (warning time)."""
        track = pd.DataFrame({
            'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 12:00']),
            'max_wind': [80, 115]
        })
        nearest_approach = pd.Timestamp('2021-08-29 00:00')

        lead_times = calculate_lead_times(track, nearest_approach)

        # Cat 4 reached at 12:00, approach at next day 00:00 = 12 hours lead time
        assert lead_times['lead_time_cat4_hours'] == 12.0
        assert lead_times['lead_time_cat5_hours'] is None  # Never reached

    def test_negative_lead_time(self):
        """Storm intensified after passing (negative warning time)."""
        track = pd.DataFrame({
            'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-29 12:00']),
            'max_wind': [80, 115]
        })
        nearest_approach = pd.Timestamp('2021-08-29 00:00')

        lead_times = calculate_lead_times(track, nearest_approach)

        # Cat 4 reached 12 hours AFTER closest approach
        assert lead_times['lead_time_cat4_hours'] == -12.0

    def test_all_categories_none(self):
        """Weak storm that never becomes a hurricane."""
        track = pd.DataFrame({
            'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 12:00']),
            'max_wind': [35, 50]  # Tropical storm only
        })
        nearest_approach = pd.Timestamp('2021-08-28 18:00')

        lead_times = calculate_lead_times(track, nearest_approach)

        # All categories should be None
        for cat in ['cat1', 'cat2', 'cat3', 'cat4', 'cat5']:
            assert lead_times[f'lead_time_{cat}_hours'] is None

    def test_multiple_categories_reached(self):
        """Storm reaches multiple categories."""
        track = pd.DataFrame({
            'date': pd.to_datetime([
                '2021-08-27 00:00',  # 60kt - TS
                '2021-08-27 12:00',  # 70kt - Cat 1
                '2021-08-28 00:00',  # 85kt - Cat 2
                '2021-08-28 12:00',  # 100kt - Cat 3
            ]),
            'max_wind': [60, 70, 85, 100]
        })
        nearest_approach = pd.Timestamp('2021-08-29 00:00')

        lead_times = calculate_lead_times(track, nearest_approach)

        # Cat 1: 27th 12:00 -> 29th 00:00 = 36 hours
        assert lead_times['lead_time_cat1_hours'] == 36.0
        # Cat 2: 28th 00:00 -> 29th 00:00 = 24 hours
        assert lead_times['lead_time_cat2_hours'] == 24.0
        # Cat 3: 28th 12:00 -> 29th 00:00 = 12 hours
        assert lead_times['lead_time_cat3_hours'] == 12.0
        # Cat 4 & 5: Never reached
        assert lead_times['lead_time_cat4_hours'] is None
        assert lead_times['lead_time_cat5_hours'] is None

    def test_hurricane_ida_realistic_scenario(self):
        """Realistic scenario based on Hurricane Ida."""
        # Simplified Ida track
        track = pd.DataFrame({
            'date': pd.to_datetime([
                '2021-08-27 12:00',  # 40kt - TD
                '2021-08-28 00:00',  # 75kt - Cat 1
                '2021-08-28 12:00',  # 90kt - Cat 2
                '2021-08-29 00:00',  # 105kt - Cat 3
                '2021-08-29 12:00',  # 130kt - Cat 4
            ]),
            'max_wind': [40, 75, 90, 105, 130]
        })
        # Landfall near New Orleans ~2021-08-29 18:00
        nearest_approach = pd.Timestamp('2021-08-29 18:00')

        lead_times = calculate_lead_times(track, nearest_approach)

        # Cat 1: 28th 00:00 -> 29th 18:00 = 42 hours
        assert lead_times['lead_time_cat1_hours'] == 42.0
        # Cat 2: 28th 12:00 -> 29th 18:00 = 30 hours
        assert lead_times['lead_time_cat2_hours'] == 30.0
        # Cat 3: 29th 00:00 -> 29th 18:00 = 18 hours
        assert lead_times['lead_time_cat3_hours'] == 18.0
        # Cat 4: 29th 12:00 -> 29th 18:00 = 6 hours
        assert lead_times['lead_time_cat4_hours'] == 6.0
        # Cat 5: Never reached
        assert lead_times['lead_time_cat5_hours'] is None


class TestValidateLeadTimes:
    """Test lead time validation logic."""

    def test_valid_decreasing_lead_times(self):
        """Valid case: lead times decrease as storm intensifies."""
        lead_times = {
            'lead_time_cat1_hours': 48.0,
            'lead_time_cat2_hours': 36.0,
            'lead_time_cat3_hours': 24.0,
            'lead_time_cat4_hours': 12.0,
            'lead_time_cat5_hours': None,
        }

        assert validate_lead_times(lead_times) is True

    def test_valid_all_none(self):
        """Valid case: weak storm, all None."""
        lead_times = {
            'lead_time_cat1_hours': None,
            'lead_time_cat2_hours': None,
            'lead_time_cat3_hours': None,
            'lead_time_cat4_hours': None,
            'lead_time_cat5_hours': None,
        }

        assert validate_lead_times(lead_times) is True

    def test_valid_some_categories(self):
        """Valid case: reached Cat 2, then None."""
        lead_times = {
            'lead_time_cat1_hours': 36.0,
            'lead_time_cat2_hours': 24.0,
            'lead_time_cat3_hours': None,
            'lead_time_cat4_hours': None,
            'lead_time_cat5_hours': None,
        }

        assert validate_lead_times(lead_times) is True

    def test_invalid_none_then_value(self):
        """Invalid: None followed by a value (impossible)."""
        lead_times = {
            'lead_time_cat1_hours': 48.0,
            'lead_time_cat2_hours': None,
            'lead_time_cat3_hours': 24.0,  # Invalid - storm can't skip Cat 2
            'lead_time_cat4_hours': None,
            'lead_time_cat5_hours': None,
        }

        assert validate_lead_times(lead_times) is False

    def test_invalid_increasing_lead_times(self):
        """Invalid: lead times increasing (storm weakening then re-intensifying)."""
        lead_times = {
            'lead_time_cat1_hours': 12.0,
            'lead_time_cat2_hours': 24.0,  # Increased - suspicious
            'lead_time_cat3_hours': None,
            'lead_time_cat4_hours': None,
            'lead_time_cat5_hours': None,
        }

        # Should fail due to significant increase
        assert validate_lead_times(lead_times) is False

    def test_valid_small_increase_within_tolerance(self):
        """Valid: small increase within 6-hour tolerance for observation timing."""
        lead_times = {
            'lead_time_cat1_hours': 24.0,
            'lead_time_cat2_hours': 26.0,  # Small increase (observation timing)
            'lead_time_cat3_hours': None,
            'lead_time_cat4_hours': None,
            'lead_time_cat5_hours': None,
        }

        # Within tolerance
        assert validate_lead_times(lead_times) is True


class TestCategoryThresholdsConstant:
    """Test that category thresholds are correct."""

    def test_thresholds_match_saffir_simpson_scale(self):
        """Verify thresholds match official Saffir-Simpson scale."""
        assert CATEGORY_THRESHOLDS['cat1'] == 64   # 64-82 kt
        assert CATEGORY_THRESHOLDS['cat2'] == 83   # 83-95 kt
        assert CATEGORY_THRESHOLDS['cat3'] == 96   # 96-112 kt (Major)
        assert CATEGORY_THRESHOLDS['cat4'] == 113  # 113-136 kt
        assert CATEGORY_THRESHOLDS['cat5'] == 137  # 137+ kt

    def test_thresholds_in_ascending_order(self):
        """Thresholds should be in ascending order."""
        thresholds = list(CATEGORY_THRESHOLDS.values())
        assert thresholds == sorted(thresholds)
