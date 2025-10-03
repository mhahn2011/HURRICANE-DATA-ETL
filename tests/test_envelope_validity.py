"""
Tests for envelope algorithm validity

Critical requirements:
1. ALL envelopes must be valid (no self-intersections)
2. Track must be FULLY contained within envelope
3. All wind extent points must be inside envelope
"""
import pytest
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.ops import unary_union
import pandas as pd
import numpy as np
import sys
from pathlib import Path
import json

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'hurdat2' / 'src'))


def load_test_envelope_data():
    """Load Hurricane Ida envelope data from notebook outputs"""
    nb_path = Path(__file__).parent.parent / 'hurdat2' / 'notebooks' / 'hurdat2_to_features.ipynb'

    if not nb_path.exists():
        return None, None, None

    # Load notebook to extract envelope from Cell 6 outputs
    # For now, return None - we'll need to extract the algorithm to a module
    return None, None, None


class TestEnvelopeValidity:
    """Test envelope geometry validity"""

    def test_envelope_must_be_valid(self):
        """CRITICAL: Envelope polygon must ALWAYS be valid (no self-intersection)"""
        envelope, track_line, track_df = load_test_envelope_data()

        if envelope is None:
            pytest.skip("Algorithm not yet extracted to testable module")

        # Handle both Polygon and MultiPolygon
        if isinstance(envelope, MultiPolygon):
            for poly in envelope.geoms:
                assert poly.is_valid, f"Polygon in MultiPolygon is invalid: {poly.is_valid_reason}"
        else:
            assert envelope.is_valid, f"Envelope is invalid: {envelope.is_valid_reason}"

    def test_envelope_area_positive(self):
        """Envelope must have positive area"""
        envelope, _, _ = load_test_envelope_data()

        if envelope is None:
            pytest.skip("Algorithm not yet extracted")

        assert envelope.area > 0, f"Envelope area must be positive, got {envelope.area}"
        assert envelope.area < 500, f"Envelope area seems unreasonably large: {envelope.area} sq degrees"


class TestTrackContainment:
    """CRITICAL: Track must be fully inside envelope"""

    def test_all_track_points_inside_envelope(self):
        """Every track point must be inside the envelope"""
        envelope, track_line, track_df = load_test_envelope_data()

        if envelope is None:
            pytest.skip("Algorithm not yet extracted")

        # Check each track point
        points_outside = []
        for idx, row in track_df.iterrows():
            point = Point(row['lon'], row['lat'])
            if not envelope.contains(point):
                points_outside.append({
                    'index': idx,
                    'lat': row['lat'],
                    'lon': row['lon'],
                    'distance_to_envelope': point.distance(envelope)
                })

        assert len(points_outside) == 0, \
            f"❌ {len(points_outside)} track points are OUTSIDE envelope!\n" + \
            f"First few: {points_outside[:5]}"

    def test_track_line_inside_envelope(self):
        """The entire track LineString must be within the envelope"""
        envelope, track_line, _ = load_test_envelope_data()

        if envelope is None:
            pytest.skip("Algorithm not yet extracted")

        # Check if track line is contained by envelope
        # Allow small numerical tolerance
        assert envelope.contains(track_line) or envelope.buffer(0.01).contains(track_line), \
            "Track line extends outside envelope boundary"


class TestWindExtentContainment:
    """Wind extent points should be near or inside envelope boundary"""

    def test_wind_extent_points_near_envelope(self):
        """All wind extent points should be within or near the envelope boundary"""
        envelope, _, track_df = load_test_envelope_data()

        if envelope is None:
            pytest.skip("Algorithm not yet extracted")

        # This test would check that the 4-directional wind points
        # are all contained or define the envelope boundary
        pytest.skip("Need to extract wind extent point calculation")


class TestEnvelopeProperties:
    """Test envelope has reasonable properties"""

    def test_envelope_not_too_narrow(self):
        """Envelope should have reasonable width (not just a thin line)"""
        envelope, track_line, _ = load_test_envelope_data()

        if envelope is None:
            pytest.skip("Algorithm not yet extracted")

        # Calculate minimum width perpendicular to track
        # Envelope area should be significantly larger than track length
        track_length = track_line.length
        envelope_area = envelope.area

        # Very rough heuristic: area should be > length (implies width > 1 degree)
        assert envelope_area > track_length * 0.5, \
            f"Envelope seems too narrow: area={envelope_area:.2f}, track_length={track_length:.2f}"

    def test_envelope_bounds_reasonable(self):
        """Envelope bounds should be reasonable for Atlantic hurricanes"""
        envelope, _, _ = load_test_envelope_data()

        if envelope is None:
            pytest.skip("Algorithm not yet extracted")

        minx, miny, maxx, maxy = envelope.bounds

        # Atlantic basin checks
        assert -180 < minx < 0, f"Western bound unreasonable: {minx}"
        assert 0 < miny < 90, f"Southern bound unreasonable: {miny}"
        assert -180 < maxx < 0, f"Eastern bound unreasonable: {maxx}"
        assert 0 < maxy < 90, f"Northern bound unreasonable: {maxy}"


@pytest.mark.parametrize("storm_name,year", [
    ("IDA", 2021),
    # Add more test cases as we validate algorithm
])
def test_known_storms_produce_valid_envelopes(storm_name, year):
    """Test that known storms produce valid envelopes with track containment"""
    # This would load specific storm data and run full validation
    pytest.skip("Need to implement storm-specific data loading")
