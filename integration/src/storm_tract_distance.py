"""Compute tract-level proximity and wind metrics for a single hurricane track.

This script stitches together hurricane track data and census tract centroids to
produce a table keyed by (storm, tract). It reports minimum distance to the
track centreline as well as interpolated "max wind experienced" using the
concave-hull decay model.

Usage example (once TIGER/Line data is available):

    python integration/src/storm_tract_distance.py --storm-id AL092021 \
        --output integration/outputs/ida_tract_distances.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend(
    [
        str(REPO_ROOT / "census" / "src"),
        str(REPO_ROOT / "hurdat2" / "src"),
        str(REPO_ROOT / "integration" / "src"),
    ]
)

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope
from wind_interpolation import calculate_max_wind_experienced
from duration_calculator import calculate_duration_for_tract
from tract_centroids import load_tracts_with_centroids


EARTH_RADIUS_NM = 3440.065  # nautical miles
EARTH_RADIUS_KM = 6371.0    # kilometres


def haversine_nm(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Return great-circle distance in nautical miles."""

    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return EARTH_RADIUS_NM * c


def build_storm_track(df_clean: pd.DataFrame, storm_id: str) -> pd.DataFrame:
    """Filter cleaned dataframe to a single storm ordered by time."""

    track = df_clean[df_clean["storm_id"] == storm_id].sort_values("date").reset_index(drop=True)
    if track.empty:
        raise ValueError(f"Storm {storm_id} not found in cleaned dataset")
    return track


def track_bounds(track: pd.DataFrame, margin_deg: float = 3.0) -> Tuple[float, float, float, float]:
    """Bounding box for the storm track with optional margin."""

    min_lat, max_lat = track["lat"].min(), track["lat"].max()
    min_lon, max_lon = track["lon"].min(), track["lon"].max()
    return (
        min_lon - margin_deg,
        min_lat - margin_deg,
        max_lon + margin_deg,
        max_lat + margin_deg,
    )


def quadrant_for_offset(lat_diff: float, lon_diff: float) -> str:
    """Return NE/SE/SW/NW quadrant label for the offset from track point to centroid."""

    if lat_diff >= 0 and lon_diff >= 0:
        return "ne"
    if lat_diff < 0 <= lon_diff:
        return "se"
    if lat_diff < 0 and lon_diff < 0:
        return "sw"
    return "nw"


def compute_min_distance_features(
    centroids: pd.DataFrame,
    track: pd.DataFrame,
) -> pd.DataFrame:
    """Return per-tract proximity metrics relative to the storm track."""

    centroid_lats = centroids.geometry.y.values
    centroid_lons = centroids.geometry.x.values

    track_lats = track["lat"].values
    track_lons = track["lon"].values

    # Broadcast centroid distances to each track point (n_tracs x n_points)
    distances_nm = haversine_nm(
        centroid_lats[:, None],
        centroid_lons[:, None],
        track_lats[None, :],
        track_lons[None, :],
    )

    min_idx = distances_nm.argmin(axis=1)
    min_dist_nm = distances_nm.min(axis=1)
    min_dist_km = min_dist_nm * (EARTH_RADIUS_KM / EARTH_RADIUS_NM)

    nearest_track_rows = track.iloc[min_idx].reset_index(drop=True)

    # Determine quadrant-relative 64kt radius at nearest track point
    quadrant_labels = []
    radius_nm = []
    within_64 = []

    for centroid_lat, centroid_lon, track_row, distance_nm in zip(
        centroid_lats, centroid_lons, nearest_track_rows.itertuples(index=False), min_dist_nm
    ):
        lat_diff = centroid_lat - track_row.lat
        lon_diff = centroid_lon - track_row.lon
        quad = quadrant_for_offset(lat_diff, lon_diff)
        quadrant_labels.append(quad.upper())

        radius_col = f"wind_radii_64_{quad}"
        radius_value = getattr(track_row, radius_col, None)
        radius_nm.append(radius_value)

        if pd.isna(radius_value):
            within_64.append(None)
        else:
            within_64.append(distance_nm <= radius_value)

    result = pd.DataFrame(
        {
            "tract_geoid": centroids["GEOID"].values,
            "storm_id": nearest_track_rows["storm_id"].values,
            "storm_name": nearest_track_rows["storm_name"].values,
            "storm_time": nearest_track_rows["date"].values,
            "distance_nm": min_dist_nm,
            "distance_km": min_dist_km,
            "nearest_quadrant": quadrant_labels,
            "radius_64_nm": radius_nm,
            "within_64kt": within_64,
        }
    )

    result["storm_tract_id"] = result["storm_id"] + "_" + result["tract_geoid"].astype(str)
    return result


