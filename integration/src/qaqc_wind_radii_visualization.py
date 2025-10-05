"""QA/QC visualization for wind-radii quadrilaterals and duration values.

This script creates an interactive Folium map showing:
1. All wind-radii quadrilaterals (observed and interpolated at 15-min intervals)
2. Tract centroids color-coded by duration values
3. Visual inspection tools for debugging duration calculation issues
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import folium
import numpy as np
from shapely.geometry import Point, Polygon

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(REPO_ROOT / "hurdat2" / "src"),
    str(REPO_ROOT / "census" / "src"),
    str(REPO_ROOT / "integration" / "src"),
])

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope, impute_missing_wind_radii
from duration_calculator import (
    interpolate_track_temporal,
    create_instantaneous_wind_polygon,
)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _interpolate_color(hex_color: str, factor: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    factor = min(max(factor, 0.0), 1.0)
    r_new = int(r + (255 - r) * factor)
    g_new = int(g + (255 - g) * factor)
    b_new = int(b + (255 - b) * factor)
    return f"#{r_new:02x}{g_new:02x}{b_new:02x}"


def _add_polygon(
    layer_group: folium.FeatureGroup,
    polygon: Polygon,
    color: str,
    tooltip_html: str,
    weight: int = 2,
    dash_array: Optional[str] = None,
    fill_opacity: float = 0.3,
) -> None:
    if polygon is None or polygon.is_empty:
        return

    coords = list(polygon.exterior.coords)
    locations = [(lat, lon) for lon, lat in coords]

    folium.Polygon(
        locations=locations,
        color=color,
        weight=weight,
        fill=True,
        fill_color=color,
        fill_opacity=fill_opacity,
        dash_array=dash_array,
        tooltip=folium.Tooltip(tooltip_html, sticky=True),
    ).add_to(layer_group)


def plot_quadrilateral(
    m: folium.Map,
    polygon: Polygon,
    timestamp: pd.Timestamp,
    is_interpolated: bool,
    has_wind_radii: bool,
    is_imputed: bool,
    layer_group: folium.FeatureGroup,
) -> None:
    """Add a single wind-radii quadrilateral to the map."""

    if polygon is None:
        return

    # Color scheme: observed (solid) vs interpolated (dashed) vs imputed (dotted)
    if is_imputed:
        # Imputed wind radii - use dotted/dashed orange/yellow
        color = 'orange' if has_wind_radii else 'lightyellow'
        fill_opacity = 0.15
        weight = 2
        dash_array = '10, 5'  # Dashed for imputed
    elif is_interpolated:
        # Temporal interpolation - purple/gray
        color = 'purple' if has_wind_radii else 'gray'
        fill_opacity = 0.1
        weight = 1
        dash_array = '5, 5'
    else:
        # Observed data - solid dark blue
        color = 'darkblue' if has_wind_radii else 'lightgray'
        fill_opacity = 0.3
        weight = 2
        dash_array = None

    # Create tooltip with timestamp and metadata
    radii_type = 'IMPUTED (Proportional)' if is_imputed else ('Interpolated' if is_interpolated else 'Observed')
    tooltip_html = f"""
    <b>Time:</b> {timestamp.strftime('%Y-%m-%d %H:%M')}<br>
    <b>Type:</b> {radii_type}<br>
    <b>Has Wind Radii:</b> {'Yes' if has_wind_radii else 'No'}
    """

    # Extract coordinates for the polygon
    coords = list(polygon.exterior.coords)
    locations = [(lat, lon) for lon, lat in coords]

    folium.Polygon(
        locations=locations,
        color=color,
        weight=weight,
        fill=True,
        fill_color=color,
        fill_opacity=fill_opacity,
        dash_array=dash_array,
        tooltip=folium.Tooltip(tooltip_html, sticky=True),
    ).add_to(layer_group)


def create_qaqc_map(storm_id: str = 'AL092021', interval_minutes: int = 15) -> folium.Map:
    """Create comprehensive QA/QC visualization map."""

    # Load hurricane track data
    print("Loading hurricane track data...")
    hurdat_path = REPO_ROOT / "hurdat2/input_data/hurdat2-atlantic.txt"
    storms = parse_hurdat2_file(hurdat_path)
    cleaned = clean_hurdat2_data(storms)
    track = cleaned[cleaned['storm_id'] == storm_id].sort_values('date').reset_index(drop=True)

    if track.empty:
        raise ValueError(f"Storm {storm_id} not found")

    print(f"Track has {len(track)} observed points")

    # Create envelope for reference
    envelope_geom, track_line, _ = create_storm_envelope(
        track, wind_threshold='64kt', alpha=0.6, verbose=False
    )

    # Apply proportional imputation FIRST (before temporal interpolation)
    print("Applying proportional wind radii imputation...")
    track_imputed = impute_missing_wind_radii(track, wind_threshold='64kt')
    print(f"Imputation complete. Columns: {track_imputed.columns.tolist()}")

    # Store imputation flags separately (can't interpolate boolean columns)
    imputation_flags = track_imputed[['date', 'wind_radii_64_any_imputed']].copy()

    # Prepare track for interpolation - use IMPUTED columns (numeric only)
    track_subset = track_imputed[[
        'date', 'lat', 'lon',
        'wind_radii_64_ne_imputed', 'wind_radii_64_se_imputed',
        'wind_radii_64_sw_imputed', 'wind_radii_64_nw_imputed',
    ]].copy()

    # Rename for interpolation compatibility
    track_subset = track_subset.rename(columns={
        'wind_radii_64_ne_imputed': 'wind_radii_64_ne',
        'wind_radii_64_se_imputed': 'wind_radii_64_se',
        'wind_radii_64_sw_imputed': 'wind_radii_64_sw',
        'wind_radii_64_nw_imputed': 'wind_radii_64_nw',
    })

    # Interpolate track
    print(f"Interpolating track at {interval_minutes}-minute intervals...")
    interpolated_track = interpolate_track_temporal(track_subset, interval_minutes=interval_minutes)
    print(f"Interpolated track has {len(interpolated_track)} points")

    # Mark which points are interpolated (temporal) vs imputed (spatial)
    original_timestamps = set(track['date'].values)
    interpolated_track['is_interpolated'] = ~interpolated_track['date'].isin(original_timestamps)

    # Merge imputation flags back (forward fill for interpolated rows)
    interpolated_track = interpolated_track.merge(
        imputation_flags, on='date', how='left'
    )
    interpolated_track['wind_radii_64_any_imputed'] = interpolated_track['wind_radii_64_any_imputed'].fillna(False).ffill().fillna(False)

    # Initialize map
    center_lat = track['lat'].mean()
    center_lon = track['lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=7)

    # Create layer groups
    observed_layer = folium.FeatureGroup(name='Observed Wind-Radii (Solid Blue)', show=True)
    imputed_layer = folium.FeatureGroup(name='Imputed Wind-Radii (Dashed Orange)', show=True)
    interpolated_layer = folium.FeatureGroup(name='Temporal Interpolation (Dotted Purple)', show=True)

    # Plot all quadrilaterals
    print("Plotting wind-radii quadrilaterals...")
    quadrilateral_count = 0
    observed_count = 0
    interpolated_count = 0
    imputed_count = 0

    for idx, row in interpolated_track.iterrows():
        polygon = create_instantaneous_wind_polygon(
            lat=row['lat'],
            lon=row['lon'],
            wind_radii_ne=row['wind_radii_64_ne'],
            wind_radii_se=row['wind_radii_64_se'],
            wind_radii_sw=row['wind_radii_64_sw'],
            wind_radii_nw=row['wind_radii_64_nw'],
        )

        if polygon is not None:
            has_wind_radii = not (
                pd.isna(row['wind_radii_64_ne']) and
                pd.isna(row['wind_radii_64_se']) and
                pd.isna(row['wind_radii_64_sw']) and
                pd.isna(row['wind_radii_64_nw'])
            )

            is_imputed = row.get('wind_radii_64_any_imputed', False)

            # Choose layer based on type
            if is_imputed:
                layer = imputed_layer
                imputed_count += 1
            elif row['is_interpolated']:
                layer = interpolated_layer
                interpolated_count += 1
            else:
                layer = observed_layer
                observed_count += 1

            plot_quadrilateral(
                m=m,
                polygon=polygon,
                timestamp=row['date'],
                is_interpolated=row['is_interpolated'],
                has_wind_radii=has_wind_radii,
                is_imputed=is_imputed,
                layer_group=layer,
            )

            quadrilateral_count += 1

    observed_layer.add_to(m)
    imputed_layer.add_to(m)
    interpolated_layer.add_to(m)

    print(f"Plotted {quadrilateral_count} quadrilaterals:")
    print(f"  - {observed_count} observed (solid blue)")
    print(f"  - {imputed_count} imputed (dashed orange)")
    print(f"  - {interpolated_count} temporal interpolation (dotted purple)")

    # Add envelope for reference
    if envelope_geom:
        folium.GeoJson(
            envelope_geom,
            name='Storm Envelope (64kt)',
            style_function=lambda x: {
                'fillColor': 'yellow',
                'color': 'orange',
                'weight': 3,
                'fillOpacity': 0.1,
                'dashArray': '10, 5'
            }
        ).add_to(m)

    # Add track centerline
    if track_line:
        folium.PolyLine(
            locations=[(y, x) for x, y in track_line.coords],
            color='red',
            weight=3,
            opacity=0.8,
            tooltip='Hurricane Track Centerline'
        ).add_to(m)

    # Load tract features to show duration values
    print("Loading tract features...")
    features_path = REPO_ROOT / "integration/outputs/ida_features_complete_v2.csv"
    if features_path.exists():
        features = pd.read_csv(features_path)
        features['tract_geoid'] = features['tract_geoid'].astype(str)

        # Create layer for tract centroids
        tracts_layer = folium.FeatureGroup(name='Tract Centroids (Duration QA/QC)', show=True)

        # Define color scale for duration
        def get_duration_color(hours: float) -> str:
            if hours == 0:
                return 'blue'  # Problematic tracts
            elif hours < 2:
                return '#FFFFB2'  # Light Yellow
            elif hours < 4:
                return '#FECC5C'  # Yellow-Orange
            elif hours < 6:
                return '#FD8D3C'  # Orange
            elif hours < 8:
                return '#F03B20'  # Red-Orange
            elif hours < 10:
                return '#BD0026'  # Red
            else:
                return '#750021'  # Dark Red

        print(f"Plotting {len(features)} tract centroids...")

        for idx, row in features.iterrows():
            duration = row['duration_in_envelope_hours']
            color = get_duration_color(duration)
            
            style_color = 'blue' if duration == 0 else 'black'
            duration_text = "DURATION = 0 hrs" if duration == 0 else f"Duration: {duration:.1f} hrs"

            tooltip_html = f"""
            <b style="color: {style_color};">{duration_text}</b><br>
            <b>Tract:</b> {row['tract_geoid']}<br>
            <b>Distance:</b> {row['distance_km']:.1f} km<br>
            <b>Max Wind:</b> {row['max_wind_experienced_kt']:.1f} kt<br>
            <b>Window:</b> {row.get('exposure_window_hours', 'N/A')} hrs
            """

            folium.CircleMarker(
                location=[row['centroid_lat'], row['centroid_lon']],
                radius=5,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                tooltip=folium.Tooltip(tooltip_html, sticky=True),
            ).add_to(tracts_layer)

        tracts_layer.add_to(m)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Add legend
    legend_html = f'''
    <div style="position: fixed; top: 10px; right: 10px; width: 280px; background-color: white; z-index:9999; font-size:11px; border:2px solid grey; border-radius: 5px; padding: 10px;">
        <p style="margin: 0 0 8px 0;"><b>QA/QC Wind-Radii Visualization</b></p>
        <p style="margin: 8px 0 4px 0;"><b>Quadrilaterals:</b></p>
        <p style="margin: 3px 0;"><i style="background: darkblue; width: 20px; height: 3px; display: inline-block; opacity: 0.6;"></i> Observed (w/ radii)</p>
        <p style="margin: 3px 0;"><i style="background: lightgray; width: 20px; height: 3px; display: inline-block; opacity: 0.6;"></i> Observed (no radii)</p>
        <p style="margin: 3px 0;"><i style="background: purple; width: 20px; height: 3px; display: inline-block; opacity: 0.3; border: 1px dashed purple;"></i> Interpolated (w/ radii)</p>
        <p style="margin: 3px 0;"><i style="background: gray; width: 20px; height: 3px; display: inline-block; opacity: 0.3; border: 1px dashed gray;"></i> Interpolated (no radii)</p>
        
        <p style="margin: 8px 0 4px 0;"><b>Tract Duration (hours):</b></p>
        <p style="margin: 3px 0;"><i style="background: blue; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 0 (Problem)</p>
        <p style="margin: 3px 0;"><i style="background: #FFFFB2; width: 12px; height: 12px; display: inline-block; border-radius: 50%; border: 1px solid #ccc;"></i> &lt; 2</p>
        <p style="margin: 3px 0;"><i style="background: #FECC5C; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 2-4</p>
        <p style="margin: 3px 0;"><i style="background: #FD8D3C; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 4-6</p>
        <p style="margin: 3px 0;"><i style="background: #F03B20; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 6-8</p>
        <p style="margin: 3px 0;"><i style="background: #BD0026; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 8-10</p>
        <p style="margin: 3px 0;"><i style="background: #750021; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 10+</p>

        <hr style="margin: 8px 0;">
        <p style="margin: 0; font-size: 10px;">
            <b>Total Quadrilaterals:</b> {quadrilateral_count}<br>
            <b>Observed:</b> {observed_count}<br>
            <b>Interpolated:</b> {interpolated_count}
        </p>
    </div>
    '''

    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def main():
    """Generate QA/QC visualization."""
    print("=" * 60)
    print("QA/QC Wind-Radii Quadrilateral Visualization")
    print("=" * 60)

    m = create_qaqc_map(storm_id='AL092021', interval_minutes=15)

    output_path = REPO_ROOT / "integration/outputs/qaqc_wind_radii_map.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))

    print("\n" + "=" * 60)
    print(f"✅ QA/QC map saved to: {output_path}")
    print("=" * 60)
    print("\nVisualization includes:")
    print("  • Observed wind-radii quadrilaterals (solid)")
    print("  • Interpolated wind-radii quadrilaterals (dashed)")
    print("  • Tract centroids colored by duration (RED = 0 hrs)")
    print("  • Storm envelope and track centerline")
    print("\nUse layer control to toggle different elements")
    print("Hover over elements for detailed information")
    print("=" * 60)


if __name__ == "__main__":
    main()
