# Next Steps for Gemini: Enhance Folium Map with Features & Legend

## Current Status

**✅ Working correctly:**
- Map displays envelope and track ✅
- Map displays 456 census tract centroids ✅
- Hover tooltips show tract GEOID ✅
- Click popups show detailed information ✅
- Spatial join is accurate (QAQC passed)

**❌ Missing/Issues:**
- Hover tooltips only show tract GEOID - need to add **distance and max wind features**
- No legend explaining the color coding
- Colors appear but user doesn't know what they mean

---

## Required Updates

### Update 1: Enhance Hover Tooltips with Features

**Current behavior**: Hover shows only `Tract: 22071001747`

**Required behavior**: Hover should show:
```
Tract: 22071001747
Distance: 73.2 km
Max Wind: 64.5 kt
```

**Implementation**:
```python
# In the loop where CircleMarkers are created:
tooltip_text = f"""
<b>Tract:</b> {row['tract_geoid']}<br>
<b>Distance:</b> {row['distance_to_track_km']:.1f} km<br>
<b>Max Wind:</b> {row['max_wind_experienced_kt']:.1f} kt
"""

folium.CircleMarker(
    location=[row['centroid_lat'], row['centroid_lon']],
    radius=4,
    tooltip=folium.Tooltip(tooltip_text, sticky=True),  # Use Tooltip object for HTML
    popup=folium.Popup(popup_html, max_width=300),
    ...
)
```

**Note**: Use `folium.Tooltip(tooltip_text, sticky=True)` instead of just passing the string directly to enable HTML formatting in hover tooltips.

---

### Update 2: Add Interactive Legend

**Required**: Add a color legend showing what each color means

**Method 1: HTML Legend Box (Recommended)**

Add a custom HTML legend in the top-right corner:

```python
# After creating the map, before adding layers:

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
```

**Alternative Method 2: Folium Branca ColorMap**

If you prefer a gradient legend instead:

```python
import branca.colormap as cm

# Create colormap
colormap = cm.LinearColormap(
    colors=['red', 'orange', 'yellow', 'green'],
    vmin=0,
    vmax=200,
    caption='Distance to Storm Track (km)'
)

# Add to map
colormap.add_to(m)
```

---

## Complete Updated Script

Replace the tract centroid loop in `plot_ida_folium.py` with this:

```python
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
```

---

## Data Source

The features are already in the visualization data:
- **File**: `integration/outputs/ida_visualization_data.csv`
- **Columns available**:
  - `tract_geoid` - Census tract ID
  - `distance_to_track_km` - Distance in km (ready to use)
  - `max_wind_experienced_kt` - Max wind in knots (ready to use)
  - `centroid_lat`, `centroid_lon` - Coordinates
  - `STATEFP`, `COUNTYFP` - State/County codes

**Important**: The file was recently updated by Gemini and now has 456 rows of data (confirmed from system reminder).

---

## Expected Output

After implementing these changes:

### Hover Behavior (Mouse-over, no click):
```
Tract: 22071001747
Distance: 73.2 km
Max Wind: 64.0 kt
```

### Click Popup (Full details):
```
Tract GEOID: 22071001747
State: 22
County: 071
─────────────────────
Distance to Track: 73.23 km
Max Wind Experienced: 64.0 kt
─────────────────────
Coordinates: (30.0401, -89.9539)
```

### Legend (Top-right corner):
```
┌──────────────────────┐
│ Distance to Track    │
│ ● < 50 km    (red)   │
│ ● 50-100 km  (orange)│
│ ● 100-150 km (yellow)│
│ ● > 150 km   (green) │
└──────────────────────┘
```

---

## Testing

After running the updated script:

1. **Open the map**: `open integration/outputs/ida_interactive_map.html`
2. **Test hover**: Move mouse over colored dots - should show tract ID, distance, and max wind
3. **Test click**: Click dots - should show full popup with all details
4. **Check legend**: Top-right corner should show color meanings
5. **Verify data**: Hover values should match the CSV data

---

## Summary of Changes

1. ✅ **Tooltip enhancement**: Change from simple string to `folium.Tooltip()` with HTML
2. ✅ **Add distance feature**: Include `distance_km` in hover tooltip
3. ✅ **Add wind feature**: Include `max_wind_experienced_kt` in hover tooltip
4. ✅ **Add legend**: HTML legend box in top-right showing color meanings
5. ✅ **Keep existing popup**: Full details remain on click

**Files to modify**: Only `integration/src/plot_ida_folium.py`

**No data changes needed**: The visualization CSV already has all required features
