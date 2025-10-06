"""Orchestrates feature extraction for individual storms (dashboard helper)."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
import sys
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
    str(REPO_ROOT / "01_data_sources" / "census" / "src"),
    str(REPO_ROOT / "02_transformations" / "storm_tract_distance" / "src"),
    str(REPO_ROOT / "02_transformations" / "lead_time" / "src"),
    str(REPO_ROOT / "03_integration" / "src"),
])

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from intensification_features import calculate_intensification_features
from storm_tract_distance import run_pipeline as distance_run_pipeline

DEFAULT_GULF_STATES = ['22', '28', '48', '01', '12']  # LA, MS, TX, AL, FL


def _build_args(
    storm_id: str,
    hurdat_data_path: str,
    census_year: int,
    bounds_margin: float,
    states: Sequence[str] | None,
) -> SimpleNamespace:
    """Helper to build an argparse-like namespace for ``run_pipeline``."""

    return SimpleNamespace(
        storm_id=storm_id,
        hurdat_path=hurdat_data_path,
        census_year=census_year,
        bounds_margin=bounds_margin,
        states=list(states) if states else None,
        output=None,
    )


def extract_all_features_for_storm(
    storm_id: str,
    hurdat_data_path: str = "01_data_sources/hurdat2/raw/hurdat2-atlantic.txt",
    census_year: int = 2019,
    gulf_states: Iterable[str] | None = DEFAULT_GULF_STATES,
    bounds_margin: float = 3.0,
) -> pd.DataFrame:
    """Return tract-level features for a single hurricane storm.

    The function delegates to the modern pipeline implemented in
    ``02_transformations/storm_tract_distance/src/storm_tract_distance.py`` and attaches storm-level
    intensification metrics for downstream analytics.
    """

    args = _build_args(
        storm_id=storm_id,
        hurdat_data_path=hurdat_data_path,
        census_year=census_year,
        bounds_margin=bounds_margin,
        states=gulf_states,
    )

    features = distance_run_pipeline(args)
    if features.empty:
        return features

    # Append intensification features (constant per storm) for completeness.
    df_raw = parse_hurdat2_file(hurdat_data_path)
    df_clean = clean_hurdat2_data(df_raw)
    track_df = df_clean[df_clean['storm_id'] == storm_id].sort_values('date').reset_index(drop=True)
    if track_df.empty:
        raise ValueError(f"Storm {storm_id} not found in cleaned dataset")

    intensification = calculate_intensification_features(track_df)
    for key, value in intensification.items():
        features[key] = value

    return features


def save_features_for_storm(
    storm_id: str,
    output_path: Path,
    hurdat_data_path: str = "01_data_sources/hurdat2/raw/hurdat2-atlantic.txt",
    census_year: int = 2019,
    gulf_states: Iterable[str] | None = DEFAULT_GULF_STATES,
    bounds_margin: float = 3.0,
) -> Path:
    """Extract features and persist them to ``output_path`` in CSV format."""

    features = extract_all_features_for_storm(
        storm_id=storm_id,
        hurdat_data_path=hurdat_data_path,
        census_year=census_year,
        gulf_states=gulf_states,
        bounds_margin=bounds_margin,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(output_path, index=False)
    return output_path


def _parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract tract-level hurricane features")
    parser.add_argument("storm_id", help="Storm identifier, e.g., AL092021")
    parser.add_argument(
        "--hurdat-path",
        default="01_data_sources/hurdat2/raw/hurdat2-atlantic.txt",
        help="Path to the HURDAT2 source file",
    )
    parser.add_argument("--census-year", type=int, default=2019, help="TIGER/Line tract vintage")
    parser.add_argument(
        "--states",
        nargs="*",
        default=DEFAULT_GULF_STATES,
        help="Optional list of state FIPS codes to limit tract loading",
    )
    parser.add_argument(
        "--bounds-margin",
        type=float,
        default=3.0,
        help="Padding in degrees to expand the track bounding box",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Where to write the feature CSV (defaults to 06_outputs/ml_ready/{storm_id}_features.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_cli_args()
    default_output = REPO_ROOT / "06_outputs" / "ml_ready" / f"{args.storm_id.lower()}_features.csv"
    output_path = args.output or default_output

    saved_path = save_features_for_storm(
        storm_id=args.storm_id,
        output_path=output_path,
        hurdat_data_path=args.hurdat_path,
        census_year=args.census_year,
        gulf_states=args.states,
        bounds_margin=args.bounds_margin,
    )

    print(f"✅ Saved {args.storm_id} features to {saved_path}")


if __name__ == "__main__":
    main()
