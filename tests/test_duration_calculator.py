import pandas as pd
from shapely.geometry import Point

from integration.src.duration_calculator import (
    calculate_duration_features,
    calculate_duration_for_tract,
    check_centroid_exposure_over_time,
    create_instantaneous_wind_polygon,
    interpolate_track_temporal,
)


def build_simple_track():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2021-08-28 00:00", "2021-08-28 06:00"]),
            "lat": [25.0, 26.0],
            "lon": [-90.0, -91.0],
            "wind_radii_64_ne": [50.0, 60.0],
            "wind_radii_64_se": [50.0, 60.0],
            "wind_radii_64_sw": [50.0, 60.0],
            "wind_radii_64_nw": [50.0, 60.0],
        }
    )


def test_interpolate_track_temporal_basic():
    track = build_simple_track()
    interpolated = interpolate_track_temporal(track, interval_minutes=15)

    assert len(interpolated) == 25
    assert interpolated.iloc[0]["lat"] == 25.0
    assert interpolated.iloc[-1]["lat"] == 26.0
    assert 25.0 < interpolated.iloc[12]["lat"] < 26.0


def test_create_instantaneous_wind_polygon():
    polygon = create_instantaneous_wind_polygon(29.0, -90.0, 50, 40, 30, 45)
    assert polygon is not None
    assert polygon.is_valid
    assert polygon.geom_type == "Polygon"


def test_duration_for_stationary_point_inside():
    track = build_simple_track()
    centroid = Point(-90.5, 25.5)
    interpolated = interpolate_track_temporal(track, interval_minutes=60)
    exposure = check_centroid_exposure_over_time(centroid, interpolated)
    duration = calculate_duration_features(exposure, interval_minutes=60)

    assert duration["duration_in_envelope_hours"] > 0
    assert duration["first_entry_time"] is not None
    assert duration["continuous_exposure"] is True
    assert duration["duration_source"] == "timeline"


def test_duration_for_point_outside():
    track = build_simple_track()
    centroid = Point(-95.0, 20.0)
    interpolated = interpolate_track_temporal(track, interval_minutes=60)
    exposure = check_centroid_exposure_over_time(centroid, interpolated)
    duration = calculate_duration_features(exposure, interval_minutes=60)

    assert duration["duration_in_envelope_hours"] == 0
    assert duration["first_entry_time"] is None
    assert duration["duration_source"] == "timeline"


def test_duration_for_tract_wrapper():
    track = build_simple_track()
    centroid = Point(-90.5, 25.5)
    features = calculate_duration_for_tract(centroid, track, wind_threshold="64kt", interval_minutes=60)

    assert features["duration_in_envelope_hours"] > 0
    assert features["interpolated_points_count"] > 0
    assert features["duration_source"] in {"timeline", "edge_interpolation"}
