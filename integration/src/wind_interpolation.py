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


def _estimate_rmw_from_wind(center_wind: float | None) -> float:
    """Return a plausible radius of maximum wind (nm) when observations are missing."""

    if center_wind is None or math.isnan(center_wind):
        return 30.0
    if center_wind >= 96:  # Category 3+
        return 20.0
    if center_wind >= 64:  # Category 1-2
        return 30.0
    return 40.0


def interpolate_radius_max_wind_at_point(
    point_on_track: Point,
    track_df: pd.DataFrame,
    center_wind: float | None,
) -> float:
    """Interpolate ``radius_max_wind`` (nm) at ``point_on_track`` with sensible fallbacks."""

    if "radius_max_wind" not in track_df.columns:
        return _estimate_rmw_from_wind(center_wind)

    candidates = track_df.dropna(subset=["radius_max_wind"])
    if candidates.empty:
        return _estimate_rmw_from_wind(center_wind)

    distances_nm = candidates.apply(
        lambda row: _haversine_nm(point_on_track.y, point_on_track.x, row["lat"], row["lon"]),
        axis=1,
    )

    nearest_indices = np.argsort(distances_nm.values)[:2]
    nearest = candidates.iloc[nearest_indices].copy()
    nearest.loc[:, "dist_nm"] = distances_nm.iloc[nearest_indices].values

    nearest_sorted = nearest.sort_values("dist_nm").reset_index(drop=True)
    if len(nearest_sorted) == 0:
        return _estimate_rmw_from_wind(center_wind)
    if len(nearest_sorted) == 1 or math.isclose(
        nearest_sorted.loc[0, "dist_nm"],
        nearest_sorted.loc[min(1, len(nearest_sorted) - 1), "dist_nm"],
        rel_tol=1e-6,
    ):
        value = nearest_sorted.loc[0, "radius_max_wind"]
        if pd.isna(value):
            return _estimate_rmw_from_wind(center_wind)
        return float(value)

    nearer = nearest_sorted.loc[0]
    farther = nearest_sorted.loc[1]
    nearer_val = nearer["radius_max_wind"]
    farther_val = farther["radius_max_wind"]

    if pd.isna(nearer_val) and pd.isna(farther_val):
        return _estimate_rmw_from_wind(center_wind)
    if pd.isna(nearer_val):
        return float(farther_val)
    if pd.isna(farther_val):
        return float(nearer_val)

    ratio = nearer["dist_nm"] / (nearer["dist_nm"] + farther["dist_nm"])
    interpolated = nearer_val + ratio * (farther_val - nearer_val)
    if pd.isna(interpolated):
        return _estimate_rmw_from_wind(center_wind)
    return float(interpolated)


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


def _check_inside_wind_radii_quadrilateral(
    centroid: Point,
    track_point: Point,
    wind_radii: Dict[str, float],
    threshold_kt: int,
) -> bool:
    """Check if centroid is inside wind radii quadrilateral for given threshold."""

    # Get quadrant-specific radii for this threshold
    radii_keys = {
        "ne": f"wind_radii_{threshold_kt}_ne",
        "se": f"wind_radii_{threshold_kt}_se",
        "sw": f"wind_radii_{threshold_kt}_sw",
        "nw": f"wind_radii_{threshold_kt}_nw",
    }

    # Extract radii values, skip if any are missing
    radii_values = {}
    for quad, key in radii_keys.items():
        if key not in wind_radii or pd.isna(wind_radii[key]):
            return False
        radii_values[quad] = wind_radii[key]

    # Determine which quadrant the centroid is in relative to track point
    lat_diff = centroid.y - track_point.y
    lon_diff = centroid.x - track_point.x

    if lat_diff >= 0 and lon_diff >= 0:
        quadrant = "ne"
    elif lat_diff < 0 <= lon_diff:
        quadrant = "se"
    elif lat_diff < 0 and lon_diff < 0:
        quadrant = "sw"
    else:
        quadrant = "nw"

    # Check if distance is within the quadrant's radius
    dist_nm = _haversine_nm(track_point.y, track_point.x, centroid.y, centroid.x)
    return dist_nm <= radii_values[quadrant]


