"""
Batch generates QA/QC envelope visualizations for a predefined list of storms.
"""
import sys
from pathlib import Path
import pandas as pd

# Add project src path to allow importing modules
sys.path.insert(0, str(Path(__file__).parent))

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope
from visualize_envelope import save_qa_envelope_plot

# List of notable Gulf Coast hurricanes to generate QA plots for
STORMS_TO_PROCESS = [
    ('KATRINA', 2005),
    ('RITA', 2005),
    ('DENNIS', 2005),
    ('GUSTAV', 2008),
    ('IKE', 2008),
    ('HARVEY', 2017),
    ('IRMA', 2017),
    ('MICHAEL', 2018),
    ('LAURA', 2020),
    ('DELTA', 2020),
    ('ZETA', 2020),
    ('SALLY', 2020),
    ('IDA', 2021),
    ('IAN', 2022),
]

# Alpha values to test for the alpha shape algorithm
# Larger alpha = tighter fit
ALPHAS_TO_TEST = [0.4, 0.5, 0.6]

def main():
    """Main function to drive the batch processing of QA plots."""
    print("=" * 60)
    print("BATCH GENERATING CONCAVE HULL SENSITIVITY PLOTS")
    print("=" * 60)

    # --- 1. Load and Prepare Data ---
    hurdat_file = Path(__file__).parent.parent / "input_data" / "hurdat2-atlantic.txt"
    if not hurdat_file.exists():
        print(f"❌ ERROR: HURDAT2 data file not found at {hurdat_file}")
        return

    print("Loading and cleaning HURDAT2 data...")
    df_raw = parse_hurdat2_file(hurdat_file)
    df_clean = clean_hurdat2_data(df_raw)
    print(f"✅ Data loaded and cleaned. {len(df_clean)} records available.")

    # --- 2. Loop Through Storms and Generate Plots ---
    output_dir = Path(__file__).parent.parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    for storm_name, storm_year in STORMS_TO_PROCESS:
        print("-" * 50)
        print(f"Processing: {storm_name} ({storm_year})")

        storm_track_df = df_clean[
            (df_clean['storm_name'] == storm_name) &
            (df_clean['year'] == storm_year)
        ].sort_values('date').reset_index(drop=True)

        if storm_track_df.empty:
            print(f"⚠️ Warning: No track data found. Skipping.")
            continue

        envelopes_for_plotting = {}
        hull_points_to_plot = []
        for i, alpha in enumerate(ALPHAS_TO_TEST):
            print(f"  Generating envelope with alpha={alpha}...")
            envelope_poly, track_line, hull_points = create_storm_envelope(
                storm_track_df, 
                wind_threshold='64kt',
                alpha=alpha,
                verbose=False
            )
            if envelope_poly:
                envelopes_for_plotting[f"Alpha: {alpha}"] = envelope_poly
                if i == 0: # Only get points from the first iteration
                    hull_points_to_plot = hull_points

        if not envelopes_for_plotting:
            print(f"❌ ERROR: Could not generate any envelopes for {storm_name}. Skipping plot.")
            continue

        output_path = output_dir / f"sensitivity_envelope_{storm_name}_{storm_year}.png"

        save_qa_envelope_plot(
            storm_track_df=storm_track_df,
            envelopes_dict=envelopes_for_plotting,
            track_line=track_line,
            output_path=output_path,
            hull_points=hull_points_to_plot
        )

    print("-" * 50)
    print("\n✅ Batch processing complete.")


if __name__ == "__main__":
    main()
