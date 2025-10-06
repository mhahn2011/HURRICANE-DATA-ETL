"""Ultra-fast batch processing using indexed HURDAT2 parser."""

import pandas as pd
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
    str(REPO_ROOT / "01_data_sources" / "census" / "src"),
    str(REPO_ROOT / "02_transformations" / "storm_tract_distance" / "src"),
    str(REPO_ROOT / "02_transformations" / "lead_time" / "src"),
    str(REPO_ROOT / "03_integration" / "src"),
])

from parse_raw_indexed import parse_storm_by_id, get_or_build_index
from profile_clean import clean_hurdat2_data
from storm_tract_distance import (
    build_storm_track, track_bounds, haversine_nm,
    create_wind_coverage_envelope, quadrant_for_offset
)
from tract_centroids import load_tracts_with_centroids
from wind_interpolation import calculate_max_wind_experienced
from duration_calculator import calculate_duration_for_tract
from lead_time_calculator import calculate_lead_times
from intensification_features import calculate_intensification_features
import numpy as np

# All 14 target storms
ALL_STORMS = [
    "AL042005", "AL072008", "AL092008", "AL092017", "AL092021", "AL092022",
    "AL112017", "AL122005", "AL132020", "AL142018", "AL182005", "AL192020",
    "AL262020", "AL282020"
]

GULF_STATES = ['22', '28', '48', '01', '12']  # LA, MS, TX, AL, FL

def process_storm_fast(storm_id: str, tract_data, hurdat_path: str, index: dict) -> pd.DataFrame:
    """Process a single storm with indexed parsing."""

    # Parse only this storm's data (FAST!)
    df_raw = parse_storm_by_id(hurdat_path, storm_id, index=index)
    df_clean = clean_hurdat2_data(df_raw)
    track = df_clean.sort_values('date').reset_index(drop=True)

    if track.empty:
        return pd.DataFrame()

    # Get storm bounds
    bounds = track_bounds(track, margin_deg=3.0)

    # Filter tracts to bounding box
    centroids_df = tract_data.centroids
    in_bounds = (
        (centroids_df['centroid_lon'] >= bounds[0]) &
        (centroids_df['centroid_lat'] >= bounds[1]) &
        (centroids_df['centroid_lon'] <= bounds[2]) &
        (centroids_df['centroid_lat'] <= bounds[3])
    )
    centroids_filtered = centroids_df[in_bounds].copy()

    if centroids_filtered.empty:
        return pd.DataFrame()

    # Create wind envelope
    envelope, track_line, interpolated_track = create_wind_coverage_envelope(
        track, wind_threshold="64kt", interval_minutes=15
    )

    # Calculate distances
    distances = []
    for _, tract_row in centroids_filtered.iterrows():
        tract_lat = tract_row['centroid_lat']
        tract_lon = tract_row['centroid_lon']

        # Distance to each track point
        dists_nm = haversine_nm(
            np.full(len(track), tract_lat),
            np.full(len(track), tract_lon),
            track['lat'].values,
            track['lon'].values
        )

        min_idx = np.argmin(dists_nm)
        min_dist_nm = dists_nm[min_idx]
        min_dist_km = min_dist_nm * 1.852

        nearest_point = track.iloc[min_idx]
        lat_diff = tract_lat - nearest_point['lat']
        lon_diff = tract_lon - nearest_point['lon']
        quadrant = quadrant_for_offset(lat_diff, lon_diff)

        distances.append({
            'tract_geoid': tract_row['tract_geoid'],
            'distance_nm': min_dist_nm,
            'distance_km': min_dist_km,
            'nearest_quadrant': quadrant,
            'nearest_track_idx': min_idx,
            'centroid_lat': tract_lat,
            'centroid_lon': tract_lon,
        })

    dist_df = pd.DataFrame(distances)

    # Calculate wind features
    wind_results = []
    for _, row in dist_df.iterrows():
        wind_data = calculate_max_wind_experienced(
            tract_lat=row['centroid_lat'],
            tract_lon=row['centroid_lon'],
            track_df=track,
            nearest_track_idx=row['nearest_track_idx']
        )
        wind_results.append({
            'tract_geoid': row['tract_geoid'],
            **wind_data
        })

    wind_df = pd.DataFrame(wind_results)

    # Merge distance + wind
    features = dist_df.merge(wind_df, on='tract_geoid', how='left')

    # Calculate duration
    duration_results = []
    for _, row in features.iterrows():
        duration_data = calculate_duration_for_tract(
            tract_lat=row['centroid_lat'],
            tract_lon=row['centroid_lon'],
            interpolated_track=interpolated_track,
            wind_threshold_kt=64
        )
        duration_results.append({
            'tract_geoid': row['tract_geoid'],
            **duration_data
        })

    duration_df = pd.DataFrame(duration_results)
    features = features.merge(duration_df, on='tract_geoid', how='left')

    # Calculate lead times
    lead_time_results = []
    for _, row in features.iterrows():
        lead_times = calculate_lead_times(
            tract_lat=row['centroid_lat'],
            tract_lon=row['centroid_lon'],
            track_df=track
        )
        lead_time_results.append({
            'tract_geoid': row['tract_geoid'],
            **lead_times
        })

    lead_time_df = pd.DataFrame(lead_time_results)
    features = features.merge(lead_time_df, on='tract_geoid', how='left')

    # Add storm metadata
    features['storm_id'] = storm_id
    features['storm_name'] = track.iloc[0]['storm_name']

    # Add intensification features
    intensification = calculate_intensification_features(track)
    for key, value in intensification.items():
        features[key] = value

    return features


