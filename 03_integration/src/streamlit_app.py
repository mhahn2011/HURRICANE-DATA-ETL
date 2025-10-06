"""Streamlit dashboard for exploring hurricane tract features."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from branca.colormap import linear
from shapely.geometry import LineString
from streamlit_folium import st_folium

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend(
    [
        str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
        str(REPO_ROOT / "02_transformations" / "storm_tract_distance" / "src"),
        str(REPO_ROOT / "03_integration" / "src"),
    ]
)

from parse_raw import parse_hurdat2_file  # noqa: E402
from profile_clean import clean_hurdat2_data  # noqa: E402
from storm_tract_distance import create_wind_coverage_envelope  # noqa: E402

OUTPUT_DIR = REPO_ROOT / "06_outputs" / "ml_ready"
HURDAT_PATH = REPO_ROOT / "01_data_sources" / "hurdat2" / "input_data" / "hurdat2-atlantic.txt"


@dataclass(frozen=True)
class StormOption:
    label: str
    path: Path
    storm_id: str
    storm_name: str
    year: str


@st.cache_data(show_spinner=False)
def discover_storm_files() -> List[StormOption]:
    """Return available storm feature files with parsed metadata."""

    options: List[StormOption] = []
    if not OUTPUT_DIR.exists():
        return options

    for csv_path in sorted(OUTPUT_DIR.glob("*_features*.csv")):
        try:
            head = pd.read_csv(csv_path, nrows=1)
        except Exception:
            continue
        if head.empty:
            continue

        row = head.iloc[0]
        storm_id = str(row.get("storm_id", "")).strip()
        storm_name = str(row.get("storm_name", "")).strip().title() or csv_path.stem
        year = ""
        if len(storm_id) >= 4 and storm_id[-4:].isdigit():
            year = storm_id[-4:]
        label = f"{storm_name} ({storm_id})" + (f" – {year}" if year else "")
        options.append(StormOption(label=label, path=csv_path, storm_id=storm_id, storm_name=storm_name, year=year))

    return options


@st.cache_data(show_spinner=False)
def load_features(csv_path: Path) -> pd.DataFrame:
    """Load features for selected storm."""

    df = pd.read_csv(csv_path)
    # Ensure datetime columns parsed for analytics
    for col in ["storm_time", "first_entry_time", "last_exit_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_hurdat() -> pd.DataFrame:
    """Load and clean HURDAT2 dataset once."""

    raw = parse_hurdat2_file(str(HURDAT_PATH))
    return clean_hurdat2_data(raw)


@st.cache_data(show_spinner=False)
def compute_track_and_envelope(storm_id: str) -> Dict[str, Optional[object]]:
    """Return track dataframe, coverage envelope, and track line for the storm."""

    hurdat = load_hurdat()
    track_df = hurdat[hurdat["storm_id"] == storm_id].sort_values("date").reset_index(drop=True)
    if track_df.empty:
        return {"track_df": None, "coverage": None, "track_line": None}

    coverage, track_line, _ = create_wind_coverage_envelope(track_df, wind_threshold="64kt", interval_minutes=15)
    return {"track_df": track_df, "coverage": coverage, "track_line": track_line}


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
        summary["Max Wind"] = f"{df['max_wind_experienced_kt'].max():.0f} kt"
    if "STATEFP" in df.columns and not df.empty:
        states = sorted({str(s).zfill(2) for s in df["STATEFP"].dropna()})
        summary["States"] = ", ".join(states) if states else "N/A"
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
    selected_states: List[str],
) -> pd.DataFrame:
    """Filter feature dataframe based on user controls."""

    filtered = df.copy()
    if "duration_in_envelope_hours" in filtered.columns:
        filtered = filtered[filtered["duration_in_envelope_hours"] >= min_duration]
    if "distance_km" in filtered.columns:
        filtered = filtered[filtered["distance_km"] <= max_distance]
    if selected_states:
        filtered = filtered[filtered["STATEFP"].astype(str).str.zfill(2).isin(selected_states)]
    return filtered.reset_index(drop=True)


def build_map(
    df: pd.DataFrame,
    coverage,
    track_line: Optional[LineString],
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

    if show_centroids:
        centroid_layer = folium.FeatureGroup(name="Tract Centroids", show=True)
        distances = df["distance_km"].clip(lower=0)
        if distances.empty:
            distances = pd.Series([0])
        colormap = linear.YlOrRd_09.scale(distances.min(), distances.max())
        colormap.caption = "Distance to Track (km)"
        colormap.add_to(fmap)

        for _, row in df.iterrows():
            color = colormap(row.get("distance_km", 0)) if not pd.isna(row.get("distance_km")) else "#cccccc"
            tooltip = (
                f"<b>Tract:</b> {row.get('tract_geoid')}<br>"
                f"<b>Distance:</b> {row.get('distance_km', float('nan')):.1f} km<br>"
                f"<b>Duration:</b> {row.get('duration_in_envelope_hours', float('nan')):.1f} hrs<br>"
                f"<b>Max Wind:</b> {row.get('max_wind_experienced_kt', float('nan')):.1f} kt"
            )
            popup_fields = row.dropna()
            popup_html = "<br>".join(f"<b>{col}:</b> {val}" for col, val in popup_fields.items())
            folium.CircleMarker(
                location=[row["centroid_lat"], row["centroid_lon"]],
                radius=4,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                tooltip=tooltip,
                popup=folium.Popup(popup_html, max_width=300),
            ).add_to(centroid_layer)
        centroid_layer.add_to(fmap)

    folium.LayerControl().add_to(fmap)
    return fmap


def render_charts(df: pd.DataFrame, storm_label: str) -> None:
    """Render Plotly insight charts within tabs."""

    if df.empty:
        st.info("No data available for the selected filters.")
        return

    tabs = st.tabs([
        "Duration Distribution",
        "Distance vs Duration",
        "Wind Speed Distribution",
        "Exposure Timeline",
    ])

    with tabs[0]:
        if "duration_in_envelope_hours" in df:
            fig = px.histogram(df, x="duration_in_envelope_hours", nbins=30, title="Duration Distribution (hours)")
            fig.update_layout(bargap=0.1)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Duration data unavailable.")

    with tabs[1]:
        if {"distance_km", "duration_in_envelope_hours"}.issubset(df.columns):
            fig = px.scatter(
                df,
                x="distance_km",
                y="duration_in_envelope_hours",
                color="max_wind_experienced_kt" if "max_wind_experienced_kt" in df else None,
                title="Distance vs Duration",
                labels={"distance_km": "Distance (km)", "duration_in_envelope_hours": "Duration (hrs)"},
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Distance/duration columns unavailable.")

    with tabs[2]:
        if "max_wind_experienced_kt" in df:
            fig = px.histogram(df, x="max_wind_experienced_kt", nbins=30, title="Max Wind Experienced (kt)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Max wind data unavailable.")

    with tabs[3]:
        if {"first_entry_time", "last_exit_time"}.issubset(df.columns):
            timeline_df = df[["tract_geoid", "first_entry_time", "last_exit_time"]].dropna()
            if timeline_df.empty:
                st.write("No exposure timeline data available.")
            else:
                timeline_df = timeline_df.assign(duration=(timeline_df["last_exit_time"] - timeline_df["first_entry_time"]).dt.total_seconds() / 3600)
                fig = px.timeline(
                    timeline_df,
                    x_start="first_entry_time",
                    x_end="last_exit_time",
                    y="tract_geoid",
                    color="duration",
                    title=f"Exposure Window Timeline – {storm_label}",
                )
                fig.update_yaxes(showticklabels=False)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Exposure timing columns unavailable.")


def main() -> None:
    st.set_page_config(page_title="Hurricane Data Explorer", layout="wide")
    st.title("🌀 Hurricane Data Explorer")
    st.caption("Interactively explore tract-level impacts derived from HURDAT2 wind radii.")

    storm_options = discover_storm_files()
    if not storm_options:
        st.error("No feature CSV files found under 06_outputs/ml_ready/. Run the ETL pipeline first.")
        return

    option_labels = [opt.label for opt in storm_options]
    default_index = 0
    selected_label = st.sidebar.selectbox("Select Hurricane", option_labels, index=default_index)
    selected_option = next(opt for opt in storm_options if opt.label == selected_label)

    st.sidebar.markdown("### Filters")
    features_df = load_features(selected_option.path)

    duration_max = float(features_df.get("duration_in_envelope_hours", pd.Series([0])).max() or 0) or 0.0
    distance_max = float(features_df.get("distance_km", pd.Series([0])).max() or 0) or 0.0

    min_duration = st.sidebar.slider(
        "Minimum Duration (hrs)",
        min_value=0.0,
        max_value=max(12.0, round(duration_max + 1, 1)),
        value=0.0,
        step=0.25,
    )
    max_distance = st.sidebar.slider(
        "Maximum Distance from Track (km)",
        min_value=0.0,
        max_value=max(50.0, round(distance_max + 1, 1)),
        value=max(50.0, round(distance_max + 1, 1)),
        step=1.0,
    )

    available_states = sorted({str(s).zfill(2) for s in features_df.get("STATEFP", pd.Series([])).dropna()})
    selected_states = st.sidebar.multiselect("Filter by State FIPS", options=available_states)

    st.sidebar.markdown("### Map Layers")
    show_envelope = st.sidebar.checkbox("Wind Coverage", value=True)
    show_track = st.sidebar.checkbox("Storm Track", value=True)
    show_centroids = st.sidebar.checkbox("Tract Centroids", value=True)

    filtered_df = apply_filters(features_df, min_duration=min_duration, max_distance=max_distance, selected_states=selected_states)

    summary = summarise_features(filtered_df)
    summary_cols = st.columns(min(4, len(summary))) if summary else []
    for (label, value), col in zip(summary.items(), summary_cols):
        col.metric(label, value)

    with st.expander("Download Data", expanded=False):
        csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download filtered CSV",
            data=csv_bytes,
            file_name=f"{selected_option.storm_id.lower()}_features_filtered.csv",
            mime="text/csv",
        )

    track_assets = compute_track_and_envelope(selected_option.storm_id)
    map_container = st.container()
    with map_container:
        st.subheader("Interactive Map")
        fmap = build_map(
            filtered_df,
            coverage=track_assets.get("coverage"),
            track_line=track_assets.get("track_line"),
            show_envelope=show_envelope,
            show_track=show_track,
            show_centroids=show_centroids,
        )
        if fmap is None:
            st.info("Insufficient data to render the map with current filters.")
        else:
            st_folium(fmap, width=None, height=500, returned_objects=[], key=f"map-{selected_option.storm_id}")

    st.subheader("Analytical Views")
    render_charts(filtered_df, storm_label=selected_option.label)

    st.subheader("Feature Table")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
