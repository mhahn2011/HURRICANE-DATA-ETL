"""Manual sanity check for Hurricane Ida wind interpolation."""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend(
    [
        str(REPO_ROOT / "hurdat2" / "src"),
        str(REPO_ROOT / "census" / "src"),
        str(REPO_ROOT / "integration" / "src"),
    ]
)

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope
from tract_centroids import load_tracts_with_centroids
from wind_interpolation import calculate_max_wind_experienced


def load_specific_tract(geoid: str) -> gpd.GeoSeries:
    centroids = load_tracts_with_centroids(states=["22"]).centroids
    result = centroids[centroids["GEOID"] == geoid]
    if result.empty:
        raise ValueError(f"Tract {geoid} not found in Louisiana centroids")
    return result.iloc[0]


def main() -> None:
    df = clean_hurdat2_data(parse_hurdat2_file(str(REPO_ROOT / "hurdat2" / "input_data" / "hurdat2-atlantic.txt")))
    ida_track = df[df["storm_id"] == "AL092021"].sort_values("date")

    envelope, track_line, _ = create_storm_envelope(ida_track, wind_threshold="64kt", alpha=0.6)

    test_tract = load_specific_tract("22071001747")

    wind_features = calculate_max_wind_experienced(
        centroid=test_tract.geometry,
        track_line=track_line,
        track_df=ida_track,
        envelope=envelope,
    )

    print("Max wind experienced:", f"{wind_features['max_wind_experienced_kt']:.1f} kt")
    print("Center wind at approach:", f"{wind_features['center_wind_at_approach_kt']:.1f} kt")
    print("Distance to envelope edge:", f"{wind_features['distance_to_envelope_edge_nm']:.1f} nm")


if __name__ == "__main__":
    main()
