"""
Spatial join to identify census tracts within storm envelopes.

This module:
1. Loads storm envelope polygon
2. Loads census tract centroids
3. Performs spatial join to identify tracts within envelope
4. Outputs storm-tract pairs table
"""

import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Add census module to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "census" / "src"))
from tract_centroids import load_tracts_with_centroids

# Import HURDAT2 parsing
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope


def identify_tracts_in_envelope(envelope_geom, tract_centroids_gdf):
    """
    Identify which census tract centroids fall within the storm envelope.

    Args:
        envelope_geom: Shapely Polygon or MultiPolygon
        tract_centroids_gdf: GeoDataFrame with tract centroid points

    Returns:
        GeoDataFrame of tracts within envelope
    """
    if envelope_geom is None or envelope_geom.is_empty:
        return gpd.GeoDataFrame()

    # Perform spatial filter - keep only centroids within envelope
    tracts_in_envelope = tract_centroids_gdf[tract_centroids_gdf.intersects(envelope_geom)].copy()

    return tracts_in_envelope


def create_storm_tract_pairs(storm_id, storm_name, year, tracts_in_envelope):
    """
    Create storm-tract pairs table.

    Args:
        storm_id: HURDAT2 storm identifier
        storm_name: Storm name
        year: Storm year
        tracts_in_envelope: GeoDataFrame of tracts within envelope

    Returns:
        DataFrame with columns: storm_id, storm_name, year, tract_id, tract_geoid
    """
    if tracts_in_envelope.empty:
        return pd.DataFrame(columns=['storm_id', 'storm_name', 'year', 'tract_geoid'])

    pairs = pd.DataFrame({
        'storm_id': storm_id,
        'storm_name': storm_name,
        'year': year,
        'tract_geoid': tracts_in_envelope['GEOID'].values
    })

    return pairs


def main():
    """Test with Hurricane Ida"""

    print("=" * 60)
    print("STORM-TRACT SPATIAL JOIN: Hurricane Ida 2021")
    print("=" * 60)

    # 1. Load and process Hurricane Ida
    print("\n1. Loading Hurricane Ida data...")
    hurdat_path = Path(__file__).resolve().parents[1] / "input_data" / "hurdat2-atlantic.txt"

    storms_df = parse_hurdat2_file(str(hurdat_path))
    cleaned_df = clean_hurdat2_data(storms_df)

    ida_track = cleaned_df[
        (cleaned_df['storm_id'] == 'AL092021') &
        (cleaned_df['storm_name'] == 'IDA')
    ].copy()

    print(f"   ✅ Loaded {len(ida_track)} track points")
    print(f"   Date range: {ida_track['date'].min()} to {ida_track['date'].max()}")

    # 2. Create envelope
    print("\n2. Creating storm envelope (alpha=0.6)...")
    envelope_geom, track_line, hull_points = create_storm_envelope(
        ida_track,
        wind_threshold='64kt',
        alpha=0.6,
        verbose=True
    )

    if envelope_geom is None:
        print("   ❌ Failed to create envelope")
        return

    print(f"   ✅ Envelope created")
    print(f"   Type: {envelope_geom.geom_type}")
    print(f"   Area: {envelope_geom.area:.2f} sq degrees")

    # 3. Load Gulf Coast census tracts
    print("\n3. Loading Gulf Coast census tracts...")
    gulf_coast_states = ['22', '28', '48', '01', '12']  # LA, MS, TX, AL, FL

    tract_data = load_tracts_with_centroids(
        year=2019,
        states=gulf_coast_states,
        columns=['GEOID', 'STATEFP', 'COUNTYFP', 'TRACTCE', 'NAME']
    )

    print(f"   ✅ Loaded {len(tract_data.centroids):,} census tracts")

    # 4. Spatial join - find tracts within envelope
    print("\n4. Performing spatial join...")
    tracts_in_envelope = identify_tracts_in_envelope(
        envelope_geom,
        tract_data.centroids
    )

    print(f"   ✅ Found {len(tracts_in_envelope):,} tracts within envelope")

    if len(tracts_in_envelope) > 0:
        print(f"\n   Sample tracts affected:")
        for i, row in tracts_in_envelope.head(10).iterrows():
            print(f"      {row['GEOID']} - State: {row['STATEFP']}, County: {row['COUNTYFP']}")

    # 5. Create storm-tract pairs table
    print("\n5. Creating storm-tract pairs table...")
    pairs_df = create_storm_tract_pairs(
        storm_id='AL092021',
        storm_name='IDA',
        year=2021,
        tracts_in_envelope=tracts_in_envelope
    )

    print(f"   ✅ Created {len(pairs_df):,} storm-tract pairs")

    # 6. Save output
    output_dir = Path(__file__).resolve().parents[1] / "outputs"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "ida_tract_pairs.csv"

    pairs_df.to_csv(output_path, index=False)
    print(f"\n   ✅ Saved to: {output_path}")

    # Summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Storm: {pairs_df['storm_name'].iloc[0] if len(pairs_df) > 0 else 'N/A'} ({pairs_df['year'].iloc[0] if len(pairs_df) > 0 else 'N/A'})")
    print(f"Total census tracts affected: {len(pairs_df):,}")
    print(f"Envelope area: {envelope_geom.area:.2f} sq degrees")
    print(f"Track length: {track_line.length:.2f} degrees")

    if len(tracts_in_envelope) > 0:
        states_affected = tracts_in_envelope['STATEFP'].value_counts()
        print(f"\nTracts by state:")
        state_names = {'22': 'Louisiana', '28': 'Mississippi', '48': 'Texas',
                      '01': 'Alabama', '12': 'Florida'}
        for state_fp, count in states_affected.items():
            state_name = state_names.get(state_fp, f"State {state_fp}")
            print(f"   {state_name}: {count:,} tracts")

    print("\n✅ Spatial join complete!")


if __name__ == "__main__":
    main()
