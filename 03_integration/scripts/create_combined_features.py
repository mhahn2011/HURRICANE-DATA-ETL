"""Combine all individual storm features into one table with selected columns."""

import pandas as pd
from pathlib import Path
import glob

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_READY_DIR = REPO_ROOT / "06_outputs" / "ml_ready"

# Columns to keep in the final combined table
FINAL_COLUMNS = [
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

def main():
    """Combine all storm feature files."""
    # Find all individual storm feature files
    feature_files = glob.glob(str(ML_READY_DIR / "al*_features.csv"))

    if not feature_files:
        print("❌ No feature files found!")
        return

    print(f"Found {len(feature_files)} storm feature files")

    all_data = []

    for file_path in sorted(feature_files):
        storm_file = Path(file_path).name
        print(f"  Loading {storm_file}...")

        try:
            df = pd.read_csv(file_path)

            # Check which columns exist
            available_cols = [col for col in FINAL_COLUMNS if col in df.columns]
            missing_cols = [col for col in FINAL_COLUMNS if col not in df.columns]

            if missing_cols:
                print(f"    ⚠️  Missing columns: {missing_cols}")

            # Select only available columns
            df_subset = df[available_cols]
            all_data.append(df_subset)

            print(f"    ✅ {len(df_subset):,} records")

        except Exception as e:
            print(f"    ❌ Error loading {storm_file}: {e}")
            continue

    if not all_data:
        print("❌ No data to combine!")
        return

    # Combine all storms
    combined = pd.concat(all_data, ignore_index=True)

    # Save combined output
    output_path = ML_READY_DIR / "storm_tract_features.csv"
    combined.to_csv(output_path, index=False)

    print(f"\n{'='*60}")
    print(f"COMBINED FEATURES CREATED")
    print(f"{'='*60}")
    print(f"Total storms: {len(all_data)}")
    print(f"Total records: {len(combined):,}")
    print(f"Columns: {list(combined.columns)}")
    print(f"Output: {output_path}")
    print(f"\nRecords by storm:")
    print(combined.groupby('storm_name').size().sort_values(ascending=False))

if __name__ == "__main__":
    main()
