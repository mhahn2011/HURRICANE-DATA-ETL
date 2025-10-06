"""Process all 14 hurricanes and generate final unified CSV."""

import pandas as pd
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "03_integration" / "src"))
sys.path.insert(0, str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"))
sys.path.insert(0, str(REPO_ROOT / "02_transformations" / "storm_tract_distance" / "src"))

from feature_pipeline import extract_all_features_for_storm

def main():
    """
    Process all 14 Gulf Coast hurricanes (2005-2022).

    Storms to process:
        KATRINA (2005), RITA (2005), DENNIS (2005)
        GUSTAV (2008), IKE (2008)
        HARVEY (2017), IRMA (2017)
        MICHAEL (2018)
        LAURA (2020), DELTA (2020), ZETA (2020), SALLY (2020)
        IDA (2021)
        IAN (2022)

    Steps:
    1. Load storm list from batch_processing_summary.csv
    2. For each storm:
        a. Extract all features using feature_pipeline.py
        b. Append to master DataFrame
    3. Save unified output: integration/outputs/storm_tract_features.csv
    4. Generate summary statistics
    """
    # Load storm list
    summary_path = REPO_ROOT / "01_data_sources" / "hurdat2" / "processed" / "batch_processing_summary.csv"
    storms = pd.read_csv(summary_path)

    all_features = []

    for idx, storm_row in storms.iterrows():
        storm_id = storm_row['storm_id']
        storm_name = storm_row['name']
        year = storm_row['year']

        print(f"\n{'='*60}")
        print(f"Processing: {storm_name} ({year}) - {storm_id}")
        print(f"{'='*60}")

        try:
            # Extract features for this storm
            storm_features = extract_all_features_for_storm(storm_id)
            if storm_features.empty:
                print(f"⚠️ No tracts found for {storm_name}; skipping")
                continue

            # Persist per-storm features for dashboard usage
            per_storm_path = (
                REPO_ROOT / "03_integration" / "outputs" / f"{storm_id.lower()}_features_complete.csv"
            )
            per_storm_path.parent.mkdir(parents=True, exist_ok=True)
            storm_features.to_csv(per_storm_path, index=False)

            all_features.append(storm_features)

            print(f"✅ Extracted {len(storm_features)} tract features")

        except Exception as e:
            print(f"❌ Error processing {storm_name}: {e}")
            continue

    # Concatenate all storms
    final_df = pd.concat(all_features, ignore_index=True)

    # Save unified output
    output_path = REPO_ROOT / "03_integration" / "outputs" / "storm_tract_features.csv"
    output_path.parent.mkdir(exist_ok=True, parents=True)
    final_df.to_csv(output_path, index=False)

    # Summary
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Total storms processed: {len(all_features)}")
    print(f"Total storm-tract records: {len(final_df):,}")
    print(f"Output saved to: {output_path}")
    print(f"\nRecords by storm:")
    print(final_df.groupby(['storm_name', 'year']).size().sort_values(ascending=False))

if __name__ == "__main__":
    main()
