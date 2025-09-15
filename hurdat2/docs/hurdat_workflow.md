# HURDAT2 to ML Features Workflow

## Overview

Transform HURDAT2 raw format → Storm-Tract feature matrix using Max Distance Envelope Approach

**Input**: Raw HURDAT2 text file (mixed header/data format)
**Output**: CSV where each row = one storm's impact on one census tract
**Key Innovation**: Envelope polygon method for efficient wind field modeling

---

## Step 1: Parse Raw HURDAT2 → Flat Table

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

## Step 4: Identify Relevant Census Tracts

### 4.1 Spatial Filter Using Envelope
```python
def find_relevant_tracts(storm_envelope, tract_centroids):
    """Point-in-polygon test for computational efficiency"""
    relevant_tracts = []
    
    for tract_id, centroid in tract_centroids.items():
        if storm_envelope.contains(Point(centroid)):
            relevant_tracts.append(tract_id)
    
    return relevant_tracts
```

### 4.2 Create Storm-Tract Combinations
- For each storm: Find all tracts within envelope
- Create pairs: (storm_id, tract_id)
- **Dramatic reduction**: Only process tracts actually affected

**Output**: `relevant_storm_tract_pairs.csv`

---

## Step 5: Calculate Wind Speeds for Relevant Tracts

### 5.1 Wind Speed Interpolation
```python
def calculate_wind_at_tract(storm_track, tract_centroid, storm_envelope):
    # Find closest point on storm path to tract centroid
    closest_path_point = find_closest_point_on_path(storm_track, tract_centroid)
    
    # Calculate perpendicular distance from centroid to path
    perp_distance = calculate_perpendicular_distance(tract_centroid, closest_path_point)
    
    # Get maximum wind radius at that path location
    max_radius = get_max_wind_radius_at_point(closest_path_point)
    max_wind_speed = closest_path_point['max_wind']
    
    # Linear interpolation: max_wind (at path center) → 64 knots (at envelope boundary)
    if perp_distance <= max_radius:
        wind_speed = max_wind_speed - (max_wind_speed - 64) * (perp_distance / max_radius)
        return max(wind_speed, 64)  # Minimum 64 knots within envelope
    else:
        return 0  # Outside envelope = no significant winds
```

### 5.2 Duration of Exposure Features
```python
def calculate_exposure_duration(storm_track, tract_centroid):
    """Calculate time tract spent within storm envelope"""
    total_hours = 0
    peak_wind = 0
    exposure_start = None
    exposure_end = None
    
    for i, track_point in storm_track.iterrows():
        # Create envelope for this time step
        temp_envelope = create_point_envelope(track_point)
        
        if temp_envelope.contains(Point(tract_centroid)):
            total_hours += 6  # 6-hour intervals in HURDAT2
            wind_speed = calculate_wind_at_tract([track_point], tract_centroid, temp_envelope)
            
            if wind_speed > peak_wind:
                peak_wind = wind_speed
            
            if exposure_start is None:
                exposure_start = track_point['datetime']
            exposure_end = track_point['datetime']
    
    return {
        'exposure_duration_hours': total_hours,
        'peak_wind_experienced': peak_wind,
        'exposure_start_time': exposure_start,
        'exposure_end_time': exposure_end
    }
```

---

## Step 6: Feature Engineering

### 6.1 Core Features per Storm-Tract Combination
```python
features = {
    # Identifiers
    'tract_id': tract_fips,
    'storm_id': storm_identifier,
    'storm_name': storm_name,
    'year': storm_year,
    
    # Wind Impact ⭐ KEY FEATURES
    'max_wind_experienced': peak_wind_at_tract,
    'exposure_duration_hours': time_in_envelope,
    'distance_to_track': perpendicular_distance_to_path,
    
    # Timing
    'time_of_peak_winds': timestamp_of_closest_approach,
    'exposure_start': when_winds_began,
    'exposure_end': when_winds_ended,
    
    # Storm Characteristics
    'storm_max_intensity': overall_max_wind_speed,
    'storm_min_pressure': overall_min_pressure,
    'landfall_flag': whether_storm_made_landfall,
    'approach_bearing': direction_of_approach_to_tract
}
```

### 6.2 Advanced Features
```python
# Storm evolution features
features.update({
    'intensification_rate': max_24hr_wind_increase,
    'storm_forward_speed': average_forward_motion,
    'time_to_landfall': hours_until_landfall,
    'storm_size_index': average_64kt_radius,
    'asymmetry_index': max_radius_difference / mean_radius
})
```

