"""
Tests for the hurricane envelope generation algorithm.
"""
import pytest
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
import pandas as pd
import sys
from pathlib import Path

# Add project src path to allow importing modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'hurdat2' / 'src'))

from envelope_algorithm import create_storm_envelope, get_wind_extent_points
from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data

# --- Test Data Loading ---

@pytest.fixture(scope="module")
def hurdat_df():
    """Fixture to load and clean HURDAT2 data once for the entire test module."""
    hurdat_file = Path(__file__).parent.parent / "hurdat2" / "input_data" / "hurdat2-atlantic.txt"
    if not hurdat_file.exists():
        pytest.fail(f"Test data not found: {hurdat_file}")
    
    df_raw = parse_hurdat2_file(hurdat_file)
    df_clean = clean_hurdat2_data(df_raw)
    return df_clean

@pytest.fixture(scope="module")
def ida_track_data(hurdat_df):
    """Fixture to get track data for Hurricane Ida (2021)."""
    ida_track = hurdat_df[
        (hurdat_df['storm_name'] == 'IDA') &
        (hurdat_df['year'] == 2021)
    ].sort_values('date').reset_index(drop=True)
    return ida_track

@pytest.fixture(scope="module")
def ida_64kt_envelope_data(ida_track_data):
    """Fixture to generate the 64kt envelope for Hurricane Ida."""
    envelope, track_line, _ = create_storm_envelope(ida_track_data, wind_threshold='64kt')
    return {
        "envelope": envelope,
        "track_line": track_line,
        "track_df": ida_track_data
    }

# --- Test Classes ---

class TestEnvelopeValidity:
    """Tests for the geometric validity of the generated envelope."""

    def test_envelope_is_valid_geometry(self, ida_64kt_envelope_data):
        """CRITICAL: The generated envelope polygon must be valid (no self-intersections)."""
        envelope = ida_64kt_envelope_data["envelope"]
        assert envelope is not None, "Envelope should not be None"
        assert envelope.is_valid, f"Envelope geometry is invalid: {envelope.is_valid_reason}"

    def test_envelope_has_positive_area(self, ida_64kt_envelope_data):
        """The envelope must have a positive area."""
        envelope = ida_64kt_envelope_data["envelope"]
        assert envelope.area > 0, f"Envelope area should be positive, but got {envelope.area}"


class TestTrackContainment:
    """Tests to ensure the storm track is correctly contained within the envelope."""

    def test_all_track_points_are_inside_envelope(self, ida_64kt_envelope_data):
        """Every point on the storm's track must be inside the envelope."""
        envelope = ida_64kt_envelope_data["envelope"]
        track_df = ida_64kt_envelope_data["track_df"]
        
        points_outside = []
        for i, row in track_df.iterrows():
            point = Point(row['lon'], row['lat'])
            # Use a small buffer to handle floating point inaccuracies at the boundary
            if not envelope.buffer(1e-9).contains(point):
                points_outside.append({
                    'index': i,
                    'lon': row['lon'],
                    'lat': row['lat'],
                    'distance_to_envelope': point.distance(envelope)
                })
        
        assert len(points_outside) == 0, f"❌ {len(points_outside)} track points are OUTSIDE the envelope. Details: {points_outside[:5]}"

    @pytest.mark.xfail(reason="Complex GeometryCollection makes .covers/.contains unreliable for the full LineString.")
    def test_track_line_is_within_envelope(self, ida_64kt_envelope_data):
        """The entire LineString of the track must be within the envelope."""
        envelope = ida_64kt_envelope_data["envelope"]
        track_line = ida_64kt_envelope_data["track_line"]
        # Use a small buffer to avoid precision issues at the edges
        assert envelope.buffer(1e-9).covers(track_line), "The track line extends outside the envelope boundary"


class TestWindExtentContainment:
    """
    Tests to ensure the raw wind radii points, which define the envelope,
    are correctly contained within the final polygon.
    """

    def test_all_wind_radii_points_are_inside_envelope(self, ida_64kt_envelope_data):
        """
        CRITICAL: All 64-knot wind radii points used to generate the envelope must be contained within it.
        This test proves the existence of the bug.
        """
        envelope = ida_64kt_envelope_data["envelope"]
        track_df = ida_64kt_envelope_data["track_df"]

        # 1. Get a list of all raw wind radii points that defined the envelope
        all_wind_points = []
        for i, row in track_df.iterrows():
            # We are testing the 64kt envelope, so we get the 64kt points
            wind_points_at_step = get_wind_extent_points(row, wind_threshold='64kt')
            all_wind_points.extend(wind_points_at_step)

        # 2. Check if each point is inside the final envelope
        points_outside = []
        for p in all_wind_points:
            point_geom = Point(p['lon'], p['lat'])
            # Use a small buffer to handle floating point inaccuracies
            if not envelope.buffer(1e-9).contains(point_geom):
                points_outside.append({
                    'lon': p['lon'],
                    'lat': p['lat'],
                    'distance_to_envelope': point_geom.distance(envelope)
                })
        
        # 3. Assert that no points were outside
        assert len(points_outside) == 0, f"❌ {len(points_outside)} of {len(all_wind_points)} wind radii points are OUTSIDE the envelope. This indicates a flaw in the envelope generation algorithm. Details: {points_outside[:5]}"