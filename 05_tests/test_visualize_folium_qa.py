"""Tests for the Folium QA visualization utilities."""

import math
import sys
from pathlib import Path

import folium
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"))

from visualize_folium_qa import (
    create_wind_arc_polygon,
    generate_qa_map,
)


def _sample_track() -> pd.DataFrame:
    timestamps = pd.date_range("2021-08-28", periods=2, freq="6H")
    return pd.DataFrame(
        {
            "lat": [29.0, 29.5],
            "lon": [-90.0, -90.5],
            "date": timestamps,
            "storm_name": ["TEST", "TEST"],
            "storm_id": ["AL999999", "AL999999"],
            "max_wind": [100, 90],
            "min_pressure": [950, 955],
            "status": ["HU", "HU"],
            "wind_radii_34_ne": [60, 55],
            "wind_radii_34_se": [55, 50],
            "wind_radii_34_sw": [50, 45],
            "wind_radii_34_nw": [65, 60],
            "wind_radii_50_ne": [40, 38],
            "wind_radii_50_se": [35, 34],
            "wind_radii_50_sw": [30, 28],
            "wind_radii_50_nw": [42, 39],
            "wind_radii_64_ne": [25, 23],
            "wind_radii_64_se": [22, 20],
            "wind_radii_64_sw": [18, 17],
            "wind_radii_64_nw": [24, 22],
            "radius_max_wind": [20, 18],
        }
    )


def test_create_wind_arc_polygon_returns_vertices():
    radii = {"ne": 20.0, "se": 20.0, "sw": 20.0, "nw": 20.0}
    vertices = create_wind_arc_polygon(29.0, -90.0, radii)

    assert vertices is not None
    assert len(vertices) > 4  # Arc-based polygons have many more vertices than quadrilaterals
    assert all(isinstance(lat, (int, float)) and isinstance(lon, (int, float)) for lat, lon in vertices)


def test_create_wind_arc_polygon_handles_missing_values():
    radii = {"ne": 30.0, "se": None, "sw": 30.0, "nw": 30.0}
    assert create_wind_arc_polygon(29.0, -90.0, radii) is None


def test_generate_qa_map_writes_html(tmp_path):
    track_df = _sample_track()
    output_path = tmp_path / "qa_map.html"

    map_obj = generate_qa_map(track_df, "TEST", "AL999999", output_path)

    assert isinstance(map_obj, folium.Map)
    assert output_path.exists()
    assert output_path.stat().st_size > 0

    html = output_path.read_text()
    assert "track-point-label" in html
    assert "100 kt" in html
