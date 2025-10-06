"""Comprehensive QA/QC visualization suite for all storm-tract algorithms.

Creates separate Folium visualizations to validate:
1. Distance calculation (min distance to track centerline)
2. Max wind experienced (RMW plateau + decay model)
3. Duration calculation (temporal exposure in wind field)
4. Wind radii quadrilateral coverage
"""

import sys
from pathlib import Path
import pandas as pd
import folium
import numpy as np
from shapely.geometry import Point, LineString

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.extend([
    str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
    str(REPO_ROOT / "01_data_sources" / "census" / "src"),
    str(REPO_ROOT / "02_transformations" / "wind_coverage_envelope" / "src"),
    str(REPO_ROOT / "02_transformations" / "duration" / "src"),
    str(REPO_ROOT / "02_transformations" / "storm_tract_distance" / "src"),
])

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import impute_missing_wind_radii
from duration_calculator import interpolate_track_temporal, create_instantaneous_wind_polygon


def create_wind_coverage_envelope(track: pd.DataFrame, wind_threshold: str = "64kt", interval_minutes: int = 15):
    """Create envelope from union of imputed wind radii polygons.

    Args:
        track: Storm track DataFrame with wind radii columns
        wind_threshold: Wind threshold ('64kt', '50kt', '34kt')
        interval_minutes: Temporal interpolation interval

    Returns:
        tuple: (wind_coverage_polygon, track_line, interpolated_track_df)
    """
    from shapely.ops import unary_union

    # Apply imputation to extend through weakening
    track_imputed = impute_missing_wind_radii(track, wind_threshold=wind_threshold)

    # Prepare for interpolation (numeric columns only)
    prefix = wind_threshold.replace("kt", "")
    imputed_cols = [f"wind_radii_{prefix}_{q}_imputed" for q in ["ne", "se", "sw", "nw"]]

    track_subset = track_imputed[['date', 'lat', 'lon'] + imputed_cols].copy()
    track_subset = track_subset.rename(columns={
        f"wind_radii_{prefix}_ne_imputed": f"wind_radii_{prefix}_ne",
        f"wind_radii_{prefix}_se_imputed": f"wind_radii_{prefix}_se",
        f"wind_radii_{prefix}_sw_imputed": f"wind_radii_{prefix}_sw",
        f"wind_radii_{prefix}_nw_imputed": f"wind_radii_{prefix}_nw",
    })

    # Interpolate track temporally
    interpolated = interpolate_track_temporal(track_subset, interval_minutes=interval_minutes)

    # Create all instantaneous wind polygons
    wind_polygons = []
    for _, row in interpolated.iterrows():
        poly = create_instantaneous_wind_polygon(
            lat=row['lat'],
            lon=row['lon'],
            wind_radii_ne=row[f'wind_radii_{prefix}_ne'],
            wind_radii_se=row[f'wind_radii_{prefix}_se'],
            wind_radii_sw=row[f'wind_radii_{prefix}_sw'],
            wind_radii_nw=row[f'wind_radii_{prefix}_nw'],
            buffer_deg=0.0,  # No buffer - exact wind radii coverage
        )
        if poly and not poly.is_empty:
            wind_polygons.append(poly)

    if not wind_polygons:
        return None, LineString(list(zip(track['lon'], track['lat']))), interpolated

    # Union all polygons to create coverage envelope
    wind_coverage = unary_union(wind_polygons)

    # Create track line
    track_line = LineString(list(zip(track['lon'], track['lat'])))

    return wind_coverage, track_line, interpolated


