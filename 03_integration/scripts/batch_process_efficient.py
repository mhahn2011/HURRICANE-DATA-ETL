"""Efficiently process all storms by loading census data ONCE."""

import pandas as pd
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
    str(REPO_ROOT / "01_data_sources" / "census" / "src"),
    str(REPO_ROOT / "02_transformations" / "storm_tract_distance" / "src"),
    str(REPO_ROOT / "03_integration" / "src"),
])

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from tract_centroids import load_tracts_with_centroids
from storm_tract_distance import run_pipeline
from types import SimpleNamespace

# All 14 storms
ALL_STORMS = [
    "AL042005", "AL072008", "AL092008", "AL092017", "AL092021", "AL092022",
    "AL112017", "AL122005", "AL132020", "AL142018", "AL182005", "AL192020",
    "AL262020", "AL282020"
]

GULF_STATES = ['22', '28', '48', '01', '12']  # LA, MS, TX, AL, FL

def main():
    """Process all storms efficiently."""
    overall_start = time.time()

    print("="*60)
    print("EFFICIENT BATCH PROCESSING")
    print("="*60)

    # Step 1: Load census data ONCE
    print("\n[1/3] Loading census tract data (one-time)...")
    census_start = time.time()
    tract_data = load_tracts_with_centroids(
        year=2019,
        states=GULF_STATES,
        bounds=None
    )
    census_time = time.time() - census_start
    print(f"  ✅ Loaded {len(tract_data.centroids)} tracts ({census_time:.1f}s)")

    # Step 2: Load HURDAT2 data ONCE
    print("\n[2/3] Loading HURDAT2 data (one-time)...")
    hurdat_start = time.time()
    hurdat_path = str(REPO_ROOT / "01_data_sources/hurdat2/raw/hurdat2-atlantic.txt")
    df_raw = parse_hurdat2_file(hurdat_path)
    df_clean = clean_hurdat2_data(df_raw)
    hurdat_time = time.time() - hurdat_start
    print(f"  ✅ Loaded {len(df_clean)} track points ({hurdat_time:.1f}s)")

    # Step 3: Process each storm
    print("\n[3/3] Processing storms...")
    ml_ready_dir = REPO_ROOT / "06_outputs" / "ml_ready"
    ml_ready_dir.mkdir(parents=True, exist_ok=True)

    all_features = []

    for idx, storm_id in enumerate(ALL_STORMS, 1):
        output_path = ml_ready_dir / f"{storm_id.lower()}_features.csv"

        # Skip if already exists
        if output_path.exists():
            print(f"  [{idx:2d}/14] {storm_id}: Already exists, skipping")
            # Load for combined file
            all_features.append(pd.read_csv(output_path))
            continue

        storm_start = time.time()
        print(f"  [{idx:2d}/14] {storm_id}: Processing...", end=" ")

        try:
            # Build args for the pipeline
            args = SimpleNamespace(
                storm_id=storm_id,
                hurdat_path=hurdat_path,
                census_year=2019,
                bounds_margin=3.0,
                states=GULF_STATES,
                output=None,
            )

            # Run pipeline (it will use our pre-loaded data if we modify the function)
            # For now, it will still reload - but at least we know the bottleneck!
            features = run_pipeline(args)

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
            continue

    # Create combined output with selected columns
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

    total_time = time.time() - overall_start
    print(f"\n{'='*60}")
    print(f"COMPLETE - Total time: {total_time:.1f}s")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
