"""Streamlit viewer for arc-based hurricane wind field visualizations."""

from __future__ import annotations

import datetime as dt
import tempfile
from pathlib import Path
from typing import Dict
import json

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
sys_paths = [
    REPO_ROOT / "01_data_sources" / "hurdat2" / "src",
    REPO_ROOT / "04_src_shared",
]

for path in sys_paths:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from visualize_folium_qa import (
    add_rmw_layer,
    add_track_point_markers,
    add_wind_field_layer,
)

DEFAULT_HURDAT_PATH = REPO_ROOT / "01_data_sources" / "hurdat2" / "raw" / "hurdat2-atlantic.txt"
EXPORT_DIR = REPO_ROOT / "06_outputs" / "visuals" / "hurdat2" / "streamlit_exports"
TARGET_CONFIG_PATH = REPO_ROOT / "00_config" / "target_hurricanes.json"


@st.cache_data(show_spinner=False)
def load_hurdat_dataframe(hurdat_path: Path) -> pd.DataFrame:
    df_raw = parse_hurdat2_file(str(hurdat_path))
    df_clean = clean_hurdat2_data(df_raw)
    return df_clean


@st.cache_data(show_spinner=False)
def list_available_storms(hurdat_df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        hurdat_df.groupby("storm_id")
        .agg(
            storm_name=("storm_name", "first"),
            first_obs=("date", "min"),
            last_obs=("date", "max"),
            max_wind=("max_wind", "max"),
        )
        .reset_index()
    )
    grouped["year"] = grouped["first_obs"].dt.year
    grouped["label"] = grouped.apply(
        lambda row: f"{row['storm_name'].title()} ({row['storm_id']}) - {row['year']}", axis=1
    )
    grouped = grouped.sort_values("first_obs", ascending=False).reset_index(drop=True)
    return grouped