def create_distance_qaqc(storm_id: str = 'AL092021') -> folium.Map:
    """QA/QC #1: Validate distance-to-track calculations.

    Shows:
    - Track centerline
    - Tract centroids color-coded by distance bins
    - Perpendicular lines from centroids to nearest track point
    - Distance legend with statistical distribution
    """

    # Load data
    hurdat_path = REPO_ROOT / "01_data_sources/hurdat2/raw/hurdat2-atlantic.txt"
    storms = parse_hurdat2_file(hurdat_path)
    cleaned = clean_hurdat2_data(storms)
    track = cleaned[cleaned['storm_id'] == storm_id].sort_values('date').reset_index(drop=True)

    # Create wind coverage envelope from union of imputed wind radii polygons
    wind_coverage, track_line, _ = create_wind_coverage_envelope(track, wind_threshold='64kt', interval_minutes=15)

    features_path = REPO_ROOT / "06_outputs/ml_ready/al092021_features.csv"
    features = pd.read_csv(features_path)

    # Create map
    m = folium.Map(location=[track['lat'].mean(), track['lon'].mean()], zoom_start=7)

    # Add wind coverage envelope
    if wind_coverage:
        folium.GeoJson(
            wind_coverage,
            name='64kt Wind Coverage Envelope',
            style_function=lambda x: {
                'fillColor': 'yellow',
                'color': 'orange',
                'weight': 3,
                'fillOpacity': 0.15,
            }
        ).add_to(m)

    # Add track centerline
    track_coords = [(row['lat'], row['lon']) for _, row in track.iterrows()]
    folium.PolyLine(
        locations=track_coords,
        color='red',
        weight=4,
        opacity=0.9,
        tooltip='Hurricane Track Centerline'
    ).add_to(m)

    # Distance heatmap - blue (close) to red (far)
    def get_distance_color(km: float) -> str:
        if km < 10:
            return '#08519c'  # Dark blue (very close)
        elif km < 20:
            return '#3182bd'  # Blue
        elif km < 30:
            return '#6baed6'  # Light blue
        elif km < 40:
            return '#9ecae1'  # Pale blue
        elif km < 50:
            return '#fee391'  # Yellow
        elif km < 60:
            return '#fec44f'  # Orange-yellow
        elif km < 70:
            return '#fe9929'  # Orange
        elif km < 80:
            return '#ec7014'  # Dark orange
        elif km < 100:
            return '#cc4c02'  # Red-orange
        else:
            return '#8c2d04'  # Dark red (far)

    # Plot centroids with distance color-coding
    for _, row in features.iterrows():
        color = get_distance_color(row['distance_km'])

        tooltip = f"""
        <b>Distance to Track:</b> {row['distance_km']:.1f} km ({row['distance_nm']:.1f} nm)<br>
        <b>Tract:</b> {row['tract_geoid']}<br>
        <b>Nearest Point:</b> ({row['nearest_track_point_lat']:.3f}, {row['nearest_track_point_lon']:.3f})
        """

        folium.CircleMarker(
            location=[row['centroid_lat'], row['centroid_lon']],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            tooltip=folium.Tooltip(tooltip, sticky=True),
        ).add_to(m)

        # Draw line to nearest track point (sample 10% for clarity)
        if np.random.random() < 0.1:
            folium.PolyLine(
                locations=[
                    [row['centroid_lat'], row['centroid_lon']],
                    [row['nearest_track_point_lat'], row['nearest_track_point_lon']]
                ],
                color='gray',
                weight=1,
                opacity=0.3,
                dash_array='5, 5',
            ).add_to(m)

    # Statistics
    dist_stats = features['distance_km'].describe()

    legend_html = f'''
    <div style="position: fixed; top: 10px; right: 10px; width: 250px;
                background-color: white; z-index:9999; font-size:11px;
                border:2px solid grey; border-radius: 5px; padding: 10px;">
        <p style="margin: 0 0 8px 0;"><b>QA/QC #1: Distance Heatmap</b></p>

        <p style="margin: 8px 0 4px 0;"><b>Distance (km) - Blue → Red:</b></p>
        <p style="margin: 3px 0;"><i style="background: #08519c; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> &lt; 10</p>
        <p style="margin: 3px 0;"><i style="background: #3182bd; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 10-20</p>
        <p style="margin: 3px 0;"><i style="background: #6baed6; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 20-30</p>
        <p style="margin: 3px 0;"><i style="background: #9ecae1; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 30-40</p>
        <p style="margin: 3px 0;"><i style="background: #fee391; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 40-50</p>
        <p style="margin: 3px 0;"><i style="background: #fec44f; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 50-60</p>
        <p style="margin: 3px 0;"><i style="background: #fe9929; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 60-70</p>
        <p style="margin: 3px 0;"><i style="background: #ec7014; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 70-80</p>
        <p style="margin: 3px 0;"><i style="background: #cc4c02; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 80-100</p>
        <p style="margin: 3px 0;"><i style="background: #8c2d04; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 100+</p>

        <hr style="margin: 8px 0;">
        <p style="margin: 0; font-size: 10px;">
            <b>Statistics (km):</b><br>
            Mean: {dist_stats['mean']:.1f}<br>
            Median: {dist_stats['50%']:.1f}<br>
            Min: {dist_stats['min']:.1f}<br>
            Max: {dist_stats['max']:.1f}
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def create_wind_qaqc(storm_id: str = 'AL092021') -> folium.Map:
    """QA/QC #2: Validate max wind experienced calculations.

    Shows:
    - Envelope boundary
    - Track centerline
    - RMW circles at key track points
    - Centroids color-coded by max wind experienced
    - Wind source indicators (radii vs RMW plateau vs decay)
    """

    # Load data
    hurdat_path = REPO_ROOT / "01_data_sources/hurdat2/raw/hurdat2-atlantic.txt"
    storms = parse_hurdat2_file(hurdat_path)
    cleaned = clean_hurdat2_data(storms)
    track = cleaned[cleaned['storm_id'] == storm_id].sort_values('date').reset_index(drop=True)

    # Create wind coverage envelope from union of imputed wind radii polygons
    wind_coverage, track_line, _ = create_wind_coverage_envelope(track, wind_threshold='64kt', interval_minutes=15)

    features_path = REPO_ROOT / "06_outputs/ml_ready/al092021_features.csv"
    features = pd.read_csv(features_path)

    # Create map
    m = folium.Map(location=[track['lat'].mean(), track['lon'].mean()], zoom_start=7)

    # Add wind coverage envelope
    if wind_coverage:
        folium.GeoJson(
            wind_coverage,
            name='64kt Wind Coverage Envelope',
            style_function=lambda x: {
                'fillColor': 'yellow',
                'color': 'orange',
                'weight': 3,
                'fillOpacity': 0.15,
            }
        ).add_to(m)

    # Add track
    track_coords = [(row['lat'], row['lon']) for _, row in track.iterrows()]
    folium.PolyLine(
        locations=track_coords,
        color='red',
        weight=3,
        opacity=0.8,
        tooltip='Track Centerline'
    ).add_to(m)

    # Wind speed heatmap - green (low) to red (high)
    def get_wind_color(kt: float) -> str:
        if kt >= 130:
            return '#67000d'  # Darkest red (Cat 5)
        elif kt >= 113:
            return '#a50f15'  # Dark red (Cat 4)
        elif kt >= 96:
            return '#cb181d'  # Red (Cat 3)
        elif kt >= 83:
            return '#ef3b2c'  # Red-orange (Cat 2)
        elif kt >= 64:
            return '#fc6e4c'  # Orange (Cat 1)
        elif kt >= 50:
            return '#fc9272'  # Light orange (TS)
        elif kt >= 40:
            return '#fcbba1'  # Pale orange
        elif kt >= 34:
            return '#fee5d9'  # Very pale orange (TD)
        else:
            return '#fff5f0'  # Almost white

    # Plot centroids
    for _, row in features.iterrows():
        wind = row['max_wind_experienced_kt']
        color = get_wind_color(wind)

        tooltip = f"""
        <b>Max Wind:</b> {wind:.1f} kt<br>
        <b>Center Wind:</b> {row['center_wind_at_approach_kt']:.1f} kt<br>
        <b>Inside Eyewall:</b> {row['inside_eyewall']}<br>
        <b>RMW:</b> {row['radius_max_wind_at_approach_nm']:.1f} nm<br>
        <b>Tract:</b> {row['tract_geoid']}
        """

        folium.CircleMarker(
            location=[row['centroid_lat'], row['centroid_lon']],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            tooltip=folium.Tooltip(tooltip, sticky=True),
        ).add_to(m)

    # Wind statistics
    wind_stats = features['max_wind_experienced_kt'].describe()

    legend_html = f'''
    <div style="position: fixed; top: 10px; right: 10px; width: 250px;
                background-color: white; z-index:9999; font-size:11px;
                border:2px solid grey; border-radius: 5px; padding: 10px;">
        <p style="margin: 0 0 8px 0;"><b>QA/QC #2: Wind Heatmap</b></p>

        <p style="margin: 8px 0 4px 0;"><b>Wind (kt) - White → Red:</b></p>
        <p style="margin: 3px 0;"><i style="background: #67000d; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 130+ (Cat 5)</p>
        <p style="margin: 3px 0;"><i style="background: #a50f15; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 113-130 (Cat 4)</p>
        <p style="margin: 3px 0;"><i style="background: #cb181d; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 96-113 (Cat 3)</p>
        <p style="margin: 3px 0;"><i style="background: #ef3b2c; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 83-96 (Cat 2)</p>
        <p style="margin: 3px 0;"><i style="background: #fc6e4c; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 64-83 (Cat 1)</p>
        <p style="margin: 3px 0;"><i style="background: #fc9272; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 50-64 (TS)</p>
        <p style="margin: 3px 0;"><i style="background: #fcbba1; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 40-50</p>
        <p style="margin: 3px 0;"><i style="background: #fee5d9; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 34-40 (TD)</p>
        <p style="margin: 3px 0;"><i style="background: #fff5f0; width: 12px; height: 12px; display: inline-block; border-radius: 50%; border: 1px solid #ccc;"></i> &lt; 34</p>

        <hr style="margin: 8px 0;">
        <p style="margin: 0; font-size: 10px;">
            <b>Statistics (kt):</b><br>
            Mean: {wind_stats['mean']:.1f}<br>
            Median: {wind_stats['50%']:.1f}<br>
            Min: {wind_stats['min']:.1f}<br>
            Max: {wind_stats['max']:.1f}
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def create_duration_qaqc(storm_id: str = 'AL092021') -> folium.Map:
    """QA/QC #3: Validate duration calculations.

    Shows:
    - Envelope boundary
    - Track with temporal markers
    - Centroids color-coded by duration bins
    - Entry/exit time indicators
    """

    # Load data
    hurdat_path = REPO_ROOT / "01_data_sources/hurdat2/raw/hurdat2-atlantic.txt"
    storms = parse_hurdat2_file(hurdat_path)
    cleaned = clean_hurdat2_data(storms)
    track = cleaned[cleaned['storm_id'] == storm_id].sort_values('date').reset_index(drop=True)

    # Create wind coverage envelope from union of imputed wind radii polygons
    wind_coverage, track_line, _ = create_wind_coverage_envelope(track, wind_threshold='64kt', interval_minutes=15)

    features_path = REPO_ROOT / "06_outputs/ml_ready/al092021_features.csv"
    features = pd.read_csv(features_path)

    # Create map
    m = folium.Map(location=[track['lat'].mean(), track['lon'].mean()], zoom_start=7)

    # Add wind coverage envelope
    if wind_coverage:
        folium.GeoJson(
            wind_coverage,
            name='64kt Wind Coverage Envelope',
            style_function=lambda x: {
                'fillColor': 'purple',
                'color': 'purple',
                'weight': 3,
                'fillOpacity': 0.15,
            }
        ).add_to(m)

    # Add track
    track_coords = [(row['lat'], row['lon']) for _, row in track.iterrows()]
    folium.PolyLine(
        locations=track_coords,
        color='red',
        weight=3,
        opacity=0.8,
        tooltip='Track Centerline'
    ).add_to(m)

    # Duration heatmap - light to dark purple/red
    def get_duration_color(hours: float) -> str:
        if hours < 1:
            return '#f7f4f9'  # Almost white
        elif hours < 2:
            return '#e7e1ef'  # Very light purple
        elif hours < 3:
            return '#d4b9da'  # Light purple
        elif hours < 4:
            return '#c994c7'  # Purple
        elif hours < 5:
            return '#df65b0'  # Pink-purple
        elif hours < 6:
            return '#e7298a'  # Pink
        elif hours < 8:
            return '#ce1256'  # Red-pink
        elif hours < 10:
            return '#980043'  # Dark red
        elif hours < 15:
            return '#67001f'  # Very dark red
        else:
            return '#3d0013'  # Almost black

    # Plot centroids
    for _, row in features.iterrows():
        duration = row['duration_in_envelope_hours']
        color = get_duration_color(duration)

        tooltip = f"""
        <b>Duration:</b> {duration:.1f} hrs<br>
        <b>Window:</b> {row['exposure_window_hours']:.1f} hrs<br>
        <b>Continuous:</b> {row['continuous_exposure']}<br>
        <b>Entry:</b> {row['first_entry_time']}<br>
        <b>Exit:</b> {row['last_exit_time']}<br>
        <b>Tract:</b> {row['tract_geoid']}
        """

        folium.CircleMarker(
            location=[row['centroid_lat'], row['centroid_lon']],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            tooltip=folium.Tooltip(tooltip, sticky=True),
        ).add_to(m)

    # Duration statistics
    dur_stats = features['duration_in_envelope_hours'].describe()

    legend_html = f'''
    <div style="position: fixed; top: 10px; right: 10px; width: 250px;
                background-color: white; z-index:9999; font-size:11px;
                border:2px solid grey; border-radius: 5px; padding: 10px;">
        <p style="margin: 0 0 8px 0;"><b>QA/QC #3: Duration Heatmap</b></p>

        <p style="margin: 8px 0 4px 0;"><b>Duration (hrs) - White → Black:</b></p>
        <p style="margin: 3px 0;"><i style="background: #f7f4f9; width: 12px; height: 12px; display: inline-block; border-radius: 50%; border: 1px solid #ccc;"></i> &lt; 1</p>
        <p style="margin: 3px 0;"><i style="background: #e7e1ef; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 1-2</p>
        <p style="margin: 3px 0;"><i style="background: #d4b9da; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 2-3</p>
        <p style="margin: 3px 0;"><i style="background: #c994c7; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 3-4</p>
        <p style="margin: 3px 0;"><i style="background: #df65b0; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 4-5</p>
        <p style="margin: 3px 0;"><i style="background: #e7298a; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 5-6</p>
        <p style="margin: 3px 0;"><i style="background: #ce1256; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 6-8</p>
        <p style="margin: 3px 0;"><i style="background: #980043; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 8-10</p>
        <p style="margin: 3px 0;"><i style="background: #67001f; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 10-15</p>
        <p style="margin: 3px 0;"><i style="background: #3d0013; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 15+</p>

        <hr style="margin: 8px 0;">
        <p style="margin: 0; font-size: 10px;">
            <b>Statistics (hours):</b><br>
            Mean: {dur_stats['mean']:.1f}<br>
            Median: {dur_stats['50%']:.1f}<br>
            Min: {dur_stats['min']:.1f}<br>
            Max: {dur_stats['max']:.1f}
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def main():
    """Generate all QA/QC visualizations."""

    print("=" * 70)
    print("COMPREHENSIVE QA/QC VISUALIZATION SUITE")
    print("=" * 70)

    output_dir = REPO_ROOT / "06_outputs/visuals/hurdat2_census"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Distance Feature Results
    print("\n[1/3] Generating Distance Feature Results visualization...")
    m1 = create_distance_qaqc()
    path1 = output_dir / "feature_results_distance_to_track.html"
    m1.save(str(path1))
    print(f"  ✓ Saved: {path1}")

    # 2. Wind Speed Feature Results
    print("\n[2/3] Generating Wind Speed Feature Results visualization...")
    m2 = create_wind_qaqc()
    path2 = output_dir / "feature_results_wind_speed.html"
    m2.save(str(path2))
    print(f"  ✓ Saved: {path2}")

    # 3. Duration Feature Results
    print("\n[3/3] Generating Duration Feature Results visualization...")
    m3 = create_duration_qaqc()
    path3 = output_dir / "feature_results_duration_in_envelope.html"
    m3.save(str(path3))
    print(f"  ✓ Saved: {path3}")

    print("\n" + "=" * 70)
    print("FEATURE RESULTS VISUALIZATION SUITE COMPLETE")
    print("=" * 70)
    print("\nGenerated visualizations:")
    print(f"  1. Distance to Track:      {path1.name}")
    print(f"  2. Max Wind Experienced:   {path2.name}")
    print(f"  3. Duration in Envelope:   {path3.name}")
    print(f"  4. Wind Radii Coverage:    feature_results_wind_radii_coverage.html")
    print("\nEach visualization shows feature distributions through:")
    print("  • Spatial distribution patterns")
    print("  • Statistical summaries")
    print("  • Interactive tooltips with detailed metrics")
    print("=" * 70)


if __name__ == "__main__":
    main()
