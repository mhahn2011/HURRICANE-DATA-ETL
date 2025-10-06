"""
Pre-computes and saves all data required for the multi-storm dashboard.

This script iterates through the target hurricanes, loads their feature data,
computes their storm track and wind coverage envelopes, and saves the combined
data into a series of dashboard-ready GeoJSON files.
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

# --- Add project paths to sys.path ---
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
    str(REPO_ROOT / "02_transformations" / "storm_tract_distance" / "src"),
])

# --- Import project-specific modules ---
from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from storm_tract_distance import create_wind_coverage_envelope

# --- Define constants for file paths ---
HURDAT_PATH = REPO_ROOT / "01_data_sources" / "hurdat2" / "input_data" / "hurdat2-atlantic.txt"
TARGET_HURRICANES_PATH = REPO_ROOT / "00_config" / "target_hurricanes.json"
FEATURES_DIR = REPO_ROOT / "06_outputs" / "ml_ready"
OUTPUT_DIR = REPO_ROOT / "07_dashboard_app" / "data"


def main():
    """Main function to run the pre-computation pipeline."""
    print("--- Starting Dashboard Pre-computation Script ---")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Output directory is: {OUTPUT_DIR}")

    # --- Load shared data once ---
    print(f"Loading and cleaning HURDAT data from {HURDAT_PATH}...")
    hurdat_raw = parse_hurdat2_file(str(HURDAT_PATH))
    hurdat_clean = clean_hurdat2_data(hurdat_raw)
    print("HURDAT data loaded and cleaned.")

    with open(TARGET_HURRICANES_PATH) as f:
        target_hurricanes = json.load(f)["target_hurricanes"]
    print(f"Loaded {len(target_hurricanes)} target hurricanes.")

    # --- Main processing loop for each storm ---
    for storm_info in target_hurricanes:
        storm_id = storm_info["storm_id"]
        storm_name = storm_info["name"]
        print(f"\n--- Processing: {storm_name} ({storm_id}) ---")

        # 1. Get storm track from the cleaned HURDAT data
        track_df = hurdat_clean[hurdat_clean["storm_id"] == storm_id].sort_values("date").reset_index(drop=True)
        if track_df.empty:
            print(f"  [!] WARNING: No track data found for {storm_id}. Skipping.")
            continue
        print(f"  - Found {len(track_df)} track points.")

        # 2. Compute the wind coverage envelope and track line
        try:
            coverage, track_line, _ = create_wind_coverage_envelope(track_df, wind_threshold="64kt")
            if coverage is None or coverage.is_empty:
                print(f"  [!] WARNING: Could not generate wind envelope for {storm_id}. Skipping.")
                continue
            print("  - Successfully generated wind envelope and track line.")
        except Exception as e:
            print(f"  [!] ERROR: Failed to create envelope for {storm_id}: {e}. Skipping.")
            continue

        # 3. Load the corresponding tract-level feature data
        # Note: File names are inconsistent, so we search for a file starting with the storm ID.
        feature_files = list(FEATURES_DIR.glob(f"{storm_id.lower()}*.csv"))
        if not feature_files:
            # Try another common pattern if the first fails
            feature_files = list(FEATURES_DIR.glob(f"*{storm_name.lower()}*.csv"))

        if not feature_files:
            print(f"  [!] WARNING: No feature CSV found for {storm_id}. Skipping.")
            continue

        feature_path = feature_files[0]
        print(f"  - Loading features from: {feature_path.name}")
        features_df = pd.read_csv(feature_path)

        # 4. Convert feature DataFrame to a GeoDataFrame of tract centroids
        tract_gdf = gpd.GeoDataFrame(
            features_df,
            geometry=gpd.points_from_xy(features_df.centroid_lon, features_df.centroid_lat),
            crs="EPSG:4326"
        )
        tract_gdf["type"] = "tract"
        print(f"  - Converted {len(tract_gdf)} tracts to GeoDataFrame.")

        # 5. Create GeoDataFrames for the envelope and track
        envelope_gdf = gpd.GeoDataFrame([{"type": "envelope", "storm_id": storm_id}], geometry=[coverage], crs="EPSG:4326")
        track_gdf = gpd.GeoDataFrame([{"type": "track", "storm_id": storm_id}], geometry=[track_line], crs="EPSG:4326")

        # 6. Combine all geometries into a single GeoDataFrame
        # Use pd.concat as gpd.concat is deprecated
        combined_gdf = gpd.GeoDataFrame(pd.concat([envelope_gdf, track_gdf, tract_gdf], ignore_index=True), crs="EPSG:4326")
        print("  - Combined envelope, track, and tracts into a single GeoDataFrame.")

        # 7. Save the final output to a GeoJSON file
        output_path = OUTPUT_DIR / f"{storm_id}.geojson"
        try:
            # Note: GeoPandas handles NaN/NaT values when writing to GeoJSON
            combined_gdf.to_file(output_path, driver="GeoJSON")
            print(f"  -> Successfully saved output to {output_path}")
        except Exception as e:
            print(f"  [!] ERROR: Failed to write GeoJSON file for {storm_id}: {e}")

    print("\n--- Dashboard Pre-computation Complete ---")


if __name__ == "__main__":
    main()