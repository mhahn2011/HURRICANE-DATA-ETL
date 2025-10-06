import sys
from pathlib import Path
import pandas as pd
from shapely.geometry import Point, LineString

# Add project src path to allow importing modules
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend(
    [
        str(REPO_ROOT / "census" / "src"),
        str(REPO_ROOT / "hurdat2" / "src"),
    ]
)

from tract_centroids import load_tracts_with_centroids
from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data

def main():
    """
    Prepares the data needed for visualizing Hurricane Ida's impact on census tracts.
    """
    print("--- Task 1: Preparing Hurricane Ida Visualization Data ---")

    # 1. Load affected tract pairs
    print("Loading affected tract pairs...")
    tract_pairs_path = REPO_ROOT / "hurdat2" / "outputs" / "ida_tract_pairs.csv"
    if not tract_pairs_path.exists():
        print(f"❌ ERROR: {tract_pairs_path} not found. Please run the spatial join script first.")
        return
    tract_pairs = pd.read_csv(tract_pairs_path)
    tract_pairs['tract_geoid'] = tract_pairs['tract_geoid'].astype(str)
    affected_geoids = tract_pairs['tract_geoid'].tolist()
    print(f"Loaded {len(affected_geoids)} affected tract GEOIDs.")

    # 2. Load census tract centroids
    print("Loading census tract centroids...")
    tract_data = load_tracts_with_centroids(
        year=2019,
        states=['22', '28', '48', '01', '12'], # LA, MS, TX, AL, FL
        columns=['GEOID', 'STATEFP', 'COUNTYFP', 'NAME']
    )
    tract_data.centroids['GEOID'] = tract_data.centroids['GEOID'].astype(str)
    affected_centroids = tract_data.centroids[
        tract_data.centroids['GEOID'].isin(affected_geoids)
    ].copy()
    print(f"Data type of GEOID in centroids: {tract_data.centroids['GEOID'].dtype}")
    print(f"Filtered to {len(affected_centroids)} affected tract centroids.")

    # 3. Load Hurricane Ida track data
    print("Loading Hurricane Ida track data...")
    hurdat_path = REPO_ROOT / "hurdat2" / "input_data" / "hurdat2-atlantic.txt"
    storms = parse_hurdat2_file(hurdat_path)
    cleaned = clean_hurdat2_data(storms)
    ida_track = cleaned[
        (cleaned['storm_id'] == 'AL092021') &
        (cleaned['storm_name'] == 'IDA')
    ].copy()
    print(f"Loaded {len(ida_track)} track points for Hurricane Ida.")

    # 4. Calculate distances
    print("Calculating distances from centroids to track...")
    track_coords = list(zip(ida_track['lon'], ida_track['lat']))
    track_line = LineString(track_coords)

    distances_km = []
    for idx, row in affected_centroids.iterrows():
        centroid_point = Point(row.geometry.x, row.geometry.y)
        distance_deg = centroid_point.distance(track_line)
        distance_km = distance_deg * 111.0  # Approximate conversion
        distances_km.append(distance_km)
    
    affected_centroids['distance_to_track_km'] = distances_km
    print("Distance calculation complete.")

    # 5. Create enriched CSV
    print("Creating enriched visualization dataset...")
    affected_centroids['centroid_lon'] = affected_centroids.geometry.x
    affected_centroids['centroid_lat'] = affected_centroids.geometry.y

    affected_centroids.rename(columns={'GEOID': 'tract_geoid'}, inplace=True)
    
    vis_data = pd.merge(tract_pairs, affected_centroids, on='tract_geoid')

    output_columns = [
        'storm_id',
        'storm_name',
        'year',
        'tract_geoid',
        'centroid_lat',
        'centroid_lon',
        'distance_to_track_km',
        'STATEFP',
        'COUNTYFP'
    ]
    final_columns = [col for col in output_columns if col in vis_data.columns]
    final_data = vis_data[final_columns]

    # 6. Output enriched CSV
    output_path = REPO_ROOT / "integration" / "outputs" / "ida_visualization_data.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_data.to_csv(output_path, index=False)
    print(f"✅ Enriched data saved to {output_path}")
    print("--- Task 1 Complete ---")

if __name__ == "__main__":
    main()
