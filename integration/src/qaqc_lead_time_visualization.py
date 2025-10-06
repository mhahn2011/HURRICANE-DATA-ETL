"""QA/QC visualization for lead time features.

Creates interactive Folium heatmap showing warning times for different
hurricane categories across census tracts.
"""

import sys
from pathlib import Path
import pandas as pd
import folium
import numpy as np
from shapely.geometry import LineString

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(REPO_ROOT / "hurdat2" / "src"),
    str(REPO_ROOT / "integration" / "src"),
])

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data


def create_lead_time_qaqc(
    storm_id: str = 'AL092021',
    category: str = 'cat4'
) -> folium.Map:
    """Create QA/QC heatmap for lead time features.

    Args:
        storm_id: Storm ID (e.g., 'AL092021' for Ida)
        category: Category to visualize ('cat1', 'cat2', 'cat3', 'cat4', 'cat5')

    Returns:
        Folium map with lead time heatmap
    """

    # Load track data
    hurdat_path = REPO_ROOT / "hurdat2/input_data/hurdat2-atlantic.txt"
    storms = parse_hurdat2_file(hurdat_path)
    cleaned = clean_hurdat2_data(storms)
    track = cleaned[cleaned['storm_id'] == storm_id].sort_values('date').reset_index(drop=True)

    # Load feature data
    features_path = REPO_ROOT / "integration/outputs/ida_features_with_lead_time.csv"
    features = pd.read_csv(features_path)
    features['tract_geoid'] = features['tract_geoid'].astype(str)

    # Create map
    center_lat = track['lat'].mean()
    center_lon = track['lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=7)

    # Add track
    track_coords = [(row['lat'], row['lon']) for _, row in track.iterrows()]
    folium.PolyLine(
        locations=track_coords,
        color='red',
        weight=3,
        opacity=0.8,
        tooltip='Hurricane Track'
    ).add_to(m)

    # Lead time color scheme (hours) - green (long warning) to red (short warning)
    def get_lead_time_color(hours: float) -> str:
        if pd.isna(hours):
            return '#cccccc'  # Gray for None
        elif hours < 0:
            return '#000080'  # Dark blue for negative (intensified after passing)
        elif hours < 6:
            return '#8b0000'  # Dark red - very short warning
        elif hours < 12:
            return '#dc143c'  # Red
        elif hours < 24:
            return '#ff6347'  # Tomato
        elif hours < 36:
            return '#ffa500'  # Orange
        elif hours < 48:
            return '#ffd700'  # Gold
        elif hours < 60:
            return '#9acd32'  # Yellow-green
        else:
            return '#228b22'  # Forest green - long warning

    # Get lead time column
    lead_col = f'lead_time_{category}_hours'
    if lead_col not in features.columns:
        raise ValueError(f"Column {lead_col} not found in features")

    # Plot centroids
    non_null_count = features[lead_col].notna().sum()
    null_count = features[lead_col].isna().sum()

    for _, row in features.iterrows():
        lead_time = row[lead_col]
        color = get_lead_time_color(lead_time)

        if pd.isna(lead_time):
            tooltip_html = f"""
            <b>Storm never reached {category.upper()}</b><br>
            <b>Tract:</b> {row['tract_geoid']}<br>
            <b>Distance:</b> {row['distance_km']:.1f} km
            """
        else:
            tooltip_html = f"""
            <b>Lead Time ({category.upper()}):</b> {lead_time:.1f} hours<br>
            <b>Tract:</b> {row['tract_geoid']}<br>
            <b>Distance:</b> {row['distance_km']:.1f} km<br>
            <b>Max Wind:</b> {row['max_wind_experienced_kt']:.1f} kt
            """

        folium.CircleMarker(
            location=[row['centroid_lat'], row['centroid_lon']],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            tooltip=folium.Tooltip(tooltip_html, sticky=True),
        ).add_to(m)

    # Calculate statistics
    if non_null_count > 0:
        lead_values = features[lead_col].dropna()
        stats = {
            'mean': lead_values.mean(),
            'median': lead_values.median(),
            'min': lead_values.min(),
            'max': lead_values.max(),
        }
    else:
        stats = {'mean': 0, 'median': 0, 'min': 0, 'max': 0}

    # Category threshold info
    thresholds = {
        'cat1': '64kt (Hurricane)',
        'cat2': '83kt (Cat 2)',
        'cat3': '96kt (Major Hurricane)',
        'cat4': '113kt (Cat 4)',
        'cat5': '137kt (Cat 5)',
    }

    legend_html = f'''
    <div style="position: fixed; top: 10px; right: 10px; width: 280px;
                background-color: white; z-index:9999; font-size:11px;
                border:2px solid grey; border-radius: 5px; padding: 10px;">
        <p style="margin: 0 0 8px 0;"><b>QA/QC #4: Lead Time - {category.upper()}</b></p>
        <p style="margin: 0 0 8px 0; font-size:10px;"><i>Threshold: {thresholds[category]}</i></p>

        <p style="margin: 8px 0 4px 0;"><b>Warning Time (hours):</b></p>
        <p style="margin: 3px 0;"><i style="background: #228b22; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 60+ (Long warning)</p>
        <p style="margin: 3px 0;"><i style="background: #9acd32; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 48-60</p>
        <p style="margin: 3px 0;"><i style="background: #ffd700; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 36-48</p>
        <p style="margin: 3px 0;"><i style="background: #ffa500; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 24-36</p>
        <p style="margin: 3px 0;"><i style="background: #ff6347; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 12-24</p>
        <p style="margin: 3px 0;"><i style="background: #dc143c; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> 6-12</p>
        <p style="margin: 3px 0;"><i style="background: #8b0000; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> &lt; 6 (Short warning)</p>
        <p style="margin: 3px 0;"><i style="background: #000080; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> Negative (intensified after)</p>
        <p style="margin: 3px 0;"><i style="background: #cccccc; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> N/A (never reached)</p>

        <hr style="margin: 8px 0;">
        <p style="margin: 0; font-size: 10px;">
            <b>Statistics (hours):</b><br>
            Mean: {stats['mean']:.1f}<br>
            Median: {stats['median']:.1f}<br>
            Min: {stats['min']:.1f}<br>
            Max: {stats['max']:.1f}<br>
            <br>
            <b>Coverage:</b><br>
            With lead time: {non_null_count}<br>
            Never reached: {null_count}
        </p>
    </div>
    '''

    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def main():
    """Generate all lead time QA/QC visualizations."""

    print("=" * 70)
    print("LEAD TIME QA/QC VISUALIZATION SUITE")
    print("=" * 70)

    output_dir = REPO_ROOT / "integration/outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    categories = ['cat1', 'cat2', 'cat3', 'cat4', 'cat5']

    for i, cat in enumerate(categories, start=1):
        print(f"\n[{i}/5] Generating {cat.upper()} lead time visualization...")
        try:
            m = create_lead_time_qaqc(storm_id='AL092021', category=cat)
            path = output_dir / f"qaqc_04_lead_time_{cat}.html"
            m.save(str(path))
            print(f"  ✓ Saved: {path}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print("\n" + "=" * 70)
    print("LEAD TIME QA/QC SUITE COMPLETE")
    print("=" * 70)
    print("\nGenerated visualizations:")
    print("  • qaqc_04_lead_time_cat1.html - Category 1 (64kt) warning times")
    print("  • qaqc_04_lead_time_cat2.html - Category 2 (83kt) warning times")
    print("  • qaqc_04_lead_time_cat3.html - Category 3 (96kt) warning times")
    print("  • qaqc_04_lead_time_cat4.html - Category 4 (113kt) warning times")
    print("  • qaqc_04_lead_time_cat5.html - Category 5 (137kt) warning times")
    print("\nColor scheme: Green (long warning) → Red (short warning)")
    print("=" * 70)


if __name__ == "__main__":
    main()
