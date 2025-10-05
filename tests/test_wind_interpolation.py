"""Unit tests for wind interpolation plateau + decay model."""

import math

import pandas as pd
from shapely.geometry import LineString, Point

from integration.src.wind_interpolation import calculate_max_wind_experienced


def _make_track_df(max_wind: float, radius_max_wind: float | None = None) -> pd.DataFrame:
    data = {
        "lat": [0.0, 0.1],
        "lon": [0.0, 0.1],
        "max_wind": [max_wind, max_wind],
    }
    if radius_max_wind is not None:
        data["radius_max_wind"] = [radius_max_wind, radius_max_wind]
    return pd.DataFrame(data)


def _make_track_line(track_df: pd.DataFrame) -> LineString:
    return LineString(list(zip(track_df["lon"], track_df["lat"])))


def _make_envelope():
    # Large enough buffer (degrees) for tests; precise distance handled by haversine.
    return Point(0.0, 0.0).buffer(2.0)


def test_plateau_model_inside_rmw_returns_center_wind():
    track_df = _make_track_df(max_wind=120.0, radius_max_wind=20.0)
    track_line = _make_track_line(track_df)
    envelope = _make_envelope()
    centroid = Point(0.0, 10.0 / 60.0)  # ~10 nm north

    result = calculate_max_wind_experienced(centroid, track_line, track_df, envelope)

    assert math.isclose(result["center_wind_at_approach_kt"], 120.0, rel_tol=1e-6)
    assert math.isclose(result["max_wind_experienced_kt"], 120.0, rel_tol=1e-6)
    assert result["inside_eyewall"] is True


def test_plateau_model_outside_rmw_decays_linearly():
    track_df = _make_track_df(max_wind=120.0, radius_max_wind=20.0)
    track_line = _make_track_line(track_df)
    envelope = _make_envelope()
    centroid = Point(0.0, 40.0 / 60.0)  # ~40 nm north

    result = calculate_max_wind_experienced(centroid, track_line, track_df, envelope)

    assert result["inside_eyewall"] is False
    assert result["max_wind_experienced_kt"] < result["center_wind_at_approach_kt"]
    assert result["max_wind_experienced_kt"] > 64.0


def test_plateau_model_at_rmw_boundary_matches_center_wind():
    track_df = _make_track_df(max_wind=100.0, radius_max_wind=25.0)
    track_line = _make_track_line(track_df)
    envelope = _make_envelope()
    centroid = Point(0.0, 25.0 / 60.0)  # ~25 nm north

    result = calculate_max_wind_experienced(centroid, track_line, track_df, envelope)

    assert math.isclose(result["max_wind_experienced_kt"], 100.0, rel_tol=1e-6)
    assert result["inside_eyewall"] is True


def test_missing_rmw_column_uses_fallback_defaults():
    track_df = _make_track_df(max_wind=110.0, radius_max_wind=None)
    track_df = track_df.drop(columns=["radius_max_wind"], errors="ignore")
    track_line = _make_track_line(track_df)
    envelope = _make_envelope()
    centroid = Point(0.0, 30.0 / 60.0)  # ~30 nm north

    result = calculate_max_wind_experienced(centroid, track_line, track_df, envelope)

    assert math.isclose(result["radius_max_wind_at_approach_nm"], 20.0, rel_tol=1e-6)
    assert result["inside_eyewall"] is False
