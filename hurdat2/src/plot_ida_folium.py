import sys
from pathlib import Path
import pandas as pd
import folium

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(REPO_ROOT / "hurdat2" / "src"),
    str(REPO_ROOT / "census" / "src"),
])

from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data
from envelope_algorithm import create_storm_envelope
from tract_centroids import load_tracts_with_centroids

def main():
    print("Creating Interactive Folium Map with Census Tracts")

    # Load features from wind coverage envelope (new accurate method)
    features_path = REPO_ROOT / "integration/outputs/ida_features_final.csv"
    if not features_path.exists():
        print(f"⚠️  {features_path} not found, using fallback")
        features_path = REPO_ROOT / "integration/outputs/ida_features_complete.csv"

    viz_data = pd.read_csv(features_path)
    viz_data['tract_geoid'] = viz_data['tract_geoid'].astype(str)
    print(f"Loaded {len(viz_data)} tracts with wind coverage envelope filtering")

    # 5. Load Ida track and envelope
    hurdat_path = REPO_ROOT / "hurdat2/input_data/hurdat2-atlantic.txt"
    storms = parse_hurdat2_file(hurdat_path)
    cleaned = clean_hurdat2_data(storms)
    ida_track = cleaned[
        (cleaned['storm_id'] == 'AL092021') &
        (cleaned['storm_name'] == 'IDA')
    ].copy()

    envelope_geom, track_line, _ = create_storm_envelope(
        ida_track, wind_threshold='64kt', alpha=0.6, verbose=False
    )

    # 6. Create Folium map
    m = folium.Map(location=[29.5, -90.5], zoom_start=7)

    # Add envelope
    if envelope_geom:
        folium.GeoJson(
            envelope_geom,
            name='Storm Envelope (64kt winds)',
            style_function=lambda x: {
                'fillColor': 'blue',
                'color': 'blue',
                'weight': 2,
                'fillOpacity': 0.2
            }
        ).add_to(m)

    # Add track
    if track_line:
        folium.PolyLine(
            locations=[(y, x) for x, y in track_line.coords],
            color='red',
            weight=3,
            opacity=0.8,
            tooltip='Hurricane Ida Track'
        ).add_to(m)

    # Add tract centroids with tooltips and popups
    tracts_layer = folium.FeatureGroup(name='Census Tract Centroids (456 affected)')

    for idx, row in viz_data.iterrows():
        # Tooltip (hover) - NOW WITH FEATURES
        tooltip_html = f"""
        <b>Tract:</b> {row['tract_geoid']}<br>
        <b>Distance:</b> {row['distance_km']:.1f} km<br>
        <b>Max Wind:</b> {row['max_wind_experienced_kt']:.1f} kt<br>
        <b>Duration:</b> {row['duration_in_envelope_hours']:.1f} hrs
        """

        # Popup (click) - FULL DETAILS
        popup_html = f"""
        <div style="font-family: Arial; font-size: 12px;">
            <b>Tract GEOID:</b> {row['tract_geoid']}<br>
            <b>State:</b> {row['STATEFP']}<br>
            <b>County:</b> {row['COUNTYFP']}<br>
            <hr>
            <b>── Exposure Metrics ──</b><br>
            <b>Distance to Track:</b> {row['distance_km']:.2f} km<br>
            <b>Max Wind Experienced:</b> {row['max_wind_experienced_kt']:.1f} kt<br>
            <b>Duration in Envelope:</b> {row['duration_in_envelope_hours']:.1f} hours<br>
            <b>First Entry:</b> {row['first_entry_time']}<br>
            <b>Last Exit:</b> {row['last_exit_time']}<br>
            <hr>
            <b>── Location ──</b><br>
            <b>Coordinates:</b> ({row['centroid_lat']:.4f}, {row['centroid_lon']:.4f})
        </div>
        """

        # Color by distance - NEW 10km increments
        dist_km = row['distance_km']
        if dist_km < 10:
            color = 'red'
        elif dist_km < 20:
            color = 'orange'
        elif dist_km < 30:
            color = 'yellow'
        elif dist_km < 40:
            color = 'lightgreen'
        elif dist_km < 50:
            color = 'blue'
        else:
            color = 'gray'

        folium.CircleMarker(
            location=[row['centroid_lat'], row['centroid_lon']],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            tooltip=folium.Tooltip(tooltip_html, sticky=True),  # ← Changed to Tooltip object
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(tracts_layer)

    tracts_layer.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # ADD LEGEND (after layer control)
    legend_html = '''
    <div style="position: fixed; 
        top: 10px; right: 10px; width: 200px;
        background-color: white; z-index:9999; font-size:12px;
        border:2px solid grey; border-radius: 5px; padding: 10px">
    
        <p style="margin: 0 0 8px 0;"><b>Distance to Track</b></p>
        <p style="margin: 3px 0;">
            <i style="background: red; width: 12px; height: 12px;
               display: inline-block; border-radius: 50%;"></i>
            0-10 km
        </p>
        <p style="margin: 3px 0;">
            <i style="background: orange; width: 12px; height: 12px;
               display: inline-block; border-radius: 50%;"></i>
            10-20 km
        </p>
        <p style="margin: 3px 0;">
            <i style="background: yellow; width: 12px; height: 12px;
               display: inline-block; border-radius: 50%;"></i>
            20-30 km
        </p>
        <p style="margin: 3px 0;">
            <i style="background: lightgreen; width: 12px; height: 12px;
               display: inline-block; border-radius: 50%;"></i>
            30-40 km
        </p>
        <p style="margin: 3px 0;">
            <i style="background: blue; width: 12px; height: 12px;
               display: inline-block; border-radius: 50%;"></i>
            40-50 km
        </p>
        <p style="margin: 3px 0;">
            <i style="background: gray; width: 12px; height: 12px;
               display: inline-block; border-radius: 50%;"></i>
            &gt; 50 km
        </p>
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(legend_html))

    # Save
    output_path = REPO_ROOT / "integration/outputs/ida_interactive_map.html"
    m.save(str(output_path))
    print(f"✅ Map saved to {output_path}")
    print(f"   - Envelope: blue polygon")
    print(f"   - Track: red line")
    print(f"   - Tracts: {len(viz_data)} colored dots")
    print(f"   - Hover over dots to see tract ID")
    print(f"   - Click dots for detailed info")

if __name__ == "__main__":
    main()