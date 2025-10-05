"""Orchestrates all feature extraction for a single storm."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(REPO_ROOT / "hurdat2" / "src"),
    str(REPO_ROOT / "census" / "src"),
    str(REPO_ROOT / "integration" / "src"),
])

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope
from tract_centroids import load_tracts_with_centroids
from storm_tract_distance import compute_min_distance_features
from wind_interpolation import calculate_max_wind_experienced
from duration_calculator import calculate_duration_for_tract
from intensification_features import calculate_intensification_features, calculate_lead_time


def extract_all_features_for_storm(
    storm_id: str,
    hurdat_data_path: str = "hurdat2/input_data/hurdat2-atlantic.txt",
    census_year: int = 2019,
    gulf_states: list = ['22', '28', '48', '01', '12'],
    alpha: float = 0.6,
    wind_threshold: str = '64kt'
) -> pd.DataFrame:
    """
    Extract all features for one storm.

    Steps:
    1. Load and clean HURDAT2 data
    2. Filter to specific storm
    3. Create envelope (alpha=0.6, 64kt threshold)
    4. Load Gulf Coast census tract centroids
    5. Spatial join: Find tracts within envelope
    6. For each tract in envelope:
        a. Calculate distance features
        b. Calculate wind features
        c. Calculate duration features
    7. Calculate storm-level intensification features
    8. Merge all features into single DataFrame

    Returns:
        DataFrame with all features (one row per tract in envelope)
    """
    # 1. Load data
    df_raw = parse_hurdat2_file(hurdat_data_path)
    df_clean = clean_hurdat2_data(df_raw)
    track_df = df_clean[df_clean['storm_id'] == storm_id].sort_values('date').reset_index(drop=True)
    if track_df.empty:
        raise ValueError(f"Storm {storm_id} not found in cleaned dataset")

    centroids_gdf = load_tracts_with_centroids(year=census_year, states=gulf_states)

    # 2. Create envelope
    envelope, track_line, _ = create_storm_envelope(track_df, wind_threshold, alpha)

    # 3. Spatial join
    tracts_in_envelope = centroids_gdf[centroids_gdf.intersects(envelope)]

    # 4. Calculate storm-level features (same for all tracts)
    intensification_features = calculate_intensification_features(track_df)

    # 5. Calculate tract-level features
    results = []
    for idx, tract_row in tracts_in_envelope.iterrows():
        centroid = tract_row.geometry

        # Distance features
        dist_features = compute_min_distance_features(pd.DataFrame([tract_row]), track_df).iloc[0]

        # Wind features
        wind_features = calculate_max_wind_experienced(
            centroid, track_line, track_df, envelope
        )

        # Duration features
        duration_features = calculate_duration_for_tract(
            centroid, track_df, wind_threshold
        )

        # Lead time (tract-specific)
        lead_time = calculate_lead_time(
            intensification_features['cat4_first_time'],
            dist_features['storm_time']
        )

        # Merge all features
        row = {
            'tract_geoid': tract_row.GEOID,
            'tract_state_fp': tract_row.STATEFP,
            'tract_county_fp': tract_row.COUNTYFP,
            **dist_features.to_dict(),
            **wind_features,
            **duration_features,
            **intensification_features,
            'lead_time_to_max_wind_hours': lead_time
        }
        results.append(row)

    return pd.DataFrame(results)