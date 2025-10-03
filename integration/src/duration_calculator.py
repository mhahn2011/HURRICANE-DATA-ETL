"""Duration exposure calculations for storm-track interactions."""

from __future__ import annotations

import math
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT / "hurdat2" / "src"))

from envelope_algorithm import calculate_destination_point


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
) -> Polygon | None:
    """Create a wind extent polygon from quadrant radii."""

    radii = {
        "ne": wind_radii_ne,
        "se": wind_radii_se,
        "sw": wind_radii_sw,
        "nw": wind_radii_nw,
    }

    points: List[Point] = []
    bearings = {"ne": 45, "se": 135, "sw": 225, "nw": 315}

    for quad, radius in radii.items():
        if pd.isna(radius) or radius <= 0:
            continue
        dest_lon, dest_lat = calculate_destination_point(lat, lon, bearings[quad], radius)
        points.append(Point(dest_lon, dest_lat))

    if not points:
        return None

    if len(points) == 1:
        return points[0].buffer(0.001)

    if len(points) == 2:
        # Create line buffer for 2 points
        from shapely.geometry import LineString
        return LineString(points).buffer(0.001)

    # Need at least 3 points for polygon
    return Polygon([p.coords[0] for p in points]).convex_hull


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


def calculate_duration_for_tract(
    centroid: Point,
    track_df: pd.DataFrame,
    wind_threshold: str = "64kt",
    interval_minutes: int = 15,
) -> Dict[str, object]:
    """Main entry point for duration exposure features."""

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

    rename_map = {
        f"wind_radii_{wind_threshold.replace('kt', '')}_ne": "wind_radii_64_ne",
        f"wind_radii_{wind_threshold.replace('kt', '')}_se": "wind_radii_64_se",
        f"wind_radii_{wind_threshold.replace('kt', '')}_sw": "wind_radii_64_sw",
        f"wind_radii_{wind_threshold.replace('kt', '')}_nw": "wind_radii_64_nw",
    }

    track_subset = track_df[["date", "lat", "lon", *rename_map.keys()]].rename(columns=rename_map)

    interpolated = interpolate_track_temporal(track_subset, interval_minutes=interval_minutes)
    exposure = check_centroid_exposure_over_time(centroid, interpolated)
    duration = calculate_duration_features(exposure, interval_minutes=interval_minutes)
    return duration
