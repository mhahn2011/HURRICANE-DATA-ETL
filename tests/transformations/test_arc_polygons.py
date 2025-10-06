"""Unit tests for arc-based wind polygon generation."""

import sys
from pathlib import Path

from shapely.geometry import Polygon

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.extend([
    str(REPO_ROOT / "hurdat2" / "src"),
    str(REPO_ROOT / "hurdat2_census" / "src"),
])

from duration_calculator import create_instantaneous_wind_polygon
from envelope_algorithm import calculate_destination_point


def _build_chord_polygon(lat: float, lon: float, radii):
    """Construct the legacy 4-point chord polygon for comparison."""
    bearings = {"ne": 45, "se": 135, "sw": 225, "nw": 315}
    coords = []
    for quadrant, bearing in bearings.items():
        radius = radii.get(quadrant)
        if radius is None:
            continue
        dest_lon, dest_lat = calculate_destination_point(lat, lon, bearing, radius)
        coords.append((dest_lon, dest_lat))
    if len(coords) < 3:
        return None
    return Polygon(coords)


def test_arc_polygon_has_dense_vertex_count():
    lat, lon = 29.0, -90.0
    radii_nm = {quad: 60.0 for quad in ("ne", "se", "sw", "nw")}
    arc_poly = create_instantaneous_wind_polygon(
        lat,
        lon,
        radii_nm["ne"],
        radii_nm["se"],
        radii_nm["sw"],
        radii_nm["nw"],
    )

    assert arc_poly is not None
    vertex_count = len(arc_poly.exterior.coords)
    # 120 samples + closing coordinate → expect > 100 vertices
    assert vertex_count > 100, f"Expected >100 vertices, got {vertex_count}"


def test_arc_polygon_area_exceeds_chord_polygon():
    lat, lon = 29.0, -90.0
    radii_nm = {"ne": 80.0, "se": 60.0, "sw": 40.0, "nw": 70.0}

    arc_poly = create_instantaneous_wind_polygon(
        lat,
        lon,
        radii_nm["ne"],
        radii_nm["se"],
        radii_nm["sw"],
        radii_nm["nw"],
    )
    chord_poly = _build_chord_polygon(lat, lon, radii_nm)

    assert arc_poly is not None and chord_poly is not None
    assert arc_poly.area > chord_poly.area * 1.05, (
        "Arc-based polygon should have at least 5% greater area than chord polygon"
    )


def test_single_quadrant_fallback_produces_area():
    lat, lon = 29.0, -90.0
    arc_poly = create_instantaneous_wind_polygon(lat, lon, 50.0, None, None, None)

    assert arc_poly is not None
    assert arc_poly.area > 0.0
