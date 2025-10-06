"""Streamlit dashboard for exploring hurricane tract features."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
from branca.colormap import linear
from shapely.geometry import LineString, Polygon
from streamlit_folium import st_folium

# --- Constants ---
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "07_dashboard_app" / "data"
TARGET_HURRICANES_PATH = REPO_ROOT / "00_config" / "target_hurricanes.json"


# --- Data Loading ---
@dataclass(frozen=True)
class StormOption:
    """Represents a storm in the selection dropdown."""
    label: str
    storm_id: str
    storm_name: str
    year: str

@st.cache_data(show_spinner=False)
def get_storm_metadata() -> Dict[str, Dict]:
    """Loads the target hurricanes config file."""
    with open(TARGET_HURRICANES_PATH) as f:
        target_hurricanes = json.load(f)["target_hurricanes"]
    return {item["storm_id"]: item for item in target_hurricanes}

@st.cache_data(show_spinner=False)
def discover_storms() -> List[StormOption]:
    """Return available storms based on the pre-computed GeoJSON files."""
    options: List[StormOption] = []
    storm_meta = get_storm_metadata()
    if not DATA_DIR.exists():
        return options

    for geojson_path in sorted(DATA_DIR.glob("*.geojson")):
        storm_id = geojson_path.stem
        if storm_id in storm_meta:
            meta = storm_meta[storm_id]
            label = f"{meta['name'].title()} ({storm_id}) – {meta['year']}"
            options.append(StormOption(label=label, storm_id=storm_id, storm_name=meta['name'], year=str(meta['year'])))
        else:
            # Fallback if not in metadata file
            label = storm_id
            options.append(StormOption(label=label, storm_id=storm_id, storm_name=storm_id, year=""))

    return options

@st.cache_data(show_spinner=False)
def load_storm_data(storm_id: str) -> Tuple[Optional[Polygon], Optional[LineString], Optional[gpd.GeoDataFrame]]:
    """Load and parse a pre-computed GeoJSON data file for a single storm."""
    geojson_path = DATA_DIR / f"{storm_id}.geojson"
    if not geojson_path.exists():
        return None, None, None

    gdf = gpd.read_file(geojson_path)

    # Extract the different geometry types
    envelope_geom = gdf[gdf["type"] == "envelope"].geometry.iloc[0]
    track_geom = gdf[gdf["type"] == "track"].geometry.iloc[0]
    tracts_gdf = gdf[gdf["type"] == "tract"].copy()

    # Ensure datetime columns are parsed
    for col in ["storm_time", "first_entry_time", "last_exit_time"]:
        if col in tracts_gdf.columns:
            tracts_gdf[col] = pd.to_datetime(tracts_gdf[col], errors="coerce")

    return envelope_geom, track_geom, tracts_gdf


def summarise_features(df: pd.DataFrame) -> Dict[str, str]:
    """Compute key statistics for metric cards."""

    summary: Dict[str, str] = {
        "Affected Tracts": f"{len(df):,}",
    }
    if "duration_in_envelope_hours" in df.columns and not df.empty:
        durations = df["duration_in_envelope_hours"].dropna()
        summary["Duration Range"] = (
            f"{durations.min():.1f} – {durations.max():.1f} hrs" if not durations.empty else "N/A"
        )
        summary["Mean Duration"] = f"{durations.mean():.1f} hrs" if not durations.empty else "N/A"
    if "distance_km" in df.columns and not df.empty:
        distances = df["distance_km"].dropna()
        summary["Distance Range"] = (
            f"{distances.min():.1f} – {distances.max():.1f} km" if not distances.empty else "N/A"
        )
    if "max_wind_experienced_kt" in df.columns and not df.empty:
        summary["Max Wind"] = f'{df['max_wind_experienced_kt'].max():.0f} kt'
    if "storm_time" in df.columns and not df.empty:
        storm_times = df["storm_time"].dropna().sort_values()
        if not storm_times.empty:
            summary["First Observation"] = storm_times.iloc[0].strftime("%Y-%m-%d %H:%M")
            summary["Last Observation"] = storm_times.iloc[-1].strftime("%Y-%m-%d %H:%M")
    return summary


def apply_filters(
    df: pd.DataFrame,
    min_duration: float,
    max_distance: float,
) -> pd.DataFrame:
    """Filter feature dataframe based on user controls."""

    filtered = df.copy()
    if "duration_in_envelope_hours" in filtered.columns:
        filtered = filtered[filtered["duration_in_envelope_hours"] >= min_duration]
    if "distance_km" in filtered.columns:
        filtered = filtered[filtered["distance_km"] <= max_distance]
    return filtered.reset_index(drop=True)


def build_map(
    df: pd.DataFrame,
    coverage: Polygon,
    track_line: Optional[LineString],
    selected_feature: str,
    show_envelope: bool,
    show_track: bool,
    show_centroids: bool,
) -> Optional[folium.Map]:
    """Construct folium map for the filtered dataset."""

    if df.empty:
        return None

    lat_center = df["centroid_lat"].mean()
    lon_center = df["centroid_lon"].mean()
    fmap = folium.Map(location=[lat_center, lon_center], zoom_start=6, tiles="cartodbpositron")

    if show_envelope and coverage is not None:
        folium.GeoJson(
            coverage,
            name="Wind Coverage",
            style_function=lambda _: {
                "fillColor": "#1f77b4",
                "color": "#1f77b4",
                "weight": 2,
                "fillOpacity": 0.2,
            },
        ).add_to(fmap)

    if show_track and track_line is not None and not track_line.is_empty:
        folium.PolyLine(
            locations=[(coord[1], coord[0]) for coord in track_line.coords],
            color="red",
            weight=3,
            opacity=0.8,
            tooltip="Storm Track",
        ).add_to(fmap)

    if show_centroids and selected_feature in df:
        centroid_layer = folium.FeatureGroup(name="Tract Centroids", show=True)
        
        feature_values = df[selected_feature].dropna()
        if feature_values.empty:
            feature_values = pd.Series([0])

        # Create a color map for the selected feature
        colormap = linear.YlOrRd_09.scale(feature_values.min(), feature_values.max())
        colormap.caption = f"{selected_feature.replace('_', ' ').title()}"
        colormap.add_to(fmap)

        for _, row in df.iterrows():
            feature_value = row.get(selected_feature)
            color = colormap(feature_value) if pd.notna(feature_value) else "#cccccc"
            
            # Create a dynamic tooltip
            tooltip_html = f"<b>Tract:</b> {row.get('tract_geoid')}<br>"
            tooltip_html += f"<b>{selected_feature.replace('_', ' ').title()}:</b> {feature_value:.1f}<br><hr>"
            tooltip_html += f"<b>Distance:</b> {row.get('distance_km', float('nan')):.1f} km<br>"
            tooltip_html += f"<b>Duration:</b> {row.get('duration_in_envelope_hours', float('nan')):.1f} hrs<br>"
            tooltip_html += f"<b>Max Wind:</b> {row.get('max_wind_experienced_kt', float('nan')):.1f} kt"

            popup_fields = row.dropna()
            popup_html = "<br>".join(f"<b>{col}:</b> {val}" for col, val in popup_fields.items())

            folium.CircleMarker(
                location=[row["centroid_lat"], row["centroid_lon"]],
                radius=4,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                tooltip=tooltip_html,
                popup=folium.Popup(popup_html, max_width=300),
            ).add_to(centroid_layer)
        centroid_layer.add_to(fmap)

    folium.LayerControl().add_to(fmap)
    return fmap


def render_charts(df: pd.DataFrame, storm_label: str, selected_feature: str) -> None:
    """Render dynamic charts based on the selected feature."""

    if df.empty or selected_feature not in df:
        st.info("No data available for the selected feature or filters.")
        return

    st.subheader(f"Analysis for: {selected_feature.replace('_', ' ').title()}")

    # Create two columns for charts
    col1, col2 = st.columns(2)

    with col1:
        # Show a histogram of the selected feature
        fig_hist = px.histogram(
            df, 
            x=selected_feature, 
            nbins=30, 
            title=f"Distribution of {selected_feature.replace('_', ' ').title()}"
        )
        fig_hist.update_layout(bargap=0.1)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        # Show a scatter plot against distance, if distance is not the selected feature
        if selected_feature != "distance_km" and "distance_km" in df:
            fig_scatter = px.scatter(
                df,
                x="distance_km",
                y=selected_feature,
                title=f"{selected_feature.replace('_', ' ').title()} vs. Distance from Track",
                labels={"distance_km": "Distance (km)", selected_feature: selected_feature.replace('_', ' ').title()},
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            # If distance is selected, show a scatter against duration
            if "duration_in_envelope_hours" in df:
                fig_scatter = px.scatter(
                    df,
                    x="duration_in_envelope_hours",
                    y=selected_feature,
                    title=f"{selected_feature.replace('_', ' ').title()} vs. Duration in Envelope",
                    labels={"duration_in_envelope_hours": "Duration (hrs)", selected_feature: selected_feature.replace('_', ' ').title()},
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.write("No secondary feature to compare against.")


def main() -> None:
    st.set_page_config(page_title="Hurricane Data Explorer", layout="wide")
    st.title("🌀 Hurricane Data Explorer")
    st.caption("Interactively explore tract-level impacts derived from HURDAT2 wind radii.")

    storm_options = discover_storms()
    if not storm_options:
        st.error("No pre-computed GeoJSON files found in /07_dashboard_app/data/. Run the pre-computation script first.")
        return

    option_labels = [opt.label for opt in storm_options]
    selected_label = st.sidebar.selectbox("Select Hurricane", option_labels, index=0)
    selected_option = next(opt for opt in storm_options if opt.label == selected_label)

    # --- Load Data ---
    envelope, track, features_df = load_storm_data(selected_option.storm_id)
    if features_df is None:
        st.error(f"Could not load data for {selected_option.label}. Check the logs.")
        return

    # --- Sidebar --- 
    st.sidebar.markdown("### Visualization Options")

    # Define the curated list of features for the dropdown
    feature_cols = [
        "distance_km",
        "max_wind_experienced_kt",
        "duration_in_envelope_hours",
        "lead_time_cat1_hours",
        "lead_time_cat2_hours",
        "lead_time_cat3_hours",
        "lead_time_cat4_hours",
        "lead_time_cat5_hours",
    ]
    # Filter list to only include columns that actually exist in the dataframe
    available_features = [f for f in feature_cols if f in features_df.columns]
    selected_feature = st.sidebar.selectbox("Select Feature to Visualize", available_features, index=0)

    st.sidebar.markdown("### Filters")
    duration_max = float(features_df.get("duration_in_envelope_hours", pd.Series([0])).max() or 0) or 0.0
    distance_max = float(features_df.get("distance_km", pd.Series([0])).max() or 0) or 0.0

    min_duration = st.sidebar.slider(
        "Minimum Duration (hrs)", 0.0, max(12.0, round(duration_max + 1, 1)), 0.0, 0.25
    )
    max_distance = st.sidebar.slider(
        "Maximum Distance from Track (km)", 0.0, max(50.0, round(distance_max + 1, 1)), max(50.0, round(distance_max + 1, 1)), 1.0
    )

    st.sidebar.markdown("### Map Layers")
    show_envelope = st.sidebar.checkbox("Wind Coverage", value=True)
    show_track = st.sidebar.checkbox("Storm Track", value=True)
    show_centroids = st.sidebar.checkbox("Tract Centroids", value=True)

    # --- Main Page --- 
    filtered_df = apply_filters(features_df, min_duration, max_distance)

    summary = summarise_features(filtered_df)
    summary_cols = st.columns(min(4, len(summary))) if summary else []
    for (label, value), col in zip(summary.items(), summary_cols):
        col.metric(label, value)

    with st.expander("Download Data", expanded=False):
        csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download filtered CSV",
            csv_bytes,
            f"{selected_option.storm_id.lower()}_features_filtered.csv",
            "text/csv",
        )

    map_container = st.container()
    with map_container:
        st.subheader("Interactive Map")
        fmap = build_map(
            filtered_df,
            coverage=envelope,
            track_line=track,
            selected_feature=selected_feature,
            show_envelope=show_envelope,
            show_track=show_track,
            show_centroids=show_centroids,
        )
        if fmap is None:
            st.info("Insufficient data to render the map with current filters.")
        else:
            st_folium(fmap, width=None, height=500, returned_objects=[], key=f"map-{selected_option.storm_id}")

    st.subheader("Analytical Views")
    render_charts(filtered_df, storm_label=selected_option.label, selected_feature=selected_feature)

    st.subheader("Feature Table")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
