# HURDAT2 to ML Features Workflow - MVP

## Overview

Transform HURDAT2 raw format → Storm-Tract feature matrix using Perpendicular Distance Envelope Approach

**Input**: Raw HURDAT2 text file (mixed header/data format)
**Output**: CSV where each row = one storm's impact on one census tract
**Key Innovation**: Perpendicular distance envelope polygon for efficient wind field modeling

---

## ✅ Implementation Status

### Completed:
- ✅ Parse Raw HURDAT2 → Flat Table (`parse_raw.py`, `profile_clean.py`)
- ✅ Perpendicular Distance Envelope Algorithm (`envelope_algorithm.py`)
- ✅ Envelope Visualization with geographic context (`visualize_envelope.py`)
- ✅ Testing Infrastructure (pytest with envelope validity tests)

### Key Files:
- `hurdat2/src/envelope_algorithm.py` - Core envelope creation algorithm
- `hurdat2/src/parse_raw.py` - HURDAT2 parser
- `hurdat2/src/profile_clean.py` - Data cleaning
- `hurdat2/notebooks/hurdat2_to_features.ipynb` - Analysis notebook
- `tests/test_envelope_validity.py` - Test framework

---

## Step 1: Parse Raw HURDAT2 → Flat Table ✅ COMPLETE

### 1.1 Read & Restructure Format
```python
# Input: Mixed header/data lines
AL092021, IDA, 40,
20210829, 1655, L, HU, 29.1N, 90.2W, 130, 931, ...

# Output: Flat table with storm metadata
storm_id | storm_name | year | date | time | lat | lon | max_wind | wind_radii_64_ne | wind_radii_64_se | wind_radii_64_sw | wind_radii_64_nw | ... 
AL092021 | IDA        | 2021 | 20210829 | 1655 | 29.1 | -90.2 | 130 | 45 | 35 | 20 | 30 | ...
```

### 1.2 Data Cleaning
- Convert coordinates to decimal degrees
- Handle missing values (-999 → NaN)
- Parse date/time to datetime objects
- Filter for Gulf Coast relevance (lat: 25-32°N, lon: 80-98°W)
- **Focus on 64kt wind radii** for envelope creation

### 1.3 Feature Selection
**Essential Fields**:
- Storm metadata: storm_id, storm_name, year
- Position: date, time, latitude, longitude  
- Intensity: max_wind, min_pressure
- **Wind field: wind_radii_64_ne, wind_radii_64_se, wind_radii_64_sw, wind_radii_64_nw** ⭐
- Event markers: record_id (landfall = 'L'), status

**Output**: `clean_storm_tracks.csv`

---

## Step 2: Load Census Tract Geography

### 2.1 Census Tract Centroids
```python
import geopandas as gpd
# Load Gulf Coast census tracts with centroids
tracts = gpd.read_file("census_tracts_gulf_coast.shp")
tract_centroids = tracts.centroid
```

### 2.2 Spatial Filtering
- **Target Region**: Gulf Coast states (TX, LA, MS, AL, FL panhandle)
- **Coastal Focus**: Tracts within 200km of Gulf coastline
- **Extract centroids**: Lat/lon coordinates for each tract

**Output**: `gulf_coast_tract_centroids.csv`

---

## Step 3: Max Distance Envelope Approach ⭐ **CORE METHODOLOGY**

### 3.1 Create Storm Path Polylines
```python
def create_storm_path(storm_track_df):
    # Group by storm_id and sort by datetime
    storm_tracks = {}
    for storm_id, group in storm_track_df.groupby('storm_id'):
        sorted_track = group.sort_values('datetime')
        # Create polyline from consecutive track points
        path_coordinates = list(zip(sorted_track['longitude'], sorted_track['latitude']))
        storm_tracks[storm_id] = LineString(path_coordinates)
    return storm_tracks
```

### 3.2 Calculate Wind Extent Points
```python
def get_wind_extent_points(track_point):
    """Convert 4-directional wind radii to actual lat/lon coordinates"""
    lat, lon = track_point['latitude'], track_point['longitude']
    
    # Convert nautical miles to degrees (approximate)
    nm_to_deg = 1.0 / 60.0
    
    extent_points = {
        'NE': calculate_destination(lat, lon, 45, track_point['wind_radii_64_ne'] * nm_to_deg),
        'SE': calculate_destination(lat, lon, 135, track_point['wind_radii_64_se'] * nm_to_deg),
        'SW': calculate_destination(lat, lon, 225, track_point['wind_radii_64_sw'] * nm_to_deg),
        'NW': calculate_destination(lat, lon, 315, track_point['wind_radii_64_nw'] * nm_to_deg)
    }
    return extent_points
```