def run_pipeline(args: argparse.Namespace) -> pd.DataFrame:
    data_root = Path(args.hurdat_path).resolve()

    df_raw = parse_hurdat2_file(str(data_root))
    df_clean = clean_hurdat2_data(df_raw)
    track = build_storm_track(df_clean, args.storm_id)

    bounds = track_bounds(track, margin_deg=args.bounds_margin)

    columns = ["GEOID", "STATEFP", "COUNTYFP", "TRACTCE"]
    tract_data = load_tracts_with_centroids(
        year=args.census_year,
        bounds=bounds,
        columns=columns,
        states=args.states,
    )

    centroids = tract_data.centroids
    if centroids.empty:
        raise ValueError("No census tract centroids fell within the computed bounds; widen the margin")

    envelope, track_line, _ = create_storm_envelope(track, wind_threshold="64kt", alpha=0.6)
    if envelope is None:
        raise ValueError("Failed to generate envelope for storm; cannot compute wind features")

    centroids_in_envelope = centroids[centroids.geometry.within(envelope)].reset_index(drop=True)
    if centroids_in_envelope.empty:
        return pd.DataFrame()

    base_features = compute_min_distance_features(centroids_in_envelope, track).reset_index(drop=True)

    wind_rows = []
    duration_rows = []
    for centroid_geom in centroids_in_envelope.geometry:
        try:
            wind_data = calculate_max_wind_experienced(
                centroid=centroid_geom,
                track_line=track_line,
                track_df=track,
                envelope=envelope,
            )
        except ValueError:
            wind_data = {
                "max_wind_experienced_kt": np.nan,
                "center_wind_at_approach_kt": np.nan,
                "distance_to_envelope_edge_nm": np.nan,
                "nearest_track_point_lat": np.nan,
                "nearest_track_point_lon": np.nan,
            }
        wind_rows.append(wind_data)

        duration_rows.append(
            calculate_duration_for_tract(
                centroid=centroid_geom,
                track_df=track,
                wind_threshold="64kt",
                interval_minutes=15,
            )
        )

    wind_df = pd.DataFrame(wind_rows)
    duration_df = pd.DataFrame(duration_rows)

    combined = pd.concat([base_features, wind_df, duration_df], axis=1)
    return combined


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute tract/storm proximity features")
    parser.add_argument("--storm-id", required=True, help="Storm ID, e.g., AL092021")
    parser.add_argument(
        "--hurdat-path",
        default="hurdat2/input_data/hurdat2-atlantic.txt",
        help="Path to raw HURDAT2 text file",
    )
    parser.add_argument("--census-year", type=int, default=2019, help="TIGER/Line tract vintage")
    parser.add_argument(
        "--bounds-margin",
        type=float,
        default=3.0,
        help="Padding in degrees to expand the track bounding box",
    )
    parser.add_argument(
        "--states",
        nargs="*",
        help="Optional list of state FIPS codes to restrict tract loading (requires per-state TIGER ZIPs)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional CSV output path (written if provided)",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features = run_pipeline(args)

    print(f"Computed features for {len(features):,} tract centroids")
    print(features.head())

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        features.to_csv(args.output, index=False)
        print(f"Saved features to {args.output}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
