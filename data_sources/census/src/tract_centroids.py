"""Utilities for loading US census tracts and computing tract centroids.

The module keeps I/O concerns isolated so other pipelines can import the
functions without pulling notebook dependencies.  It expects TIGER/Line
shapefiles that match the repository layout (see `census/input_data`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

import geopandas as gpd
import pandas as pd


DEFAULT_YEAR = 2019
INPUT_ROOT = Path(__file__).resolve().parents[1] / "input_data"
ZIP_TEMPLATE = "tl_{year}_us_tract.zip"
SHP_TEMPLATE = "tl_{year}_us_tract.shp"
STATE_ZIP_TEMPLATE = "tl_{year}_{state}_tract.zip"
STATE_SHP_TEMPLATE = "tl_{year}_{state}_tract.shp"


@dataclass(frozen=True)
class TractData:
    """Simple container bundling tract polygons and their centroids."""

    tracts: gpd.GeoDataFrame
    centroids: gpd.GeoDataFrame


def load_census_tracts(
    year: int = DEFAULT_YEAR,
    bounds: Optional[Tuple[float, float, float, float]] = None,
    columns: Optional[Iterable[str]] = None,
    states: Optional[Sequence[str]] = None,
) -> gpd.GeoDataFrame:
    """Load census tracts for the given year, optionally filtering by bounds.

    Args:
        year: TIGER/Line vintage to load.
        bounds: (minx, miny, maxx, maxy) in WGS84 degrees to pre-filter.
        columns: Subset of columns to retain; geometry is always included.

    Returns:
        GeoDataFrame in EPSG:4326 with polygon geometries.

    Raises:
        FileNotFoundError: if the expected TIGER/Line archive is missing.
    """

    import zipfile

    def _read_zip(zip_path: Path, shp_name: str) -> gpd.GeoDataFrame:
        if not zipfile.is_zipfile(zip_path):
            raise ValueError(
                f"{zip_path} is not a valid ZIP archive. Re-download the TIGER/Line tract file."
            )
        data_uri = f"zip://{zip_path}!{shp_name}"
        return gpd.read_file(data_uri)

    if states:
        frames = []
        for state in states:
            state = state.strip()
            zip_path = INPUT_ROOT / STATE_ZIP_TEMPLATE.format(year=year, state=state)
            if not zip_path.exists():
                raise FileNotFoundError(
                    f"State tract archive not found: {zip_path}. Download TIGER/Line data for state {state}."
                )
            shp_name = STATE_SHP_TEMPLATE.format(year=year, state=state)
            frames.append(_read_zip(zip_path, shp_name))

        if not frames:
            return gpd.GeoDataFrame(columns=["geometry"], crs="EPSG:4326")

        tracts = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)
    else:
        zip_path = INPUT_ROOT / ZIP_TEMPLATE.format(year=year)
        if not zip_path.exists():
            raise FileNotFoundError(
                f"Census tract archive not found: {zip_path}. Download TIGER/Line data first or specify states=..."
            )

        shp_name = SHP_TEMPLATE.format(year=year)
        tracts = _read_zip(zip_path, shp_name)

    # Ensure coordinates align with hurricane data (EPSG:4326)
    if tracts.crs is not None and tracts.crs.to_string().upper() != "EPSG:4326":
        tracts = tracts.to_crs("EPSG:4326")

    if bounds is not None:
        minx, miny, maxx, maxy = bounds
        tracts = tracts.cx[minx:maxx, miny:maxy]

    if columns is not None:
        columns = list(columns)
        if "geometry" not in columns:
            columns.append("geometry")
        existing = [col for col in columns if col in tracts.columns or col == "geometry"]
        tracts = tracts[existing]

    return tracts


def compute_tract_centroids(tracts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Return point centroids for each census tract polygon."""

    if tracts.empty:
        return tracts.copy()

    # Compute centroids in an equal-area projection to avoid distortions
    projected = tracts.to_crs("EPSG:5070")  # NAD83 / Conus Albers
    centroid_geom = projected.geometry.centroid
    centroids = gpd.GeoDataFrame(tracts.drop(columns="geometry"), geometry=centroid_geom, crs="EPSG:5070")
    return centroids.to_crs("EPSG:4326")


def load_tracts_with_centroids(
    year: int = DEFAULT_YEAR,
    bounds: Optional[Tuple[float, float, float, float]] = None,
    columns: Optional[Iterable[str]] = None,
    states: Optional[Sequence[str]] = None,
) -> TractData:
    """Convenience wrapper returning both polygons and centroid points."""

    tracts = load_census_tracts(year=year, bounds=bounds, columns=columns, states=states)
    centroids = compute_tract_centroids(tracts)
    return TractData(tracts=tracts, centroids=centroids)


def main() -> None:
    """CLI helper to preview tract counts and centroid sampling."""

    import argparse

    parser = argparse.ArgumentParser(description="Load census tracts and centroids")
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR, help="TIGER/Line vintage year")
    parser.add_argument(
        "--bounds",
        nargs=4,
        type=float,
        metavar=("MINX", "MINY", "MAXX", "MAXY"),
        help="Bounding box filter in longitude/latitude degrees",
    )
    parser.add_argument(
        "--head", type=int, default=5, help="Print the first N rows for inspection"
    )
    parser.add_argument(
        "--states",
        nargs="*",
        help="Optional list of state FIPS codes (e.g., 22 28 48) to load instead of full US",
    )

    args = parser.parse_args()

    tract_data = load_tracts_with_centroids(
        year=args.year,
        bounds=tuple(args.bounds) if args.bounds else None,
        states=args.states,
    )

    print(f"Loaded {len(tract_data.tracts):,} tracts for year {args.year}")
    if args.bounds:
        print(f"Bounds filter applied: {tuple(args.bounds)}")

    print("\nSample polygons:")
    print(tract_data.tracts.head(args.head)[["GEOID", "STATEFP", "COUNTYFP", "TRACTCE"]])

    print("\nSample centroids:")
    print(
        tract_data.centroids.head(args.head)[
            ["GEOID", "STATEFP", "COUNTYFP", "TRACTCE", "geometry"]
        ]
    )


if __name__ == "__main__":  # pragma: no cover - manual exploratory usage
    main()
