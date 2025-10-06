"""Process priority storms using existing pipeline with optimized HURDAT2 parsing."""

import pandas as pd
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "03_integration" / "src"))
sys.path.insert(0, str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"))

from feature_pipeline import save_features_for_storm

# Priority storms: HARVEY, LAURA, MICHAEL, IRMA, IAN
PRIORITY_STORMS = [
    ("AL092017", "HARVEY"),
    ("AL132020", "LAURA"),
    ("AL142018", "MICHAEL"),
    ("AL112017", "IRMA"),
    ("AL092022", "IAN"),
]

def main():
    """Process priority storms."""
    overall_start = time.time()

    print("="*60)
    print("PRIORITY STORM PROCESSING")
    print("="*60)
    print(f"Storms: {', '.join([name for _, name in PRIORITY_STORMS])}")
    print("="*60)

    ml_ready_dir = REPO_ROOT / "06_outputs" / "ml_ready"
    ml_ready_dir.mkdir(parents=True, exist_ok=True)

    processed_count = 0

    for idx, (storm_id, storm_name) in enumerate(PRIORITY_STORMS, 1):
        output_path = ml_ready_dir / f"{storm_id.lower()}_features.csv"

        # Skip if already exists
        if output_path.exists():
            print(f"[{idx}/{len(PRIORITY_STORMS)}] {storm_name:8s} ({storm_id}): Already exists ✓")
            continue

        storm_start = time.time()
        print(f"[{idx}/{len(PRIORITY_STORMS)}] {storm_name:8s} ({storm_id}): Processing...", end=" ", flush=True)

        try:
            save_features_for_storm(
                storm_id=storm_id,
                output_path=output_path,
            )
            elapsed = time.time() - storm_start

            # Check file size
            df = pd.read_csv(output_path)
            print(f"✅ ({elapsed:.1f}s, {len(df):,} records)")
            processed_count += 1

        except Exception as e:
            elapsed = time.time() - storm_start
            print(f"❌ ({elapsed:.1f}s)")
            print(f"    Error: {e}")
            continue

    # Create combined output
    print("\nCreating combined feature table...")

    all_storm_files = list(ml_ready_dir.glob("al*_features.csv"))
    all_features = []
    for f in all_storm_files:
        all_features.append(pd.read_csv(f))

    if all_features:
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

        print(f"✅ Saved {len(combined_filtered):,} records to {output_path.name}")
        print(f"\nRecords by storm:")
        storm_counts = combined_filtered.groupby('storm_name').size().sort_values(ascending=False)
        for storm, count in storm_counts.items():
            print(f"  {storm:12s} {count:6,}")

    total_time = time.time() - overall_start
    print(f"\n{'='*60}")
    print(f"New storms processed: {processed_count}")
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
