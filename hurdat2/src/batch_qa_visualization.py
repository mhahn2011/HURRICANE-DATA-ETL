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
    ('IDA', 2021), # The primary test case
    ('LAURA', 2020),
    ('MICHAEL', 2018),
    ('HARVEY', 2017),
    ('ISAAC', 2012),
    ('IKE', 2008),
    ('GUSTAV', 2008),
    ('RITA', 2005),
    ('KATRINA', 2005), 
]

def main():
    """Main function to drive the batch processing of QA plots."""
    print("=" * 60)
    print("BATCH GENERATING QA/QC ENVELOPE VISUALIZATIONS")
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

        # Select the track data for the current storm
        storm_track_df = df_clean[
            (df_clean['storm_name'] == storm_name) &
            (df_clean['year'] == storm_year)
        ].sort_values('date').reset_index(drop=True)

        if storm_track_df.empty:
            print(f"⚠️ Warning: No track data found for {storm_name} ({storm_year}). Skipping.")
            continue

        print(f"  Found {len(storm_track_df)} track points. Creating 64kt envelope...")
        
        # Generate the 64-knot envelope for this storm
        envelope_poly, track_line, _ = create_storm_envelope(
            storm_track_df, 
            wind_threshold='64kt',
            verbose=False
        )

        if envelope_poly is None:
            print(f"❌ ERROR: Could not generate envelope for {storm_name}. Skipping plot.")
            continue

        # Define a unique output path for the plot
        output_path = output_dir / f"qa_envelope_{storm_name}_{storm_year}.png"

        # Generate and save the QA/QC plot
        save_qa_envelope_plot(
            storm_track_df=storm_track_df,
            envelope_poly=envelope_poly,
            track_line=track_line,
            output_path=output_path
        )

    print("-" * 50)
    print("\n✅ Batch processing complete.")


if __name__ == "__main__":
    main()
