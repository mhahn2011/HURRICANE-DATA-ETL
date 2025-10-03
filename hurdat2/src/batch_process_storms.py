"""
Batch process multiple hurricanes to generate envelopes and visualizations
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope
from visualize_envelope import create_map_visualization


# Hurricane list from user
HURRICANES = [
    {"name": "KATRINA", "year": 2005},
    {"name": "RITA", "year": 2005},
    {"name": "DENNIS", "year": 2005},
    {"name": "GUSTAV", "year": 2008},
    {"name": "IKE", "year": 2008},
    {"name": "HARVEY", "year": 2017},
    {"name": "IRMA", "year": 2017},
    {"name": "MICHAEL", "year": 2018},
    {"name": "LAURA", "year": 2020},
    {"name": "DELTA", "year": 2020},
    {"name": "ZETA", "year": 2020},
    {"name": "SALLY", "year": 2020},
    {"name": "IDA", "year": 2021},
    {"name": "IAN", "year": 2022},
]


def find_storm_in_data(df_clean, storm_name, year):
    """Find storm in HURDAT2 data by name and year"""
    matches = df_clean[
        df_clean['storm_name'].str.contains(storm_name, na=False) &
        (df_clean['year'] == year)
    ]

    if len(matches) == 0:
        return None, None

    storm_id = matches['storm_id'].iloc[0]
    track = matches.sort_values('date').reset_index(drop=True)

    return storm_id, track


def process_all_hurricanes():
    """Process all hurricanes in the list"""

    print("=" * 80)
    print("BATCH HURRICANE ENVELOPE GENERATION")
    print("=" * 80)

    # Load HURDAT2 data once
    print("\n1. Loading HURDAT2 data...")
    hurdat_file = Path(__file__).parent.parent / "input_data" / "hurdat2-atlantic.txt"
    df_raw = parse_hurdat2_file(hurdat_file)
    df_clean = clean_hurdat2_data(df_raw)
    print(f"   ✅ Loaded {len(df_clean):,} records from {df_clean['storm_id'].nunique():,} storms")

    # Output directory
    output_dir = Path(__file__).parent.parent / "outputs" / "batch_envelopes"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each hurricane
    results = []

    print(f"\n2. Processing {len(HURRICANES)} hurricanes...")
    print("-" * 80)

    for idx, hurricane in enumerate(HURRICANES, 1):
        name = hurricane['name']
        year = hurricane['year']

        print(f"\n[{idx}/{len(HURRICANES)}] Processing {name} ({year})...")

        # Find storm in data
        storm_id, track = find_storm_in_data(df_clean, name, year)

        if track is None:
            print(f"   ❌ Storm not found: {name} ({year})")
            results.append({
                'name': name,
                'year': year,
                'storm_id': None,
                'status': 'NOT FOUND',
                'envelope_area': None,
                'track_points': 0
            })
            continue

        print(f"   Storm ID: {storm_id}")
        print(f"   Track points: {len(track)}")
        print(f"   Date range: {track['date'].min()} to {track['date'].max()}")
        print(f"   Max wind: {track['max_wind'].max()} kt")

        # Create envelopes for all three wind thresholds
        try:
            envelope_34kt, track_line, _ = create_storm_envelope(track, wind_threshold='34kt', verbose=False)
            envelope_50kt, _, _ = create_storm_envelope(track, wind_threshold='50kt', verbose=False)
            envelope_64kt, _, _ = create_storm_envelope(track, wind_threshold='64kt', verbose=False)

            if envelope_34kt is None:
                print(f"   ❌ Failed to create envelope")
                results.append({
                    'name': name,
                    'year': year,
                    'storm_id': storm_id,
                    'status': 'ENVELOPE FAILED',
                    'envelope_34kt_area': None,
                    'track_points': len(track)
                })
                continue

            print(f"   ✅ Envelopes created:")
            print(f"      34kt: {envelope_34kt.area:.2f} sq°")
            if envelope_50kt:
                print(f"      50kt: {envelope_50kt.area:.2f} sq°")
            if envelope_64kt:
                print(f"      64kt: {envelope_64kt.area:.2f} sq°")

            # Create visualization with all three envelopes
            output_file = output_dir / f"{name.lower()}_{year}_envelope.png"
            title = f"Hurricane {name.title()} {year}: Wind Field Envelopes"

            create_map_visualization(
                envelope_34kt, envelope_50kt, envelope_64kt,
                track_line, track,
                output_path=output_file,
                title=title,
                focus_gulf_coast=True
            )

            print(f"   ✅ Visualization saved: {output_file.name}")

            # Store results
            results.append({
                'name': name,
                'year': year,
                'storm_id': storm_id,
                'status': 'SUCCESS',
                'envelope_34kt_area': envelope_34kt.area,
                'envelope_50kt_area': envelope_50kt.area if envelope_50kt else None,
                'envelope_64kt_area': envelope_64kt.area if envelope_64kt else None,
                'track_points': len(track),
                'max_wind': track['max_wind'].max(),
                'envelope_valid': envelope_34kt.is_valid,
                'output_file': str(output_file)
            })

        except Exception as e:
            print(f"   ❌ Error processing {name}: {e}")
            results.append({
                'name': name,
                'year': year,
                'storm_id': storm_id,
                'status': f'ERROR: {str(e)[:50]}',
                'envelope_area': None,
                'track_points': len(track)
            })

    # Save summary
    print("\n" + "=" * 80)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 80)

    results_df = pd.DataFrame(results)
    summary_file = output_dir / "batch_processing_summary.csv"
    results_df.to_csv(summary_file, index=False)

    print(f"\n✅ Summary saved to: {summary_file}")
    print(f"\n📊 Results Summary:")
    print(results_df[['name', 'year', 'status', 'envelope_34kt_area', 'envelope_50kt_area', 'envelope_64kt_area']].to_string(index=False))

    # Count successes
    success_count = len(results_df[results_df['status'] == 'SUCCESS'])
    print(f"\n✅ Successfully processed: {success_count}/{len(HURRICANES)} hurricanes")
    print(f"📁 Output directory: {output_dir}")

    return results_df


if __name__ == "__main__":
    results = process_all_hurricanes()
