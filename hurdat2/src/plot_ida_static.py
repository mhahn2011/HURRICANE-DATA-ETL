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
        str(REPO_ROOT / "hurdat2" / "src"),
    ]
)

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope

def main():
    """
    Creates a static Matplotlib visualization of Hurricane Ida's impact.
    """
    print("--- Task 2: Creating Static Matplotlib Visualization ---")

    # 1. Load the enriched data
    print("Loading visualization data...")
    vis_data_path = REPO_ROOT / "integration" / "outputs" / "ida_visualization_data.csv"
    if not vis_data_path.exists():
        print(f"❌ ERROR: {vis_data_path} not found. Please run the data preparation script first.")
        return
    vis_data = pd.read_csv(vis_data_path)
    print(f"Loaded {len(vis_data)} tract records.")

    # 2. Load Hurricane Ida track and envelope
    print("Loading Hurricane Ida track and envelope...")
    hurdat_path = REPO_ROOT / "hurdat2" / "input_data" / "hurdat2-atlantic.txt"
    storms = parse_hurdat2_file(hurdat_path)
    cleaned = clean_hurdat2_data(storms)
    ida_track_df = cleaned[
        (cleaned['storm_id'] == 'AL092021') &
        (cleaned['storm_name'] == 'IDA')
    ].copy()
    
    envelope_geom, track_line, _ = create_storm_envelope(
        ida_track_df,
        wind_threshold='64kt',
        alpha=0.6,
        verbose=False
    )
    print("Generated envelope and track LineString.")

    # 3. Create the plot
    print("Creating plot...")
    fig, ax = plt.subplots(1, 1, figsize=(15, 10))

    # Plot Gulf Coast outline
    try:
        countries_url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
        countries = gpd.read_file(countries_url)
        xlim = (-100, -75)
        ylim = (24, 37)
        countries_view = countries.cx[xlim[0]:xlim[1], ylim[0]:ylim[1]]
        countries_view.plot(ax=ax, facecolor='lightgray', edgecolor='black', linewidth=0.8, alpha=0.3, zorder=0)
        
        states_url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_1_states_provinces.zip"
        states = gpd.read_file(states_url)
        us_states = states[states['admin'] == 'United States of America']
        us_states_view = us_states.cx[xlim[0]:xlim[1], ylim[0]:ylim[1]]
        us_states_view.plot(ax=ax, facecolor='none', edgecolor='darkgray', linewidth=1, linestyle='--', alpha=0.6, zorder=0.5)
        print("Loaded basemap.")
    except Exception as e:
        print(f"⚠️ Could not load basemap: {e}")

    # Plot envelope
    if envelope_geom:
        gpd.GeoSeries([envelope_geom]).plot(ax=ax, facecolor='blue', alpha=0.3, zorder=1)

    # Plot track
    if track_line:
        gpd.GeoSeries([track_line]).plot(ax=ax, color='red', linewidth=2, zorder=2)

    # Plot tract centroids
    scatter = ax.scatter(
        vis_data['centroid_lon'],
        vis_data['centroid_lat'],
        c=vis_data['distance_to_track_km'],
        cmap='viridis_r', # Reversed viridis: green is close, yellow is far
        s=10,
        zorder=3
    )
    plt.colorbar(scatter, ax=ax, label='Distance to Track (km)')
    
    ax.set_title("Hurricane Ida Envelope and Affected Tract Centroids")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_xlim(-95, -85)
    ax.set_ylim(28, 32)
    ax.grid(True)

    # 4. Save the plot
    output_path = REPO_ROOT / "integration" / "outputs" / "ida_static_map.png"
    plt.savefig(output_path, dpi=300)
    print(f"✅ Static map saved to {output_path}")
    print("--- Task 2 Complete ---")

if __name__ == "__main__":
    main()
