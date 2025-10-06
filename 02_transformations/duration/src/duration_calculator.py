"""Duration exposure calculations for storm-track interactions."""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"))

from envelope_algorithm import calculate_destination_point, generate_quadrant_arc_points


def interpolate_track_temporal(track_df: pd.DataFrame, interval_minutes: int = 15) -> pd.DataFrame:
    """Interpolate storm track to finer temporal resolution."""

    if "date" not in track_df.columns:
        raise ValueError("track_df must include a 'date' column")

    track_sorted = track_df.sort_values("date").reset_index(drop=True)
    columns = [col for col in track_sorted.columns if col != "date"]

    records: List[Dict] = []
    interval_seconds = interval_minutes * 60

    for idx in range(len(track_sorted) - 1):
        start = track_sorted.iloc[idx]
        end = track_sorted.iloc[idx + 1]
        start_time = start["date"]
        end_time = end["date"]

        if idx == 0:
            records.append(start.to_dict())

        delta_seconds = (end_time - start_time).total_seconds()
        if delta_seconds <= 0:
            continue

        steps = int(delta_seconds // interval_seconds)
        if steps == 0:
            continue

        for step in range(1, steps + 1):
            ratio = (step * interval_seconds) / delta_seconds
            current_time = start_time + pd.Timedelta(seconds=step * interval_seconds)
            if current_time > end_time:
                current_time = end_time
                ratio = 1.0

            interpolated = {"date": current_time}
            for col in columns:
                start_val = start[col]
                end_val = end[col]
                if pd.isna(start_val) or pd.isna(end_val):
                    interpolated[col] = np.nan
                else:
                    interpolated[col] = start_val + ratio * (end_val - start_val)
            records.append(interpolated)

    if len(track_sorted) >= 1:
        records[-1] = track_sorted.iloc[-1].to_dict()

    return pd.DataFrame(records)


def create_instantaneous_wind_polygon(
    lat: float,
    lon: float,
    wind_radii_ne: float,
    wind_radii_se: float,
    wind_radii_sw: float,
    wind_radii_nw: float,
    *,
    buffer_deg: float = 0.02,
    arc_points_per_quadrant: int = 30,
) -> Polygon | None:
    """Create a wind extent polygon honouring circular quadrant arcs.

    The legacy implementation connected a single point per quadrant, forming a
    chord-based diamond. This variant samples multiple bearings per quadrant to
    approximate the true arc geometry. When fewer than three quadrants provide
    radii, we fall back to the buffered chord approach to avoid degenerate
    polygons.
    """

    radii = {
        "ne": wind_radii_ne,
        "se": wind_radii_se,
        "sw": wind_radii_sw,
        "nw": wind_radii_nw,
    }

    valid_quadrants = [quad for quad, radius in radii.items() if pd.notna(radius) and radius > 0]
    if not valid_quadrants:
        return None

    # For sparse quadrants the buffered chord method remains more stable.
    if len(valid_quadrants) <= 2:
        points: List[Point] = []
        bearings = {"ne": 45, "se": 135, "sw": 225, "nw": 315}
        for quad in valid_quadrants:
            radius = radii[quad]
            dest_lon, dest_lat = calculate_destination_point(lat, lon, bearings[quad], radius)
            points.append(Point(dest_lon, dest_lat))

        if len(points) == 1:
            return points[0].buffer(buffer_deg)

        from shapely.geometry import LineString

        line = LineString(points)
        return line.buffer(buffer_deg)

    # Build arc-based polygon for well-defined quadrants.
    arc_coords: List[Tuple[float, float]] = []
    for quad in ("ne", "se", "sw", "nw"):
        radius = radii.get(quad)
        if not pd.notna(radius) or radius <= 0:
            continue

        arc_points = generate_quadrant_arc_points(
            lat,
            lon,
            quad,
            radius,
            num_points=arc_points_per_quadrant,
            include_endpoint=True,
        )

        if not arc_points:
            continue

        if arc_coords:
            # Skip the first point to avoid duplicate coordinates where quadrants meet.
            arc_coords.extend(arc_points[1:])
        else:
            arc_coords.extend(arc_points)

    if len(arc_coords) < 3:
        from shapely.geometry import LineString

        line = LineString(arc_coords)
        return line.buffer(buffer_deg)

    polygon = Polygon(arc_coords)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    return polygon


def check_centroid_exposure_over_time(centroid: Point, interpolated_track: pd.DataFrame) -> pd.DataFrame:
    """Determine centroid exposure timeline at interpolated timesteps."""

    exposure_records: List[Dict] = []

    for _, row in interpolated_track.iterrows():
        polygon = create_instantaneous_wind_polygon(
            lat=row.get("lat"),
            lon=row.get("lon"),
            wind_radii_ne=row.get("wind_radii_64_ne"),
            wind_radii_se=row.get("wind_radii_64_se"),
            wind_radii_sw=row.get("wind_radii_64_sw"),
            wind_radii_nw=row.get("wind_radii_64_nw"),
        )

        is_inside = polygon.contains(centroid) if polygon is not None else False
        exposure_records.append({"date": row["date"], "is_inside": is_inside})

    return pd.DataFrame(exposure_records)


def calculate_duration_features(exposure_timeline: pd.DataFrame, interval_minutes: int = 15) -> Dict[str, object]:
    """Compute duration metrics from exposure timeline."""

    in_mask = exposure_timeline["is_inside"].values if not exposure_timeline.empty else np.array([])
    timestamps = exposure_timeline["date"].tolist()

    result = {
        "first_entry_time": None,
        "last_exit_time": None,
        "duration_in_envelope_hours": 0.0,
        "exposure_window_hours": 0.0,
        "continuous_exposure": False,
        "interpolated_points_count": len(exposure_timeline),
        "duration_source": "timeline",
    }

    if not in_mask.any():
        return result

    first_idx = int(np.argmax(in_mask))
    last_idx = len(in_mask) - 1 - int(np.argmax(in_mask[::-1]))

    result["first_entry_time"] = timestamps[first_idx]
    result["last_exit_time"] = timestamps[last_idx]

    duration_hours = in_mask.sum() * (interval_minutes / 60.0)
    window_hours = ((last_idx - first_idx) * interval_minutes) / 60.0

    result["duration_in_envelope_hours"] = float(duration_hours)
    result["exposure_window_hours"] = float(window_hours)

    segment = in_mask[first_idx : last_idx + 1]
    result["continuous_exposure"] = bool(segment.all())

    return result


def identify_incomplete_wind_radii_boundary(interpolated_track: pd.DataFrame) -> Dict[str, int]:
    """Find first/last indices where we have incomplete (<4) wind-radii quadrants.

    Returns:
        Dict with 'first_complete_idx' and 'last_complete_idx'
    """
    complete_mask = []

    for _, row in interpolated_track.iterrows():
        radii_values = [
            row.get("wind_radii_64_ne"),
            row.get("wind_radii_64_se"),
            row.get("wind_radii_64_sw"),
            row.get("wind_radii_64_nw"),
        ]
        # Count non-null radii
        valid_count = sum(1 for r in radii_values if not pd.isna(r) and r > 0)
        complete_mask.append(valid_count == 4)

    complete_mask = np.array(complete_mask)

    result = {
        "first_complete_idx": None,
        "last_complete_idx": None,
    }

    if not complete_mask.any():
        return result

    # Find first and last complete indices
    complete_indices = np.where(complete_mask)[0]
    result["first_complete_idx"] = int(complete_indices[0])
    result["last_complete_idx"] = int(complete_indices[-1])

    return result


def calculate_duration_for_tract(
    centroid: Point,
    track_df: pd.DataFrame,
    wind_threshold: str = "64kt",
    interval_minutes: int = 15,
    envelope=None,
    coverage=None,
) -> Dict[str, object]:
    """Main entry point for duration exposure features.

    Args:
        centroid: Tract centroid point
        track_df: Hurricane track data
        wind_threshold: Wind speed threshold (default "64kt")
        interval_minutes: Temporal interpolation interval (default 15)
        envelope: Optional alpha-shape envelope for edge interpolation fallback
        coverage: Optional exact wind-coverage union polygon. When provided this
            is used to validate whether interpolation is appropriate.

    Returns:
        Dictionary with duration metrics
    """
    from envelope_algorithm import impute_missing_wind_radii

    columns_required = {
        "date",
        "lat",
        "lon",
        f"wind_radii_{wind_threshold.replace('kt', '')}_ne",
        f"wind_radii_{wind_threshold.replace('kt', '')}_se",
        f"wind_radii_{wind_threshold.replace('kt', '')}_sw",
        f"wind_radii_{wind_threshold.replace('kt', '')}_nw",
    }
    missing = columns_required - set(track_df.columns)
    if missing:
        raise ValueError(f"track_df missing columns: {missing}")

    # Apply proportional imputation to extend through storm weakening
    track_imputed = impute_missing_wind_radii(track_df, wind_threshold=wind_threshold)

    prefix = wind_threshold.replace("kt", "")
    rename_map = {
        f"wind_radii_{prefix}_ne_imputed": "wind_radii_64_ne",
        f"wind_radii_{prefix}_se_imputed": "wind_radii_64_se",
        f"wind_radii_{prefix}_sw_imputed": "wind_radii_64_sw",
        f"wind_radii_{prefix}_nw_imputed": "wind_radii_64_nw",
    }

    track_subset = track_imputed[["date", "lat", "lon", *rename_map.keys()]].rename(columns=rename_map)

    interpolated = interpolate_track_temporal(track_subset, interval_minutes=interval_minutes)
    exposure = check_centroid_exposure_over_time(centroid, interpolated)
    duration = calculate_duration_features(exposure, interval_minutes=interval_minutes)

    # Determine which polygon (if any) can justify an interpolation fallback.
    candidate_polygon = None
    if coverage is not None:
        try:
            if coverage.contains(centroid):  # type: ignore[attr-defined]
                candidate_polygon = coverage
        except AttributeError:
            candidate_polygon = None

    if candidate_polygon is None and coverage is None and envelope is not None:
        try:
            if envelope.contains(centroid):
                candidate_polygon = envelope
        except AttributeError:
            candidate_polygon = None

    # Apply edge interpolation only when a candidate polygon confirms exposure.
    if (
        duration["duration_in_envelope_hours"] == 0.0
        and candidate_polygon is not None
    ):
        duration = _interpolate_duration_near_edge(
            centroid=centroid,
            interpolated_track=interpolated,
            envelope=candidate_polygon,
            interval_minutes=interval_minutes,
        )

    return duration


def _interpolate_duration_near_edge(
    centroid: Point,
    interpolated_track: pd.DataFrame,
    envelope,
    interval_minutes: int,
) -> Dict[str, object]:
    """Interpolate duration for tracts near envelope edge with incomplete wind-radii data.

    For tracts that fall within the envelope but have 0 duration (due to missing
    wind-radii data or edge effects), estimate duration by:
    1. Finding the temporal boundaries where complete wind-radii data exists
    2. Calculating distance from centroid to envelope boundary
    3. Linearly interpolating from max possible duration → 0 at edge

    Args:
        centroid: Tract centroid
        interpolated_track: Interpolated track data
        envelope: Alpha-shape envelope
        interval_minutes: Temporal resolution

    Returns:
        Updated duration dictionary with interpolated values
    """

    # Find where we have complete wind-radii data (all 4 quadrants)
    boundaries = identify_incomplete_wind_radii_boundary(interpolated_track)

    if boundaries["first_complete_idx"] is None:
        # No complete data - return zero duration
        return {
            "first_entry_time": None,
            "last_exit_time": None,
            "duration_in_envelope_hours": 0.0,
            "exposure_window_hours": 0.0,
            "continuous_exposure": False,
            "interpolated_points_count": len(interpolated_track),
            "duration_source": "edge_interpolation_failed",
        }

    # Calculate distance from centroid to envelope edge
    try:
        distance_to_edge = centroid.distance(envelope.boundary)
    except Exception:
        distance_to_edge = 0.0

    # Estimate maximum possible duration (time span of complete data)
    first_idx = boundaries["first_complete_idx"]
    last_idx = boundaries["last_complete_idx"]
    max_duration_hours = ((last_idx - first_idx) * interval_minutes) / 60.0

    # Linear interpolation: closer to edge = less duration
    # Assume edge buffer zone is ~0.2 degrees (~13 nm)
    edge_buffer_deg = 0.2
    if distance_to_edge >= edge_buffer_deg:
        # Far from edge - shouldn't have 0 duration, return minimal duration
        interpolated_duration = interval_minutes / 60.0  # At least 1 interval
    else:
        # Near edge - interpolate linearly
        distance_ratio = distance_to_edge / edge_buffer_deg
        interpolated_duration = max_duration_hours * distance_ratio

    # Estimate entry/exit times based on temporal boundaries
    first_time = interpolated_track.iloc[first_idx]["date"]
    last_time = interpolated_track.iloc[last_idx]["date"]

    return {
        "first_entry_time": first_time,
        "last_exit_time": last_time,
        "duration_in_envelope_hours": float(interpolated_duration),
        "exposure_window_hours": float(max_duration_hours),
        "continuous_exposure": False,
        "interpolated_points_count": len(interpolated_track),
        "duration_source": "edge_interpolation",
    }
