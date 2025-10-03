"""Wind interpolation utilities for storm-tract feature generation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

EARTH_RADIUS_NM = 3440.065


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance between two lon/lat points in nautical miles."""

    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_NM * c


def find_nearest_point_on_linestring(centroid: Point, track_line: LineString) -> Point:
    """Return the closest point on ``track_line`` to ``centroid``."""

    distance_along = track_line.project(centroid)
    return track_line.interpolate(distance_along)


def interpolate_max_wind_at_point(point_on_track: Point, track_df: pd.DataFrame) -> float:
    """Linearly interpolate ``max_wind`` at ``point_on_track`` using nearest track rows."""

    required_cols = {"lat", "lon", "max_wind"}
    missing = required_cols - set(track_df.columns)
    if missing:
        raise ValueError(f"track_df missing columns: {missing}")

    distances_nm = track_df.apply(
        lambda row: _haversine_nm(point_on_track.y, point_on_track.x, row["lat"], row["lon"]),
        axis=1,
    )
    nearest_indices = np.argsort(distances_nm.values)[:2]
    nearest = track_df.iloc[nearest_indices].copy()
    nearest.loc[:, "dist_nm"] = distances_nm.iloc[nearest_indices].values

    nearest_sorted = nearest.sort_values("dist_nm").reset_index(drop=True)
    if len(nearest_sorted) == 0:
        raise ValueError("track_df must contain at least one observation")
    if len(nearest_sorted) == 1 or math.isclose(
        nearest_sorted.loc[0, "dist_nm"], nearest_sorted.loc[min(1, len(nearest_sorted)-1), "dist_nm"], rel_tol=1e-6
    ):
        return float(nearest_sorted.loc[0, "max_wind"])

    nearer = nearest_sorted.loc[0]
    farther = nearest_sorted.loc[1]
    ratio = nearer["dist_nm"] / (nearer["dist_nm"] + farther["dist_nm"])
    return float(nearer["max_wind"] + ratio * (farther["max_wind"] - nearer["max_wind"]))


def calculate_ray_envelope_intersection(track_point: Point, centroid: Point, envelope) -> Tuple[float, Point]:
    """Return distance (nm) and intersection point where ray exits ``envelope``."""

    direction = (centroid.x - track_point.x, centroid.y - track_point.y)
    if math.isclose(direction[0], 0.0, abs_tol=1e-12) and math.isclose(direction[1], 0.0, abs_tol=1e-12):
        return 0.0, track_point

    ray_length_deg = 5.0
    unit_len = math.hypot(*direction)
    direction_unit = (direction[0] / unit_len, direction[1] / unit_len)
    tee_point = Point(
        track_point.x + ray_length_deg * direction_unit[0],
        track_point.y + ray_length_deg * direction_unit[1],
    )
    ray = LineString([track_point, tee_point])
    intersection = ray.intersection(envelope.boundary if hasattr(envelope, "boundary") else envelope)

    if intersection.is_empty:
        raise ValueError("Ray does not intersect envelope boundary")

    if intersection.geom_type == "Point":
        edge_point = intersection
    else:
        edge_point = min(intersection.geoms, key=lambda geom: geom.distance(track_point))

    edge_dist_nm = _haversine_nm(track_point.y, track_point.x, edge_point.y, edge_point.x)
    return edge_dist_nm, edge_point


def calculate_max_wind_experienced(
    centroid: Point,
    track_line: LineString,
    track_df: pd.DataFrame,
    envelope,
) -> Dict[str, float]:
    """Estimate max wind at ``centroid`` using linear decay from track centre."""

    nearest_point = find_nearest_point_on_linestring(centroid, track_line)
    center_wind = interpolate_max_wind_at_point(nearest_point, track_df)

    centroid_dist_nm = _haversine_nm(nearest_point.y, nearest_point.x, centroid.y, centroid.x)
    edge_dist_nm, _ = calculate_ray_envelope_intersection(nearest_point, centroid, envelope)

    if math.isclose(edge_dist_nm, 0.0):
        decay_fraction = 1.0
    else:
        constrained = min(max(centroid_dist_nm / edge_dist_nm, 0.0), 1.0)
        decay_fraction = constrained

    wind_at_centroid = center_wind - decay_fraction * (center_wind - 64.0)

    return {
        "max_wind_experienced_kt": float(wind_at_centroid),
        "center_wind_at_approach_kt": float(center_wind),
        "distance_to_envelope_edge_nm": float(max(edge_dist_nm - centroid_dist_nm, 0.0)),
        "nearest_track_point_lat": float(nearest_point.y),
        "nearest_track_point_lon": float(nearest_point.x),
    }