### 3.3 Find Maximum Perpendicular Distances
```python
def find_envelope_boundaries(storm_track):
    left_boundary_points = []
    right_boundary_points = []
    
    for i, track_point in storm_track.iterrows():
        extent_points = get_wind_extent_points(track_point)
        
        # Calculate perpendicular distances from storm path
        # Determine which points are on left vs right side of path
        # Find maximum extent on each side
        
        left_max_point = find_max_perpendicular_distance(extent_points, 'left')
        right_max_point = find_max_perpendicular_distance(extent_points, 'right')
        
        left_boundary_points.append(left_max_point)
        right_boundary_points.append(right_max_point)
    
    return left_boundary_points, right_boundary_points
```

### 3.4 Create Storm Corridor Polygon
```python
def create_storm_envelope(storm_track):
    left_boundary, right_boundary = find_envelope_boundaries(storm_track)
    
    # Create polygon from boundaries + path endpoints
    polygon_coords = (
        left_boundary + 
        [storm_track.iloc[-1][['longitude', 'latitude']].values] +  # End point
        list(reversed(right_boundary)) +
        [storm_track.iloc[0][['longitude', 'latitude']].values]     # Start point
    )
    
    return Polygon(polygon_coords)
```

---

## Step 4: Identify Tracts Within Envelope

Create storm-tract lookup table by testing which census tract centroids fall within the storm envelope polygon.

**Output**: Table with (storm_id, tract_id) pairs

---

## Concave Hull + Centroid Analysis Intention

**Project intention**: Combine storm-path geometries into a concave-hull polygon, determine which census-tract centroids fall inside, compute their distance to the storm path, and deliver the results via an interactive Folium map (zoom, layer toggles, centroid metadata).

**Planned steps**:
1. **Build the concave hull** – Generate the hull with shapely/alphashape and store it in a GeoPandas GeoDataFrame.
2. **Prepare track centroids** – Compute tract centroids, keep identifying attributes, and persist them in a GeoDataFrame.
3. **Spatial query** – Spatially join centroids and hull to flag points that lie inside.
4. **Distance calculation** – For inside centroids, compute shapely distance to the storm path and append the value to the GeoDataFrame.
5. **Visualization with Folium** – Render hull, storm path, and centroids as interactive layers with popups showing tract name and distance, enabling pan/zoom exploration.

This adds an exploratory layer on top of the analytical pipeline, marrying GeoPandas/shapely workflows with Folium’s interactivity.

---

## Step 5: MVP Feature Extraction

Extract core features for each storm-tract combination. Focus on essential metrics only.

### 5.1 Distance from Storm Path
Calculate shortest perpendicular distance from tract centroid to storm track.

**Method**: Use Shapely's `distance()` between point and LineString

### 5.2 Maximum Wind Speed Experienced
Calculate peak wind speed at tract location using linear interpolation.

**Method**:
- Find closest point on storm track to tract centroid
- Linear interpolation: `max_wind` (at track center) → 64 knots (at envelope boundary)

### 5.3 Duration of Wind Exposure
Calculate time tract experienced winds above threshold.

**Options**:
1. Duration at peak wind speed experienced
2. Duration at 64kt threshold (minimum hurricane force)

**Decision needed**: Which threshold to use for MVP

### 5.4 Category 4 Lead Time
Calculate preparation time before experiencing maximum winds.

**Method**:
1. Find point in storm track where winds first reach Cat 4 (113 kt)
2. Find time when tract experienced its maximum wind speed
3. Lead time = `time_at_tract_max_wind - time_at_cat4_threshold`

**Note**: Negative values indicate tract experienced max winds before storm reached Cat 4

---

## Step 6: Output Feature Matrix

### 6.1 MVP Schema

Each row: **One storm's impact on one census tract**

| Column | Description | Units |
|--------|-------------|-------|
| `tract_id` | Census tract FIPS code | - |
| `storm_id` | HURDAT2 storm identifier | - |
| `distance_to_track` | Shortest distance to storm path | km |
| `max_wind_experienced` | Peak wind speed at tract | knots |
| `duration_wind_exposure` | Time above wind threshold | hours |
| `cat4_lead_time` | Preparation time before max winds | hours |

**Final Output**: `storm_tract_features_mvp.csv`

---

## MVP Implementation Notes

### Focus Areas
1. Envelope creation (completed)
2. Storm-tract spatial join
3. Four core features only

### Deferred for Post-MVP
- Intensification rate (alternative to Cat 4 lead time)
- Storm forward speed
- Approach bearing
- Asymmetry index
- Multiple wind threshold analysis
