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

    # 1. Load 456 tracts within envelope
    tract_pairs = pd.read_csv(REPO_ROOT / "hurdat2/outputs/ida_tract_pairs.csv")
    tract_pairs['tract_geoid'] = tract_pairs['tract_geoid'].astype(str)
    envelope_geoids = tract_pairs['tract_geoid'].tolist()
    print(f"Loaded {len(envelope_geoids)} tracts within envelope")

    # 2. Load features for these tracts
    all_features = pd.read_csv(REPO_ROOT / "integration/outputs/ida_gulf_features.csv")
    all_features['tract_geoid'] = all_features['tract_geoid'].astype(str)
    envelope_features = all_features[
        all_features['tract_geoid'].isin(envelope_geoids)
    ].copy()
    print(f"Filtered to {len(envelope_features)} tracts with features")

    # 3. Load census tract centroids
    tract_data = load_tracts_with_centroids(
        year=2019,
        states=['22', '28', '48', '01', '12'],
        columns=['GEOID', 'STATEFP', 'COUNTYFP']
    )
    tract_data.centroids['GEOID'] = tract_data.centroids['GEOID'].astype(str)
    envelope_centroids = tract_data.centroids[
        tract_data.centroids['GEOID'].isin(envelope_geoids)
    ].copy()
    envelope_centroids['centroid_lat'] = envelope_centroids.geometry.y
    envelope_centroids['centroid_lon'] = envelope_centroids.geometry.x

    # 4. Merge features + coordinates
    viz_data = envelope_features.merge(
        envelope_centroids[['GEOID', 'STATEFP', 'COUNTYFP', 'centroid_lat', 'centroid_lon']],
        left_on='tract_geoid',
        right_on='GEOID',
        how='inner'
    )
    print(f"Final data: {len(viz_data)} tracts ready for mapping")

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
        <b>Max Wind:</b> {row['max_wind_experienced_kt']:.1f} kt
        """
    
        # Popup (click) - FULL DETAILS
        popup_html = f"""
        <div style="font-family: Arial; font-size: 12px;">
            <b>Tract GEOID:</b> {row['tract_geoid']}<br>
            <b>State:</b> {row['STATEFP']}<br>
            <b>County:</b> {row['COUNTYFP']}<br>
            <hr>
            <b>Distance to Track:</b> {row['distance_km']:.2f} km<br>
            <b>Max Wind Experienced:</b> {row['max_wind_experienced_kt']:.1f} kt<br>
            <hr>
            <b>Coordinates:</b> ({row['centroid_lat']:.4f}, {row['centroid_lon']:.4f})
        </div>
        """
    
        # Color by distance (same as before)
        if row['distance_km'] < 50:
            color = 'red'
        elif row['distance_km'] < 100:
            color = 'orange'
        elif row['distance_km'] < 150:
            color = 'yellow'
        else:
            color = 'green'
    
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
        top: 10px; right: 10px; width: 180px; height: auto;
        background-color: white; z-index:9999; font-size:12px;
        border:2px solid grey; border-radius: 5px; padding: 10px">
    
        <p style="margin-bottom: 5px;"><b>Distance to Track</b></p>
        <p style="margin-bottom: 3px;">
            <i style="background: red; width: 12px; height: 12px;
               display: inline-block; border-radius: 50%; margin-right: 5px;"></i>
            &lt; 50 km
        </p>
        <p style="margin-bottom: 3px;">
            <i style="background: orange; width: 12px; height: 12px;
               display: inline-block; border-radius: 50%; margin-right: 5px;"></i>
            50-100 km
        </p>
        <p style="margin-bottom: 3px;">
            <i style="background: yellow; width: 12px; height: 12px;
               display: inline-block; border-radius: 50%; margin-right: 5px;"></i>
            100-150 km
        </p>
        <p style="margin-bottom: 3px;">
            <i style="background: green; width: 12px; height: 12px;
               display: inline-block; border-radius: 50%; margin-right: 5px;"></i>
            &gt; 150 km
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
