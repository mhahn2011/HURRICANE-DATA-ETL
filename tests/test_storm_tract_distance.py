import datetime as dt

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from shapely.geometry import Point, LineString

from integration.src.storm_tract_distance import (
    compute_min_distance_features,
    haversine_nm,
)
from integration.src.wind_interpolation import calculate_max_wind_experienced


def make_track(**kwargs) -> pd.DataFrame:
    defaults = dict(
        storm_id="AL999999",
        storm_name="TEST",
        date=pd.to_datetime([dt.datetime(2021, 8, 28)]),
        lat=[29.5],
        lon=[-90.0],
        wind_radii_64_ne=[50.0],
        wind_radii_64_se=[50.0],
        wind_radii_64_sw=[50.0],
        wind_radii_64_nw=[50.0],
    )
    defaults.update(kwargs)
    return pd.DataFrame(defaults)


def test_haversine_nm_basic_symmetry():
    a = haversine_nm(np.array([29.5]), np.array([-90.0]), np.array([29.5]), np.array([-90.5]))
    b = haversine_nm(np.array([29.5]), np.array([-90.5]), np.array([29.5]), np.array([-90.0]))
    assert np.allclose(a, b)


def test_compute_min_distance_features_structure():
    track = make_track()
    centroids = gpd.GeoDataFrame(
        {
            "GEOID": ["123456789012"],
            "STATEFP": ["22"],
            "COUNTYFP": ["071"],
            "TRACTCE": ["543210"],
            "geometry": [Point(-89.5, 30.0)],
        },
        crs="EPSG:4326",
    )

    features = compute_min_distance_features(centroids, track)

    assert list(features.columns) == [
        "tract_geoid",
        "storm_id",
        "storm_name",
        "storm_time",
        "distance_nm",
        "distance_km",
        "nearest_quadrant",
        "radius_64_nm",
        "within_64kt",
        "storm_tract_id",
    ]

    assert features.loc[0, "nearest_quadrant"] == "NE"
    assert features.loc[0, "storm_tract_id"] == "AL999999_123456789012"
    assert features.loc[0, "radius_64_nm"] == 50.0
    assert bool(features.loc[0, "within_64kt"])


def test_compute_min_distance_features_handles_missing_radius():
    track = make_track(
        wind_radii_64_ne=[np.nan],
        wind_radii_64_se=[np.nan],
        wind_radii_64_sw=[np.nan],
        wind_radii_64_nw=[np.nan],
    )
    centroids = gpd.GeoDataFrame(
        {
            "GEOID": ["999999999999"],
            "STATEFP": ["12"],
            "COUNTYFP": ["086"],
            "TRACTCE": ["000100"],
            "geometry": [Point(-89.8, 29.0)],
        },
        crs="EPSG:4326",
    )

    features = compute_min_distance_features(centroids, track)

    assert np.isnan(features.loc[0, "radius_64_nm"])
    assert features.loc[0, "within_64kt"] is None


def test_calculate_max_wind_experienced_simple_case():
    track_df = pd.DataFrame(
        {
            "lat": [0.0, 0.0],
            "lon": [0.0, 1.0],
            "max_wind": [100.0, 80.0],
        }
    )
    track_line = LineString([(0.0, 0.0), (1.0, 0.0)])
    envelope = track_line.buffer(0.5)
    centroid = Point(0.5, 0.2)

    results = calculate_max_wind_experienced(centroid, track_line, track_df, envelope)

    assert 64 <= results["max_wind_experienced_kt"] <= results["center_wind_at_approach_kt"] <= 100