---

## Step 7: Output Feature Matrix

### 7.1 Final Schema
Each row represents: **One storm's impact on one census tract**

| Column Group | Examples |
|--------------|----------|
| **Identifiers** | tract_id, storm_id, storm_name, year |
| **Wind Impact** ⭐ | max_wind_experienced, exposure_duration_hours, distance_to_track |
| **Timing** | time_of_peak_winds, exposure_start, exposure_end |
| **Storm Context** | storm_max_intensity, landfall_flag, approach_bearing |
| **Advanced** | intensification_rate, storm_forward_speed, asymmetry_index |

### 7.2 Quality Control
- Validate envelope polygon creation (no self-intersections)
- Check wind speed interpolation (64-200 knot range)
- Verify duration calculations (reasonable exposure times)
- Spatial validation (tract centroids within expected regions)

**Final Output**: `hurdat_storm_tract_features.csv`

---

## Implementation: Jupyter Notebook Structure

### **Notebook: `hurdat2_to_features.ipynb`**

Progressive development approach where each section builds on the previous:

#### **Section 1: Data Acquisition & Basic Parsing**
```python
# Cell 1: Download HURDAT2 data
# Cell 2: Parse header/data format → clean DataFrame  
# Cell 3: Basic validation and data types
```
**Outcome**: Clean tabular format with storm metadata

#### **Section 2: Data Profiling & Understanding**
```python
# Cell 4: ydata_profiling report generation
# Cell 5: Explore wind radii patterns and availability
# Cell 6: Gulf Coast geographic filtering
```
**Outcome**: Data quality understanding and regional focus

#### **Section 3: Single Storm Envelope (Test Case)**
```python
# Cell 7: Select Hurricane Ida as test case
# Cell 8: Create storm path polyline from track points
# Cell 9: Convert 4-directional wind radii → lat/lon extent points
# Cell 10: Generate envelope polygon and visualize
```
**Outcome**: Working envelope algorithm for one storm

#### **Section 4: Census Tract Integration**
```python
# Cell 11: Load Gulf Coast census tract centroids
# Cell 12: Point-in-polygon filtering for Ida envelope
# Cell 13: Validate spatial operations and tract selection
```
**Outcome**: Spatial filtering methodology established

#### **Section 5: Wind Speed Calculations**
```python
# Cell 14: Calculate distance from tract centroids to storm track
# Cell 15: Implement linear interpolation for wind speeds
# Cell 16: Test wind calculations on Ida + sample tracts
```
**Outcome**: Wind speed assignment methodology working

#### **Section 6: Scale to Multiple Storms**
```python
# Cell 17: Create batch processing pipeline
# Cell 18: Process all Gulf Coast storms (2004+ for wind radii)
# Cell 19: Generate complete storm-tract feature matrix
```
**Outcome**: Production-scale processing capability

#### **Section 7: Export & Validation**
```python
# Cell 20: Export storm_tract_features.csv
# Cell 21: Data quality checks and summary statistics
# Cell 22: Usage documentation and next steps
```
**Outcome**: ML-ready feature matrix with validation

### **Cell-by-Cell Validation Strategy**
Each working cell represents a milestone:
- **Assertions**: Validate data shapes, required columns, geometric validity
- **Visualizations**: Plot sample results to verify correctness
- **Summary stats**: Check ranges, distributions, missing values

### **Natural Progression Benefits**
- **Self-documenting**: Notebook tells the complete development story
- **Debugging-friendly**: Can re-run individual sections independently  
- **Iterative**: Each section builds incrementally on previous work
- **Cloud Code optimized**: AI can write next cell based on previous results

---

## Computational Advantages

### 1. **Efficiency Gains**
- **Pre-filtering**: Only process tracts within storm envelopes
- **Single polygon**: One envelope per storm vs thousands of point calculations
- **Vectorized operations**: Batch processing of spatial operations

### 2. **Geometric Accuracy**
- **Asymmetric wind fields**: Captures real storm structure
- **Track-following**: Accounts for storm path curvature
- **Data-driven**: Uses actual HURDAT2 wind radii measurements

### 3. **Feature Quality**
- **Duration modeling**: Time-based exposure calculations
- **Peak impact timing**: When maximum winds occurred
- **Spatial precision**: Census tract-level granularity

This envelope approach transforms 170 years of hurricane data into an efficient, accurate feature matrix optimized for machine learning while capturing the essential physics of hurricane wind fields.