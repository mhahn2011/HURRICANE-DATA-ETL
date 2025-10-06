import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString

# Add project src path to allow importing modules
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend(
    [
        str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
    ]
)

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data

def main():
    """
    Creates a diagnostic plot to debug the distance calculation for a specific tract.
    """
    print("--- Debugging Distance Calculation ---")

    # 1. Define the problematic tract's data
    tract_geoid = '28005950300'
    centroid_lat = 31.074539288518274
    centroid_lon = -90.85272658761315
    calculated_dist_km = 47.567575819249846
    
    centroid_point = Point(centroid_lon, centroid_lat)
    print(f"Problematic Tract: {tract_geoid}")
    print(f"Centroid: ({centroid_lat}, {centroid_lon})")
    print(f"Calculated Distance (km): {calculated_dist_km}")

    # 2. Load Hurricane Ida track data
    print("Loading Hurricane Ida track data...")
    hurdat_path = REPO_ROOT / "hurdat2" / "input_data" / "hurdat2-atlantic.txt"
    storms = parse_hurdat2_file(hurdat_path)
    cleaned = clean_hurdat2_data(storms)
    ida_track_df = cleaned[
        (cleaned['storm_id'] == 'AL092021') &
        (cleaned['storm_name'] == 'IDA')
    ].copy()
    print(f"Loaded {len(ida_track_df)} track points for Hurricane Ida.")

    # 3. Create track LineString
    track_coords = list(zip(ida_track_df['lon'], ida_track_df['lat']))
    track_line = LineString(track_coords)

    # 4. Recalculate distance for verification
    distance_deg = centroid_point.distance(track_line)
    recalculated_dist_km = distance_deg * 111.0 
    print(f"Recalculated Distance (km): {recalculated_dist_km}")

    # 5. Create the plot
    print("Creating diagnostic plot...")
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))

    # Plot track
    gpd.GeoSeries([track_line]).plot(ax=ax, color='red', linewidth=2, label='Ida Track')

    # Plot centroid
    gpd.GeoSeries([centroid_point]).plot(ax=ax, color='blue', markersize=50, label=f'Tract {tract_geoid}')

    # Plot circle for calculated distance
    radius_deg = calculated_dist_km / 111.0
    circle = centroid_point.buffer(radius_deg)
    gpd.GeoSeries([circle]).plot(ax=ax, facecolor='none', edgecolor='green', linestyle='--', label=f'Calculated Distance ({calculated_dist_km:.1f} km)')

    # Plot circle for 10km distance
    radius_10km_deg = 10 / 111.0
    circle_10km = centroid_point.buffer(radius_10km_deg)
    gpd.GeoSeries([circle_10km]).plot(ax=ax, facecolor='none', edgecolor='purple', linestyle=':', label='10 km Reference')


    ax.set_title(f"Distance Calculation Debug for Tract {tract_geoid}")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend()
    ax.grid(True)
    
    ax.set_xlim(centroid_lon - 1, centroid_lon + 1)
    ax.set_ylim(centroid_lat - 1, centroid_lat + 1)

    output_path = REPO_ROOT / "06_outputs" / "visuals" / "debug" / "debug_distance_plot.png"
    plt.savefig(output_path, dpi=300)
    print(f"✅ Diagnostic plot saved to {output_path}")

if __name__ == "__main__":
    main()
