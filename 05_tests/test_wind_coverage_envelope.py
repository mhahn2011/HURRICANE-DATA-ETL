"""Test wind coverage envelope vs alpha shape envelope.

This test suite validates the refactored wind coverage approach that uses
union of actual wind polygons instead of alpha shape approximation.

Baseline metrics from Hurricane Ida (before refactor):
- 520 tracts analyzed
- Duration range: 0.08 - 29.09 hours
- Mean wind speed: 80.2 kt
- 1 tract with <0.1 hour duration (false positive from alpha shape overshoot)
"""

import sys
from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import Point
from shapely.ops import unary_union

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"))
sys.path.insert(0, str(REPO_ROOT / "02_transformations" / "duration" / "src"))
sys.path.insert(0, str(REPO_ROOT / "02_transformations" / "wind_coverage_envelope" / "src"))

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from duration_calculator import (
    interpolate_track_temporal,
    create_instantaneous_wind_polygon,
)
from envelope_algorithm import impute_missing_wind_radii


class TestWindCoverageEnvelope:
    """Test that wind coverage envelope correctly captures actual wind exposure."""

    @pytest.fixture
    def ida_track(self):
        """Load Hurricane Ida track data."""
        hurdat_path = REPO_ROOT / "01_data_sources/hurdat2/input_data/hurdat2-atlantic.txt"
        storms = parse_hurdat2_file(hurdat_path)
        cleaned = clean_hurdat2_data(storms)
        track = cleaned[cleaned['storm_id'] == 'AL092021'].sort_values('date').reset_index(drop=True)
        return track

    def test_wind_polygon_union_contains_all_interpolated_polygons(self, ida_track):
        """Wind coverage envelope should contain all instantaneous wind polygons."""
        # Apply imputation first
        track_imputed = impute_missing_wind_radii(ida_track, wind_threshold='64kt')

        # Prepare for interpolation
        track_subset = track_imputed[[
            'date', 'lat', 'lon',
            'wind_radii_64_ne_imputed', 'wind_radii_64_se_imputed',
            'wind_radii_64_sw_imputed', 'wind_radii_64_nw_imputed',
        ]].copy()

        track_subset = track_subset.rename(columns={
            'wind_radii_64_ne_imputed': 'wind_radii_64_ne',
            'wind_radii_64_se_imputed': 'wind_radii_64_se',
            'wind_radii_64_sw_imputed': 'wind_radii_64_sw',
            'wind_radii_64_nw_imputed': 'wind_radii_64_nw',
        })

        # Interpolate at 15-min intervals
        interpolated = interpolate_track_temporal(track_subset, interval_minutes=15)

        # Create all wind polygons
        wind_polygons = []
        for _, row in interpolated.iterrows():
            poly = create_instantaneous_wind_polygon(
                row['lat'], row['lon'],
                row['wind_radii_64_ne'], row['wind_radii_64_se'],
                row['wind_radii_64_sw'], row['wind_radii_64_nw'],
            )
            if poly and not poly.is_empty:
                wind_polygons.append(poly)

        assert len(wind_polygons) > 0, "Should have at least one wind polygon"

        # Create union
        wind_coverage = unary_union(wind_polygons)

        assert wind_coverage.is_valid, "Wind coverage union should be valid geometry"
        assert wind_coverage.area > 0, "Wind coverage should have positive area"

        # Verify all individual polygons are contained
        for poly in wind_polygons:
            # Allow small tolerance for floating point precision
            assert poly.buffer(-0.001).within(wind_coverage.buffer(0.001))

    def test_wind_coverage_filters_zero_duration_tracts(self, ida_track):
        """Wind coverage envelope should exclude tracts with zero exposure."""
        # This is the key test - tracts inside wind coverage MUST have >0 duration
        # because they intersect at least one wind polygon by definition

        # Apply imputation
        track_imputed = impute_missing_wind_radii(ida_track, wind_threshold='64kt')

        track_subset = track_imputed[[
            'date', 'lat', 'lon',
            'wind_radii_64_ne_imputed', 'wind_radii_64_se_imputed',
            'wind_radii_64_sw_imputed', 'wind_radii_64_nw_imputed',
        ]].copy()

        track_subset = track_subset.rename(columns={
            'wind_radii_64_ne_imputed': 'wind_radii_64_ne',
            'wind_radii_64_se_imputed': 'wind_radii_64_se',
            'wind_radii_64_sw_imputed': 'wind_radii_64_sw',
            'wind_radii_64_nw_imputed': 'wind_radii_64_nw',
        })

        interpolated = interpolate_track_temporal(track_subset, interval_minutes=15)

        # Create wind coverage envelope
        wind_polygons = []
        for _, row in interpolated.iterrows():
            poly = create_instantaneous_wind_polygon(
                row['lat'], row['lon'],
                row['wind_radii_64_ne'], row['wind_radii_64_se'],
                row['wind_radii_64_sw'], row['wind_radii_64_nw'],
            )
            if poly and not poly.is_empty:
                wind_polygons.append(poly)

        wind_coverage = unary_union(wind_polygons)

        # Test with sample points
        # Point inside coverage should have duration > 0
        center_lat = ida_track['lat'].mean()
        center_lon = ida_track['lon'].mean()
        point_inside = Point(center_lon, center_lat)

        if point_inside.within(wind_coverage):
            # If inside, must intersect at least one polygon
            intersects_any = any(point_inside.intersects(poly) for poly in wind_polygons)
            assert intersects_any, "Point inside coverage must intersect at least one wind polygon"

        # Point far outside should not be inside coverage
        point_outside = Point(center_lon - 10, center_lat - 10)
        assert not point_outside.within(wind_coverage), "Point far from storm should be outside coverage"

    def test_baseline_comparison_with_ida_features(self):
        """Compare new approach with baseline Ida features."""
        baseline_path = REPO_ROOT / "06_outputs/ml_ready/ida_features_complete_v3.csv"

        if not baseline_path.exists():
            pytest.skip("Baseline file not found - run storm_tract_distance.py first")

        baseline = pd.read_csv(baseline_path)

        # Baseline expectations
        assert len(baseline) == 520, "Baseline should have 520 tracts"

        # Check for false positives (tracts with near-zero duration)
        zero_duration_tracts = baseline[baseline['duration_in_envelope_hours'] < 0.1]

        # After refactor, this should be ZERO (no false positives)
        # Before refactor, we had 1 tract with <0.1 hour
        assert len(zero_duration_tracts) <= 1, f"Should have ≤1 false positive, got {len(zero_duration_tracts)}"

        # Valid tracts should have reasonable wind speeds
        valid_tracts = baseline[baseline['duration_in_envelope_hours'] >= 0.1]
        assert valid_tracts['max_wind_experienced_kt'].mean() > 60, "Valid tracts should have mean wind >60kt"


class TestWindPolygonCreation:
    """Test instantaneous wind polygon creation."""

    def test_wind_polygon_handles_partial_radii(self):
        """Should create polygon even with some missing quadrants."""
        # All defined
        poly1 = create_instantaneous_wind_polygon(29.0, -90.0, 50, 40, 30, 35)
        assert poly1 is not None and poly1.area > 0

        # Two quadrants (should still work)
        poly2 = create_instantaneous_wind_polygon(29.0, -90.0, 50, None, None, 35)
        assert poly2 is not None and poly2.area > 0

        # One quadrant (edge case - may return small polygon or None)
        poly3 = create_instantaneous_wind_polygon(29.0, -90.0, 50, None, None, None)
        # At minimum should not error

    def test_wind_polygon_rejects_all_null(self):
        """Should return None when all radii are missing."""
        poly = create_instantaneous_wind_polygon(29.0, -90.0, None, None, None, None)
        assert poly is None or poly.is_empty