@st.cache_data(show_spinner=False)
def load_target_hurricanes(config_path: Path) -> pd.DataFrame:
    if not config_path.exists():
        raise FileNotFoundError(f"Target hurricane configuration missing: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    entries = payload.get("target_hurricanes", [])
    if not entries:
        raise ValueError("target_hurricanes list empty in configuration file")

    df = pd.DataFrame(entries)
    expected_columns = {"storm_id", "name", "year"}
    if not expected_columns.issubset(df.columns):
        raise ValueError(
            "target_hurricanes.json must contain storm_id, name, and year for each entry"
        )

    df["name"] = df["name"].str.upper()
    df = df.sort_values(["year", "name"]).reset_index(drop=True)
    return df


@st.cache_data(show_spinner=False)
def load_storm_track(hurdat_df: pd.DataFrame, storm_id: str) -> pd.DataFrame:
    track = hurdat_df[hurdat_df["storm_id"] == storm_id].sort_values("date").reset_index(drop=True)
    return track


@st.cache_resource(show_spinner=False)
def build_wind_field_map(
    storm_id: str,
    track_df: pd.DataFrame,
    show_34kt: bool,
    show_50kt: bool,
    show_64kt: bool,
    show_rmw: bool,
    show_track_points: bool,
) -> folium.Map:
    if track_df.empty:
        raise ValueError(f"Storm {storm_id} has no track data")

    center_lat = track_df["lat"].mean()
    center_lon = track_df["lon"].mean()

    folium_map = folium.Map(location=[center_lat, center_lon], tiles="CartoDB Positron", zoom_start=6)
    bounds = [[track_df["lat"].min(), track_df["lon"].min()], [track_df["lat"].max(), track_df["lon"].max()]]
    folium_map.fit_bounds(bounds)

    if show_64kt:
        add_wind_field_layer(folium_map, track_df, 64, "#d73027", 0.35)
    if show_50kt:
        add_wind_field_layer(folium_map, track_df, 50, "#fc8d59", 0.25)
    if show_34kt:
        add_wind_field_layer(folium_map, track_df, 34, "#fee090", 0.20)
    if show_rmw:
        add_rmw_layer(folium_map, track_df)
    if show_track_points:
        add_track_point_markers(folium_map, track_df)

    return folium_map


def format_storm_stats(track_df: pd.DataFrame) -> Dict[str, str]:
    stats: Dict[str, str] = {}
    if track_df.empty:
        return stats

    stats["Observations"] = f"{len(track_df)}"

    first_time = track_df["date"].min()
    last_time = track_df["date"].max()
    stats["Lifetime"] = f"{first_time:%Y-%m-%d %H:%M} — {last_time:%Y-%m-%d %H:%M}"

    max_wind = track_df["max_wind"].max()
    if pd.notna(max_wind):
        stats["Peak Intensity"] = f"{int(max_wind)} kt"

    min_pressure = track_df["min_pressure"].min()
    if pd.notna(min_pressure):
        stats["Min Pressure"] = f"{int(min_pressure)} mb"

    stats["Track Length"] = f"{track_df[['lat', 'lon']].drop_duplicates().shape[0]} points"
    return stats


def main() -> None:
    st.set_page_config(page_title="Hurricane Wind Field Viewer", layout="wide")
    st.title("🌀 Hurricane Wind Field Viewer")
    st.caption("Explore arc-based wind field envelopes for the 14 major Gulf Coast hurricanes we analyze.")

    hurdat_path = DEFAULT_HURDAT_PATH
    hurdat_df = load_hurdat_dataframe(hurdat_path)
    storm_listing = list_available_storms(hurdat_df)
    target_df = load_target_hurricanes(TARGET_CONFIG_PATH)

    merged = storm_listing.merge(target_df, on="storm_id", how="inner", suffixes=("_hurdat", ""))
    missing_ids = sorted(set(target_df["storm_id"]) - set(merged["storm_id"]))
    if missing_ids:
        st.warning(
            "The following target storms were not found in the HURDAT2 file: "
            + ", ".join(missing_ids)
        )

    storm_listing = merged
    storm_listing["label"] = storm_listing.apply(
        lambda row: f"{row['name'].title()} ({row['storm_id']}) - {row['year']}", axis=1
    )
    storm_listing = storm_listing.sort_values("year", ascending=False).reset_index(drop=True)

    if storm_listing.empty:
        st.error("No target hurricanes found in the HURDAT2 dataset.")
        return

    with st.sidebar:
        st.header("Storm Selection")
        selected_label = st.selectbox(
            "Choose Hurricane",
            options=storm_listing["label"].tolist(),
            index=0,
        )

        selected_row = storm_listing[storm_listing["label"] == selected_label].iloc[0]
        storm_id = selected_row["storm_id"]
        storm_name = selected_row["name"].title()

        st.caption(f"Showing {len(storm_listing)} target hurricanes (2005–2021).")
        st.markdown("---")
        st.subheader("Layers")
        show_64kt = st.checkbox("64 kt Wind Field", value=True)
        show_50kt = st.checkbox("50 kt Wind Field", value=True)
        show_34kt = st.checkbox("34 kt Wind Field", value=True)
        show_rmw = st.checkbox("Radius of Maximum Wind", value=False)
        show_track_points = st.checkbox("Track Points", value=False)

        if st.button("Clear Cache", help="Force regeneration of cached datasets and maps"):
            load_hurdat_dataframe.clear()
            list_available_storms.clear()
            load_storm_track.clear()
            build_wind_field_map.clear()
            st.experimental_rerun()

    track_df = load_storm_track(hurdat_df, storm_id)
    if track_df.empty:
        st.error(f"No track data available for {storm_name} ({storm_id}).")
        return

    stats = format_storm_stats(track_df)
    if stats:
        with st.sidebar.expander("Storm Statistics", expanded=True):
            for key, value in stats.items():
                st.markdown(f"**{key}:** {value}")

        with st.sidebar.expander("Included Storms", expanded=False):
            for _, row in storm_listing.sort_values("year", ascending=False).iterrows():
                st.markdown(f"- {row['name'].title()} ({row['storm_id']}) — {row['year']}")

    with st.spinner("Rendering wind fields…"):
        folium_map = build_wind_field_map(
            storm_id=storm_id,
            track_df=track_df,
            show_34kt=show_34kt,
            show_50kt=show_50kt,
            show_64kt=show_64kt,
            show_rmw=show_rmw,
            show_track_points=show_track_points,
        )

    st.subheader(f"{storm_name.title()} ({storm_id})")
    st_folium(folium_map, width=None, height=600, returned_objects=[])

    export_col1, export_col2 = st.columns([3, 2])
    with export_col1:
        st.markdown("### Export Map")
        map_html = folium_map.get_root().render()
        file_timestamp = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        download_filename = f"{storm_id.lower()}_wind_field_{file_timestamp}.html"
        st.download_button(
            label="Download HTML",
            data=map_html.encode("utf-8"),
            file_name=download_filename,
            mime="text/html",
        )

    with export_col2:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        if st.button("Save to Repository", help="Write the current map to the streamlit_exports folder"):
            save_path = EXPORT_DIR / download_filename
            folium_map.save(save_path)
            st.success(f"Saved current map to {save_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
