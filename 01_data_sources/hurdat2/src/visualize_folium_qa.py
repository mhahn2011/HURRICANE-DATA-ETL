"""Generate Folium QA/QC maps for inspecting HURDAT2 wind radii."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import folium
import pandas as pd

try:  # Support both package imports (tests) and direct script execution
    from .envelope_algorithm import calculate_destination_point
    from .parse_raw import parse_hurdat2_file
    from .profile_clean import clean_hurdat2_data
except ImportError:  # pragma: no cover - fallback for CLI usage
    import sys

    MODULE_ROOT = Path(__file__).resolve().parent
    if str(MODULE_ROOT) not in sys.path:
        sys.path.append(str(MODULE_ROOT))

    from envelope_algorithm import calculate_destination_point
    from parse_raw import parse_hurdat2_file
    from profile_clean import clean_hurdat2_data


QUADRANT_BEARINGS: Dict[str, float] = {"ne": 45.0, "se": 135.0, "sw": 225.0, "nw": 315.0}
NM_TO_METERS = 1852.0


def _valid_radii(values: Iterable[Optional[float]]) -> bool:
    for value in values:
        if value is None or pd.isna(value) or value <= 0:
            return False
    return True


def create_wind_quadrilateral(
    center_lat: float,
    center_lon: float,
    radii_nm: Dict[str, Optional[float]],
) -> Optional[List[Tuple[float, float]]]:
    """Return ordered lat/lon vertices for the quadrilateral or ``None`` if incomplete."""

    if not _valid_radii(radii_nm.values()):
        return None

    vertices: List[Tuple[float, float]] = []
    for quadrant in ("ne", "se", "sw", "nw"):
        bearing = QUADRANT_BEARINGS[quadrant]
        distance_nm = float(radii_nm[quadrant])  # type: ignore[arg-type]
        dest_lon, dest_lat = calculate_destination_point(center_lat, center_lon, bearing, distance_nm)
        vertices.append((dest_lat, dest_lon))

    return vertices


def add_wind_field_layer(
    folium_map: folium.Map,
    track_df: pd.DataFrame,
    threshold_kt: int,
    color: str,
    opacity: float,
) -> folium.FeatureGroup:
    """Add a wind-field layer for the requested threshold and return the feature group."""

    prefix = f"wind_radii_{threshold_kt}"
    layer = folium.FeatureGroup(name=f"{threshold_kt} kt Wind Field", show=True)

    for _, row in track_df.iterrows():
        radii = {
            "ne": row.get(f"{prefix}_ne"),
            "se": row.get(f"{prefix}_se"),
            "sw": row.get(f"{prefix}_sw"),
            "nw": row.get(f"{prefix}_nw"),
        }

        vertices = create_wind_quadrilateral(row["lat"], row["lon"], radii)
        if not vertices:
            continue

        popup_lines = [
            f"<b>Time:</b> {pd.Timestamp(row['date']).strftime('%Y-%m-%d %H:%M UTC')}",
            f"<b>Max Wind:</b> {row.get('max_wind', 'NA')} kt",
            f"<b>{threshold_kt}kt NE:</b> {radii['ne']} nm",
            f"<b>{threshold_kt}kt SE:</b> {radii['se']} nm",
            f"<b>{threshold_kt}kt SW:</b> {radii['sw']} nm",
            f"<b>{threshold_kt}kt NW:</b> {radii['nw']} nm",
        ]
        popup_html = "<br>".join(popup_lines)

        folium.Polygon(
            locations=vertices,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=opacity,
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(layer)

    layer.add_to(folium_map)
    return layer


def _intensity_color(max_wind: Optional[float], status: str) -> str:
    if max_wind is None or pd.isna(max_wind):
        max_wind = 0.0

    if max_wind >= 137:
        return "darkred"
    if max_wind >= 113:
        return "red"
    if max_wind >= 96:
        return "orange"
    if max_wind >= 64:
        return "yellow"
    if status == "TS":
        return "green"
    if status == "TD":
        return "blue"
    return "gray"


def add_track_point_markers(folium_map: folium.Map, track_df: pd.DataFrame) -> folium.FeatureGroup:
    layer = folium.FeatureGroup(name="Track Points", show=True)

    for _, row in track_df.iterrows():
        color = _intensity_color(row.get("max_wind"), str(row.get("status", "")))
        popup_lines = [
            f"<b>Time:</b> {pd.Timestamp(row['date']).strftime('%Y-%m-%d %H:%M UTC')}",
            f"<b>Status:</b> {row.get('status', 'NA')}",
            f"<b>Max Wind:</b> {row.get('max_wind', 'NA')} kt",
            f"<b>Min Pressure:</b> {row.get('min_pressure', 'NA')} mb",
        ]

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup("<br>".join(popup_lines), max_width=250),
        ).add_to(layer)

        max_wind_value = row.get("max_wind")
        if max_wind_value is not None and not pd.isna(max_wind_value):
            label_html = (
                '<div class="track-point-label" '
                'style="font-size:10px;font-weight:600;color:#1b263b;'
                'background:rgba(255,255,255,0.85);padding:2px 4px;'
                'border-radius:3px;border:1px solid rgba(27,38,59,0.2);">'
                f"{int(max_wind_value)} kt"
                "</div>"
            )
            folium.Marker(
                location=[row["lat"], row["lon"]],
                icon=folium.DivIcon(
                    html=label_html,
                    icon_size=(0, 0),
                    icon_anchor=(0, -12),
                ),
            ).add_to(layer)

    layer.add_to(folium_map)
    return layer


def add_rmw_layer(folium_map: folium.Map, track_df: pd.DataFrame) -> Optional[folium.FeatureGroup]:
    if "radius_max_wind" not in track_df.columns:
        return None

    subset = track_df.dropna(subset=["radius_max_wind"])
    if subset.empty:
        return None

    layer = folium.FeatureGroup(name="Radius of Maximum Wind", show=True)
    for _, row in subset.iterrows():
        radius_nm = float(row["radius_max_wind"])
        folium.Circle(
            location=[row["lat"], row["lon"]],
            radius=radius_nm * NM_TO_METERS,
            color="purple",
            weight=2,
            fill=True,
            fill_color="purple",
            fill_opacity=0.2,
            popup=folium.Popup(
                f"<b>Time:</b> {pd.Timestamp(row['date']).strftime('%Y-%m-%d %H:%M UTC')}<br>"
                f"<b>RMW:</b> {radius_nm:.0f} nm",
                max_width=250,
            ),
        ).add_to(layer)

    layer.add_to(folium_map)
    return layer


def generate_qa_map(track_df: pd.DataFrame, storm_name: str, storm_id: str, output_path: Path) -> folium.Map:
    if track_df.empty:
        raise ValueError("track_df must contain at least one record")

    track_df = track_df.sort_values("date").reset_index(drop=True)

    center_lat = track_df["lat"].mean()
    center_lon = track_df["lon"].mean()
    folium_map = folium.Map(location=[center_lat, center_lon], tiles="CartoDB Positron", zoom_start=6)

    bounds = [[track_df["lat"].min(), track_df["lon"].min()], [track_df["lat"].max(), track_df["lon"].max()]]
    folium_map.fit_bounds(bounds)

    folium.PolyLine(
        locations=track_df[["lat", "lon"]].values.tolist(),
        color="black",
        weight=2,
        tooltip=f"Track: {storm_name} ({storm_id})",
    ).add_to(folium_map)

    add_wind_field_layer(folium_map, track_df, 34, color="#ffd166", opacity=0.3)
    add_wind_field_layer(folium_map, track_df, 50, color="#f79d65", opacity=0.4)
    add_wind_field_layer(folium_map, track_df, 64, color="#ef476f", opacity=0.5)
    add_rmw_layer(folium_map, track_df)
    add_track_point_markers(folium_map, track_df)

    folium.LayerControl(collapsed=False).add_to(folium_map)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    folium_map.save(str(output_path))
    return folium_map


def _load_storm_track(hurdat_path: Path, storm_id: str) -> pd.DataFrame:
    storms = parse_hurdat2_file(str(hurdat_path))
    cleaned = clean_hurdat2_data(storms)
    track = cleaned[cleaned["storm_id"] == storm_id].copy()
    if track.empty:
        raise ValueError(f"Storm {storm_id} not found in {hurdat_path}")
    return track


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Folium QA/QC map for storm wind fields")
    parser.add_argument("--storm-id", required=True, help="Storm identifier (e.g., AL092021)")
    parser.add_argument(
        "--hurdat-path",
        default="hurdat2/input_data/hurdat2-atlantic.txt",
        help="Path to raw HURDAT2 file",
    )
    parser.add_argument(
        "--output",
        help="Output HTML path (default: hurdat2/outputs/qa_maps/<storm>_wind_field.html)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    hurdat_path = Path(args.hurdat_path)
    if not hurdat_path.exists():
        raise FileNotFoundError(f"HURDAT2 file not found at {hurdat_path}")

    track = _load_storm_track(hurdat_path, args.storm_id)
    storm_name = str(track["storm_name"].iloc[0]) if "storm_name" in track.columns else args.storm_id

    if args.output:
        output_path = Path(args.output)
    else:
        representative_year = int(pd.Timestamp(track["date"].iloc[0]).year)
        safe_name = storm_name.upper().replace(" ", "_")
        default_name = f"{safe_name}_{representative_year}_wind_field.html"
        output_path = Path("hurdat2/outputs/qa_maps") / default_name

    generate_qa_map(track, storm_name, args.storm_id, output_path)
    print(f"✅ Generated QA map for {storm_name} ({args.storm_id}) at {output_path}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
