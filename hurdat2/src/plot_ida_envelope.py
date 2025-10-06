"""Plot Hurricane Ida 64-kt envelope with impacted census tract centroids."""

from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / "integration" / "outputs" / ".mpl-cache"))
os.environ.setdefault("XDG_CACHE_HOME", str(REPO_ROOT / "integration" / "outputs" / ".xdg-cache"))

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

sys.path.extend(
    [
        str(REPO_ROOT / "hurdat2" / "src"),
        str(REPO_ROOT / "census" / "src"),
        str(REPO_ROOT / "integration" / "src"),
    ]
)

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from tract_centroids import load_tracts_with_centroids


NAUTICAL_MILE_TO_MILE = 1.15078


def calculate_destination_point(lat: float, lon: float, bearing: float, distance_nm: float) -> tuple[float, float]:
    """Return lon/lat of destination given starting point, bearing (deg), distance (nm)."""

    R_NM = 3440.065
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing)
    angular_distance = distance_nm / R_NM

    dest_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance)
        + math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
    )

    dest_lon_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(dest_lat_rad),
    )

    return (math.degrees(dest_lon_rad), math.degrees(dest_lat_rad))


def load_ida_track() -> pd.DataFrame:
    hurdat_path = REPO_ROOT / "hurdat2" / "input_data" / "hurdat2-atlantic.txt"
    df_raw = parse_hurdat2_file(str(hurdat_path))
    df_clean = clean_hurdat2_data(df_raw)
    ida_track = df_clean[df_clean["storm_id"] == "AL092021"].sort_values("date").reset_index(drop=True)
    if ida_track.empty:
        raise RuntimeError("Hurricane Ida (AL092021) not found in cleaned HURDAT2 data")
    return ida_track


def build_64kt_envelope(track: pd.DataFrame, bearing_step: float = 10.0):
    """Construct a 64-kt envelope by sampling wind radii around each track point."""

    points = []
    for row in track.itertuples():
        points.append(Point(row.lon, row.lat))

        radii = {
            "ne": getattr(row, "wind_radii_64_ne", np.nan),
            "se": getattr(row, "wind_radii_64_se", np.nan),
            "sw": getattr(row, "wind_radii_64_sw", np.nan),
            "nw": getattr(row, "wind_radii_64_nw", np.nan),
        }

        quadrant_ranges = {
            "ne": (0.0, 90.0),
            "se": (90.0, 180.0),
            "sw": (180.0, 270.0),
            "nw": (270.0, 360.0),
        }

        for quadrant, radius in radii.items():
            if not pd.notna(radius) or radius <= 0:
                continue

            start, end = quadrant_ranges[quadrant]
            bearings = np.arange(start, end + 0.1, bearing_step)
            for bearing in bearings:
                dest_lon, dest_lat = calculate_destination_point(row.lat, row.lon, bearing, radius)
                points.append(Point(dest_lon, dest_lat))

    geo_series = gpd.GeoSeries(points, crs="EPSG:4326")
    if len(points) < 3:
        envelope = geo_series.unary_union.buffer(0.1)
    else:
        envelope = geo_series.unary_union.convex_hull

    track_line = LineString([(row.lon, row.lat) for row in track.itertuples()])
    return envelope, track_line


def load_gulf_centroids(states: List[str]) -> gpd.GeoDataFrame:
    columns = ["GEOID", "STATEFP", "COUNTYFP", "TRACTCE", "NAME"]
    tract_data = load_tracts_with_centroids(year=2019, columns=columns, states=states)
    return tract_data.centroids


def load_distance_features(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["tract_geoid"] = df["tract_geoid"].astype(str).str.zfill(11)
    df["distance_miles"] = df["distance_nm"] * NAUTICAL_MILE_TO_MILE
    return df


def build_plot_dataframe(centroids: gpd.GeoDataFrame, features: pd.DataFrame, envelope) -> gpd.GeoDataFrame:
    merged = centroids.merge(features, left_on="GEOID", right_on="tract_geoid", how="inner")
    merged = gpd.GeoDataFrame(merged, geometry="geometry", crs=centroids.crs)
    merged["within_envelope"] = merged.geometry.within(envelope)

    # prefer explicit boolean from features, fall back to geometric containment
    merged["within_64kt"] = merged["within_64kt"].astype(object)
    merged.loc[merged["within_64kt"].isna(), "within_64kt"] = merged.loc[
        merged["within_64kt"].isna(), "within_envelope"
    ]
    merged["within_64kt"] = merged["within_64kt"].fillna(False).astype(bool)
    return merged


def select_label_points(df: gpd.GeoDataFrame) -> pd.DataFrame:
    bins = [0, 10, 20, 30, np.inf]
    labels = ["0-10", "10-20", "20-30", "30+"]
    df = df.copy()
    df["distance_bucket"] = pd.cut(df["distance_miles"], bins=bins, labels=labels, right=False)

    samples = []
    rng = random.Random(42)
    for label in labels[:-1]:  # focus on requested ranges
        eligible = df[(df["distance_bucket"] == label) & df["within_64kt"]]
        if eligible.empty:
            continue
        sample_n = min(3, len(eligible))
        samples.extend(eligible.sample(sample_n, random_state=rng.randint(0, 10_000)).index.tolist())
    return df.loc[samples]


def plot_envelope(envelope, track_line, df: gpd.GeoDataFrame, labels: gpd.GeoDataFrame, output_path: Path) -> None:
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 8))

    # Plot envelope
    gpd.GeoSeries([envelope], crs="EPSG:4326").boundary.plot(ax=ax, color="royalblue", linewidth=2, label="64 kt envelope")

    # Plot tract centroids
    df[df["within_64kt"]].plot(ax=ax, color="firebrick", markersize=5, alpha=0.7, label="Tract centroids (within 64 kt)")

    # Plot track line
    gpd.GeoSeries([track_line], crs="EPSG:4326").plot(ax=ax, color="black", linewidth=1.5, label="Storm track")

    for _, row in labels.iterrows():
        name = row.get("NAME", row["GEOID"])
        label_text = f"{name}\n{row['distance_miles']:.1f} mi"
        ax.annotate(
            label_text,
            xy=(row.geometry.x, row.geometry.y),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
            color="darkslategray",
            arrowprops=dict(arrowstyle="-", lw=0.5, color="gray"),
        )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Hurricane Ida 64 kt Envelope & Impacted Census Tracts")
    ax.legend(loc="upper left")

    # Zoom to landfall region (use envelope bounds around Louisiana)
    minx, miny, maxx, maxy = envelope.bounds
    ax.set_xlim(minx - 1.0, maxx + 0.5)
    ax.set_ylim(miny - 0.5, maxy + 0.5)

    ax.grid(alpha=0.2)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def main() -> None:
    states = ["48", "22", "28", "01", "12"]  # TX, LA, MS, AL, FL
    track = load_ida_track()
    envelope, track_line = build_64kt_envelope(track)

    centroids = load_gulf_centroids(states)
    features = load_distance_features(REPO_ROOT / "integration" / "outputs" / "ida_gulf_distances.csv")
    plot_df = build_plot_dataframe(centroids, features, envelope)
    plot_df = plot_df[plot_df["within_64kt"]]

    label_points = select_label_points(plot_df)
    output_path = REPO_ROOT / "integration" / "outputs" / "ida_landfall_envelope.png"
    plot_envelope(envelope, track_line, plot_df, label_points, output_path)
    print(f"Saved plot to {output_path}")


if __name__ == "__main__":
    main()