def calculate_max_wind_experienced(
    centroid: Point,
    track_line: LineString,
    track_df: pd.DataFrame,
    envelope,
    wind_radii: Dict[str, float] = None,
) -> Dict[str, float]:
    """Estimate max wind at ``centroid`` using RMW plateau + decay within wind radii boundaries.

    Hierarchical logic:
    1. Determine which wind radii quadrilateral the centroid falls within (64kt, 50kt, 34kt, or none)
    2. If inside RMW -> use plateau model (max wind)
    3. If between RMW and quadrilateral boundary -> decay from max_wind to quadrilateral threshold
    4. If outside all quadrilaterals but inside envelope -> decay from max_wind to 64kt at envelope edge

    This honors both:
    - Wind radii quadrilaterals as outer boundaries
    - RMW for maximum wind intensity in the core
    """

    nearest_point = find_nearest_point_on_linestring(centroid, track_line)
    center_wind = interpolate_max_wind_at_point(nearest_point, track_df)
    rmw_at_approach = interpolate_radius_max_wind_at_point(nearest_point, track_df, center_wind)
    rmw_at_approach = max(rmw_at_approach, 0.0)

    centroid_dist_nm = _haversine_nm(nearest_point.y, nearest_point.x, centroid.y, centroid.x)
    edge_dist_nm, _ = calculate_ray_envelope_intersection(nearest_point, centroid, envelope)

    # Determine which wind radii quadrilateral contains the centroid
    inside_64kt = False
    inside_50kt = False
    inside_34kt = False

    if wind_radii is not None:
        inside_64kt = _check_inside_wind_radii_quadrilateral(centroid, nearest_point, wind_radii, 64)
        if not inside_64kt:
            inside_50kt = _check_inside_wind_radii_quadrilateral(centroid, nearest_point, wind_radii, 50)
        if not inside_64kt and not inside_50kt:
            inside_34kt = _check_inside_wind_radii_quadrilateral(centroid, nearest_point, wind_radii, 34)

    # Check if inside RMW (eyewall)
    inside_eyewall = centroid_dist_nm <= rmw_at_approach or math.isclose(
        centroid_dist_nm, rmw_at_approach, rel_tol=1e-6
    )

    if inside_eyewall:
        # Inside RMW: plateau at max wind
        wind_at_centroid = center_wind
        wind_source = "rmw_plateau"
    elif inside_64kt:
        # Between RMW and 64kt boundary: decay from max_wind to 64kt
        decay_distance = max(centroid_dist_nm - rmw_at_approach, 0.0)
        # Decay range is from RMW to 64kt boundary (use envelope edge as proxy)
        decay_range = max(edge_dist_nm - rmw_at_approach, 0.0)

        if math.isclose(decay_range, 0.0):
            wind_at_centroid = center_wind
        else:
            decay_fraction = min(max(decay_distance / decay_range, 0.0), 1.0)
            wind_at_centroid = max(center_wind - decay_fraction * (center_wind - 64.0), 64.0)
        wind_source = "rmw_decay_to_64kt"
    elif inside_50kt:
        # Between RMW and 50kt boundary: decay from max_wind to 50kt
        decay_distance = max(centroid_dist_nm - rmw_at_approach, 0.0)
        # For 50kt zone, estimate decay range (could be improved with actual 50kt radius)
        decay_range = max(edge_dist_nm - rmw_at_approach, 0.0)

        if math.isclose(decay_range, 0.0):
            wind_at_centroid = center_wind
        else:
            decay_fraction = min(max(decay_distance / decay_range, 0.0), 1.0)
            wind_at_centroid = max(center_wind - decay_fraction * (center_wind - 50.0), 50.0)
        wind_source = "rmw_decay_to_50kt"
    elif inside_34kt:
        # Between RMW and 34kt boundary: decay from max_wind to 34kt
        decay_distance = max(centroid_dist_nm - rmw_at_approach, 0.0)
        decay_range = max(edge_dist_nm - rmw_at_approach, 0.0)

        if math.isclose(decay_range, 0.0):
            wind_at_centroid = center_wind
        else:
            decay_fraction = min(max(decay_distance / decay_range, 0.0), 1.0)
            wind_at_centroid = max(center_wind - decay_fraction * (center_wind - 34.0), 34.0)
        wind_source = "rmw_decay_to_34kt"
    else:
        # Outside all wind radii but inside envelope: decay from max_wind to 64kt
        decay_distance = max(centroid_dist_nm - rmw_at_approach, 0.0)
        decay_range = max(edge_dist_nm - rmw_at_approach, 0.0)

        if math.isclose(decay_range, 0.0):
            wind_at_centroid = center_wind
        else:
            decay_fraction = min(max(decay_distance / decay_range, 0.0), 1.0)
            wind_at_centroid = center_wind - decay_fraction * (center_wind - 64.0)
        wind_source = "rmw_decay_to_envelope"

    return {
        "max_wind_experienced_kt": float(wind_at_centroid),
        "center_wind_at_approach_kt": float(center_wind),
        "distance_to_envelope_edge_nm": float(max(edge_dist_nm - centroid_dist_nm, 0.0)),
        "nearest_track_point_lat": float(nearest_point.y),
        "nearest_track_point_lon": float(nearest_point.x),
        "radius_max_wind_at_approach_nm": float(rmw_at_approach),
        "inside_eyewall": bool(inside_eyewall),
        "wind_source": wind_source,
    }