def main():
    """Process all storms efficiently."""
    overall_start = time.time()

    print("="*60)
    print("ULTRA-FAST BATCH PROCESSING")
    print("="*60)

    hurdat_path = str(REPO_ROOT / "01_data_sources/hurdat2/raw/hurdat2-atlantic.txt")

    # Step 1: Build HURDAT2 index (one-time, cached)
    print("\n[1/3] Building HURDAT2 index...")
    index_start = time.time()
    index = get_or_build_index(hurdat_path)
    index_time = time.time() - index_start
    print(f"  ✅ Indexed {len(index)} storms ({index_time:.2f}s)")

    # Step 2: Load census data ONCE
    print("\n[2/3] Loading census tract data...")
    census_start = time.time()
    tract_data = load_tracts_with_centroids(
        year=2019,
        states=GULF_STATES,
        bounds=None
    )
    census_time = time.time() - census_start
    print(f"  ✅ Loaded {len(tract_data.centroids)} tracts ({census_time:.1f}s)")

    # Step 3: Process each storm
    print("\n[3/3] Processing storms...")
    ml_ready_dir = REPO_ROOT / "06_outputs" / "ml_ready"
    ml_ready_dir.mkdir(parents=True, exist_ok=True)

    all_features = []

    for idx, storm_id in enumerate(ALL_STORMS, 1):
        output_path = ml_ready_dir / f"{storm_id.lower()}_features.csv"

        # Skip if already exists
        if output_path.exists():
            print(f"  [{idx:2d}/14] {storm_id}: Already exists, loading...")
            all_features.append(pd.read_csv(output_path))
            continue

        storm_start = time.time()
        print(f"  [{idx:2d}/14] {storm_id}: Processing...", end=" ", flush=True)

        try:
            features = process_storm_fast(storm_id, tract_data, hurdat_path, index)

            if not features.empty:
                features.to_csv(output_path, index=False)
                all_features.append(features)
                elapsed = time.time() - storm_start
                print(f"✅ ({elapsed:.1f}s, {len(features)} records)")
            else:
                print("⚠️  No records")

        except Exception as e:
            elapsed = time.time() - storm_start
            print(f"❌ ({elapsed:.1f}s) {e}")
            import traceback
            traceback.print_exc()
            continue

    # Step 4: Create combined output with selected columns
    if all_features:
        print("\n[4/4] Creating combined feature table...")
        combined = pd.concat(all_features, ignore_index=True)

        # Select only the columns you want
        final_cols = [
            "storm_name",
            "tract_geoid",
            "distance_km",
            "max_wind_experienced_kt",
            "duration_in_envelope_hours",
            "lead_time_cat1_hours",
            "lead_time_cat2_hours",
            "lead_time_cat3_hours",
            "lead_time_cat4_hours",
        ]

        available_cols = [col for col in final_cols if col in combined.columns]
        combined_filtered = combined[available_cols]

        output_path = ml_ready_dir / "storm_tract_features.csv"
        combined_filtered.to_csv(output_path, index=False)

        print(f"  ✅ Saved {len(combined_filtered):,} records to {output_path.name}")
        print(f"  Columns: {list(combined_filtered.columns)}")
        print(f"\n  Records by storm:")
        print(combined_filtered.groupby('storm_name').size().sort_values(ascending=False).to_string())

    total_time = time.time() - overall_start
    print(f"\n{'='*60}")
    print(f"COMPLETE - Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
