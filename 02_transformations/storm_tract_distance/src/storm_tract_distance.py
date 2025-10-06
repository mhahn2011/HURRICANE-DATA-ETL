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

from shapely.geometry import LineString, Point

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.extend(
    [
        str(REPO_ROOT / "01_data_sources" / "census" / "src"),
        str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
        str(REPO_ROOT / "02_transformations" / "wind_coverage_envelope" / "src"),
        str(REPO_ROOT / "02_transformations" / "wind_interpolation" / "src"),
        str(REPO_ROOT / "02_transformations" / "duration" / "src"),
        str(REPO_ROOT / "02_transformations" / "lead_time" / "src"),
    ]
)

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope, impute_missing_wind_radii
from wind_interpolation import calculate_max_wind_experienced
from duration_calculator import (
    calculate_duration_for_tract,
    interpolate_track_temporal,
    create_instantaneous_wind_polygon,
)
from lead_time_calculator import calculate_lead_times
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


def create_wind_coverage_envelope(track: pd.DataFrame, wind_threshold: str = "64kt", interval_minutes: int = 15):
    """Create envelope from union of actual wind polygons (more accurate than alpha shape).

    This approach eliminates false positives by only including areas that actually
    experience winds ≥ threshold. Uses proportional imputation to extend coverage
    through storm weakening phases.

    Args:
        track: Storm track DataFrame with wind radii columns
        wind_threshold: Wind threshold ('64kt', '50kt', '34kt')
        interval_minutes: Temporal interpolation interval

    Returns:
        tuple: (wind_coverage_polygon, track_line, interpolated_track_df)
    """
    from shapely.ops import unary_union

    # Apply imputation to extend through weakening
    track_imputed = impute_missing_wind_radii(track, wind_threshold=wind_threshold)

    # Prepare for interpolation (numeric columns only)
    prefix = wind_threshold.replace("kt", "")
    imputed_cols = [f"wind_radii_{prefix}_{q}_imputed" for q in ["ne", "se", "sw", "nw"]]

    track_subset = track_imputed[['date', 'lat', 'lon'] + imputed_cols].copy()
    track_subset = track_subset.rename(columns={
        f"wind_radii_{prefix}_ne_imputed": f"wind_radii_{prefix}_ne",
        f"wind_radii_{prefix}_se_imputed": f"wind_radii_{prefix}_se",
        f"wind_radii_{prefix}_sw_imputed": f"wind_radii_{prefix}_sw",
        f"wind_radii_{prefix}_nw_imputed": f"wind_radii_{prefix}_nw",
    })

    # Interpolate track temporally
    interpolated = interpolate_track_temporal(track_subset, interval_minutes=interval_minutes)

    # Create all instantaneous wind polygons (NO BUFFER for exact coverage)
    wind_polygons = []
    for _, row in interpolated.iterrows():
        poly = create_instantaneous_wind_polygon(
            lat=row['lat'],
            lon=row['lon'],
            wind_radii_ne=row[f'wind_radii_{prefix}_ne'],
            wind_radii_se=row[f'wind_radii_{prefix}_se'],
            wind_radii_sw=row[f'wind_radii_{prefix}_sw'],
            wind_radii_nw=row[f'wind_radii_{prefix}_nw'],
            buffer_deg=0.0,  # No buffer - exact wind radii coverage only
        )
        if poly and not poly.is_empty:
            wind_polygons.append(poly)

    if not wind_polygons:
        return None, LineString(list(zip(track['lon'], track['lat']))), interpolated

    # Union all polygons to create coverage envelope
    wind_coverage = unary_union(wind_polygons)

    # Create track line
    track_line = LineString(list(zip(track['lon'], track['lat'])))

    return wind_coverage, track_line, interpolated


