"""
Test runner for envelope algorithm
Generates envelope and validates track containment
"""
import sys
from pathlib import Path
import pandas as pd
from shapely.geometry import Point

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope


def test_hurricane_ida():
    """Test envelope creation for Hurricane Ida 2021"""

    print("=" * 60)
    print("HURRICANE IDA 2021: ENVELOPE GENERATION & VALIDATION")
    print("=" * 60)

    # Load data
    print("\n1. Loading HURDAT2 data...")
    hurdat_file = Path(__file__).parent.parent / "input_data" / "hurdat2-atlantic.txt"
    df_raw = parse_hurdat2_file(hurdat_file)
    df_clean = clean_hurdat2_data(df_raw)
    print(f"   ✅ Loaded {len(df_clean):,} records from {df_clean['storm_id'].nunique():,} storms")

    # Select Hurricane Ida
    print("\n2. Selecting Hurricane Ida (2021)...")
    ida_track = df_clean[
        df_clean['storm_name'].str.contains('IDA', na=False) &
        (df_clean['year'] == 2021)
    ].sort_values('date').reset_index(drop=True)

    print(f"   ✅ Found {len(ida_track)} track points")
    print(f"   Date range: {ida_track['date'].min()} to {ida_track['date'].max()}")
    print(f"   Max wind: {ida_track['max_wind'].max()} kt")

    # Check wind radii availability
    print("\n3. Checking wind radii data availability...")
    for threshold in ['34', '50', '64']:
        counts = sum([
            ida_track[f'wind_radii_{threshold}_{dir}'].notna().sum()
            for dir in ['ne', 'se', 'sw', 'nw']
        ])
        print(f"   {threshold}kt radii: {counts} total data points")

    # Create envelope
    print("\n4. Creating storm envelope (using 34kt radii priority)...")
    envelope, track_line, diagnostics = create_storm_envelope(ida_track, verbose=True)

    if envelope is None:
        print("   ❌ Failed to create envelope")
        return False

    print(f"\n   ✅ Envelope created successfully")
    print(f"   Area: {envelope.area:.2f} sq degrees")
    print(f"   Track length: {track_line.length:.2f} degrees")
    print(f"   Valid: {envelope.is_valid}")
    print(f"   Type: {type(envelope).__name__}")

    # Test track containment
    print("\n5. CRITICAL TEST: Verifying track containment...")
    points_outside = []

    for idx, row in ida_track.iterrows():
        point = Point(row['lon'], row['lat'])
        if not envelope.contains(point):
            points_outside.append({
                'index': idx,
                'date': row['date'],
                'lat': row['lat'],
                'lon': row['lon'],
                'wind_speed': row['max_wind'],
                'distance_to_envelope': point.distance(envelope)
            })

    if len(points_outside) == 0:
        print(f"   ✅ SUCCESS: All {len(ida_track)} track points are inside envelope!")
        return True
    else:
        print(f"   ❌ FAILURE: {len(points_outside)} points are OUTSIDE envelope")
        print("\n   Points outside envelope:")
        for pt in points_outside[:10]:  # Show first 10
            print(f"     Point {pt['index']}: {pt['date']} - {pt['lat']:.1f}°N, {pt['lon']:.1f}°W")
            print(f"       Wind: {pt['wind_speed']}kt, Distance to envelope: {pt['distance_to_envelope']:.4f}°")
        return False


if __name__ == "__main__":
    success = test_hurricane_ida()

    print("\n" + "=" * 60)
    if success:
        print("✅ ENVELOPE ALGORITHM VALIDATION: PASSED")
    else:
        print("❌ ENVELOPE ALGORITHM VALIDATION: FAILED")
    print("=" * 60)

    sys.exit(0 if success else 1)
