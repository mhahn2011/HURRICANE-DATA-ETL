"""QA/QC visualization for wind-radii wind fields and duration values.

This script creates an interactive Folium map showing:
1. All wind-radii polygons (observed and interpolated at 15-min intervals)
2. Tract centroids color-coded by duration values
3. Visual inspection tools for debugging duration calculation issues
"""

import sys
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
import folium
from shapely.geometry import Polygon

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(REPO_ROOT / "hurdat2" / "src"),
    str(REPO_ROOT / "census" / "src"),
    str(REPO_ROOT / "integration" / "src"),
    str(REPO_ROOT / "hurdat2_census" / "src"),
])

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope, impute_missing_wind_radii
from duration_calculator import interpolate_track_temporal, create_instantaneous_wind_polygon


def plot_quadrilateral(
    m: folium.Map,
    polygon: Polygon,
    timestamp: pd.Timestamp,
    is_interpolated: bool,
    has_wind_radii: bool,
    is_imputed: bool,
    layer_group: folium.FeatureGroup,
    radii: Dict[str, Optional[float]],
) -> None:
    """Add a single wind-radii polygon to the map with wide tooltip."""

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

    def _format_radius(value: Optional[float]) -> str:
        return f"{value:.0f} nm" if pd.notna(value) else "N/A"

    radii_type = 'IMPUTED (Proportional)' if is_imputed else ('Interpolated (15-min)' if is_interpolated else 'Observed (6-hr)')
    tooltip_html = f"""
    <div style="min-width: 320px;">
        <b>Time:</b> {timestamp.strftime('%Y-%m-%d %H:%M UTC')}<br>
        <b>Wind Field Type:</b> {radii_type}<br>
        <b>Geometry:</b> Arc-based radial envelope<br>
        <b>64kt Wind Radii:</b><br>
        &nbsp;&nbsp;NE: {_format_radius(radii.get('ne'))}<br>
        &nbsp;&nbsp;SE: {_format_radius(radii.get('se'))}<br>
        &nbsp;&nbsp;SW: {_format_radius(radii.get('sw'))}<br>
        &nbsp;&nbsp;NW: {_format_radius(radii.get('nw'))}
    </div>
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
        tooltip=folium.Tooltip(tooltip_html, sticky=True, style="min-width: 320px;"),
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
    observed_layer = folium.FeatureGroup(name='Observed Wind Field (Arc-Based)', show=True)
    imputed_layer = folium.FeatureGroup(name='Imputed Wind Field (Arc-Based)', show=True)
    interpolated_layer = folium.FeatureGroup(name='Interpolated Wind Field (Arc-Based)', show=True)

    # Plot all quadrilaterals
    print("Plotting wind-radii polygons...")
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
                radii={
                    'ne': row['wind_radii_64_ne'],
                    'se': row['wind_radii_64_se'],
                    'sw': row['wind_radii_64_sw'],
                    'nw': row['wind_radii_64_nw'],
                },
            )

            quadrilateral_count += 1

    observed_layer.add_to(m)
    imputed_layer.add_to(m)
    interpolated_layer.add_to(m)

    print(f"Plotted {quadrilateral_count} wind fields:")
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

    # Load tract features to show duration values (from wind coverage envelope)
    print("Loading tract features...")
    features_path = REPO_ROOT / "integration/outputs/ida_features_final.csv"
    if not features_path.exists():
        # Fallback to older version if final doesn't exist
        features_path = REPO_ROOT / "integration/outputs/ida_features_complete_v2.csv"

    if features_path.exists():
        features = pd.read_csv(features_path)
        features['tract_geoid'] = features['tract_geoid'].astype(str)
        print(f"Loaded {len(features)} tract features from {features_path.name}")

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

    # Add legend (matching specification from WIND_FIELD_VISUALIZATION_IMPROVEMENTS.md)
    legend_html = f'''
    <div style="position: fixed;
        bottom: 50px; left: 50px; width: 250px;
        background-color: white; z-index:9999; font-size:14px;
        border:2px solid grey; border-radius: 5px; padding: 10px">

        <p style="margin: 0 0 10px 0; font-weight: bold;">Duration in 64kt Winds</p>

        <div style="background: linear-gradient(to right,
            rgb(0,0,255), rgb(0,255,255), rgb(0,255,0),
            rgb(255,255,0), rgb(255,0,0));
            height: 20px; margin-bottom: 5px;"></div>

        <div style="display: flex; justify-content: space-between; font-size: 11px;">
            <span>0 hrs</span>
            <span>2 hrs</span>
            <span>4 hrs</span>
            <span>6 hrs</span>
            <span>8+ hrs</span>
        </div>

        <p style="margin: 10px 0 5px 0; font-size: 12px;"><b>Wind Field Types:</b></p>
        <p style="margin: 3px 0;">
            <span style="color: blue; font-weight: bold;">━━━</span> Observed (6-hr data)
        </p>
        <p style="margin: 3px 0;">
            <span style="color: purple; font-weight: bold;">- - -</span> Interpolated (15-min)
        </p>
        <p style="margin: 3px 0;">
            <span style="color: orange; font-weight: bold;">· · ·</span> Imputed (estimated)
        </p>
    </div>
    '''

    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def main():
    """Generate QA/QC visualization."""
    print("=" * 60)
    print("QA/QC Wind Field Visualization (Arc Geometry)")
    print("=" * 60)

    m = create_qaqc_map(storm_id='AL092021', interval_minutes=15)

    output_path = REPO_ROOT / "integration/outputs/qaqc_wind_radii_map.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))

    print("\n" + "=" * 60)
    print(f"✅ QA/QC map saved to: {output_path}")
    print("=" * 60)
    print("\nVisualization includes:")
    print("  • Observed wind fields with arc-based geometry")
    print("  • Interpolated/imputed envelopes (dashed/dotted styling)")
    print("  • Tract centroids colored by duration (legend bottom-left)")
    print("  • Storm envelope and track centerline")
    print("\nUse layer control to toggle different elements")
    print("Hover over elements for detailed information")
    print("=" * 60)


if __name__ == "__main__":
    main()