def compute_min_distance_features(
    centroids: pd.DataFrame,
    track: pd.DataFrame,
) -> pd.DataFrame:
    """Return per-tract proximity metrics relative to the storm track."""

    centroid_lats = centroids.geometry.y.values
    centroid_lons = centroids.geometry.x.values

    track_lats = track["lat"].values
    track_lons = track["lon"].values

    if len(track_lats) >= 2:
        track_geometry = LineString(list(zip(track_lons, track_lats)))
    else:
        track_geometry = Point(track_lons[0], track_lats[0])

    min_dist_deg = []
    for lon, lat in zip(centroid_lons, centroid_lats):
        centroid_point = Point(lon, lat)
        dist_deg = centroid_point.distance(track_geometry)
        min_dist_deg.append(dist_deg)

    min_dist_deg = np.array(min_dist_deg)
    min_dist_nm = min_dist_deg * 60.0
    min_dist_km = min_dist_nm * (EARTH_RADIUS_KM / EARTH_RADIUS_NM)

    # Still need nearest track point for quadrant/wind radii
    distances_to_points_nm = haversine_nm(
        centroid_lats[:, None],
        centroid_lons[:, None],
        track_lats[None, :],
        track_lons[None, :],
    )
    min_idx = distances_to_points_nm.argmin(axis=1)

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
            "STATEFP": centroids["STATEFP"].values,
            "COUNTYFP": centroids["COUNTYFP"].values,
            "centroid_lat": centroid_lats,
            "centroid_lon": centroid_lons,
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

    # Use wind coverage envelope (union of actual wind polygons) instead of alpha shape
    # This eliminates false positives from alpha shape approximation overshoot
    wind_coverage, track_line, _ = create_wind_coverage_envelope(track, wind_threshold="64kt", interval_minutes=15)
    if wind_coverage is None:
        raise ValueError("Failed to generate wind coverage envelope for storm; cannot compute features")

    # Filter centroids to only those within actual wind coverage
    centroids_in_coverage = centroids[centroids.geometry.within(wind_coverage)].reset_index(drop=True)
    if centroids_in_coverage.empty:
        return pd.DataFrame()

    # Keep alpha shape for visualization/reference only
    alpha_envelope, _, _ = create_storm_envelope(track, wind_threshold="64kt", alpha=0.6)
    envelope = alpha_envelope if alpha_envelope else wind_coverage

    base_features = compute_min_distance_features(centroids_in_coverage, track).reset_index(drop=True)

    wind_rows = []
    duration_rows = []
    lead_time_rows = []
    for idx, centroid_geom in enumerate(centroids_in_coverage.geometry):
        # Extract wind radii from the nearest track point for this centroid
        nearest_point = track_line.interpolate(track_line.project(centroid_geom))
        track_distances = track.apply(
            lambda row: ((row['lat'] - nearest_point.y) ** 2 + (row['lon'] - nearest_point.x) ** 2) ** 0.5,
            axis=1
        )
        nearest_track_idx = track_distances.idxmin()
        nearest_track_row = track.loc[nearest_track_idx]

        wind_radii = {
            "wind_radii_34_ne": nearest_track_row.get("wind_radii_34_ne"),
            "wind_radii_34_se": nearest_track_row.get("wind_radii_34_se"),
            "wind_radii_34_sw": nearest_track_row.get("wind_radii_34_sw"),
            "wind_radii_34_nw": nearest_track_row.get("wind_radii_34_nw"),
            "wind_radii_50_ne": nearest_track_row.get("wind_radii_50_ne"),
            "wind_radii_50_se": nearest_track_row.get("wind_radii_50_se"),
            "wind_radii_50_sw": nearest_track_row.get("wind_radii_50_sw"),
            "wind_radii_50_nw": nearest_track_row.get("wind_radii_50_nw"),
            "wind_radii_64_ne": nearest_track_row.get("wind_radii_64_ne"),
            "wind_radii_64_se": nearest_track_row.get("wind_radii_64_se"),
            "wind_radii_64_sw": nearest_track_row.get("wind_radii_64_sw"),
            "wind_radii_64_nw": nearest_track_row.get("wind_radii_64_nw"),
        }

        try:
            wind_data = calculate_max_wind_experienced(
                centroid=centroid_geom,
                track_line=track_line,
                track_df=track,
                envelope=envelope,
                wind_radii=wind_radii,
            )
        except ValueError:
            wind_data = {
                "max_wind_experienced_kt": np.nan,
                "center_wind_at_approach_kt": np.nan,
                "distance_to_envelope_edge_nm": np.nan,
                "nearest_track_point_lat": np.nan,
                "nearest_track_point_lon": np.nan,
                "radius_max_wind_at_approach_nm": np.nan,
                "inside_eyewall": np.nan,
                "wind_source": "error",
            }
        wind_rows.append(wind_data)

        duration_rows.append(
            calculate_duration_for_tract(
                centroid=centroid_geom,
                track_df=track,
                wind_threshold="64kt",
                interval_minutes=15,
                envelope=envelope,
                coverage=wind_coverage,
            )
        )

        # Calculate lead time features
        nearest_approach_time = base_features.loc[idx, 'storm_time']
        lead_time_data = calculate_lead_times(
            track_df=track,
            nearest_approach_time=nearest_approach_time
        )
        lead_time_rows.append(lead_time_data)

    wind_df = pd.DataFrame(wind_rows)
    duration_df = pd.DataFrame(duration_rows)
    lead_time_df = pd.DataFrame(lead_time_rows)

    combined = pd.concat([base_features, wind_df, duration_df, lead_time_df], axis=1)

    # Filter out false positives: tracts with negligible exposure (<0.25 hours)
    # These can occur from wind coverage union bridging between non-overlapping polygons
    combined = combined[combined['duration_in_envelope_hours'] >= 0.25].reset_index(drop=True)

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
