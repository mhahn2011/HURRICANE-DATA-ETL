# Spatial Hurricane-to-Census Tract Pipeline

**Goal**: Transform HURDAT2 storm tracks → census tract wind impact features using Max Distance Envelope approach

## Core Steps (Essential Only)

### Step 1: Data Foundation ✅ COMPLETE
- Parse HURDAT2 → clean DataFrame with coordinates, wind speeds, wind radii
- Basic validation and cleaning
- **Status**: Implemented in Cells 1-3

### Step 2: Single Storm Test (Hurricane Ida)
**Next Target**: Prove envelope methodology works for one storm

```python
# Cell 4: Select Hurricane Ida (2021) as test case
ida_track = df_clean[df_clean['storm_name'] == 'IDA'].copy()
# Filter to relevant track points, sort by date
```

```python
# Cell 5: Create storm envelope polygon
def create_storm_envelope(track_df):
    # Convert 4-directional wind radii to actual lat/lon points
    # Find max perpendicular distances from track
    # Create bounding polygon around entire storm path
    return envelope_polygon
```

```python
# Cell 6: Visualize Ida envelope
# Plot storm track + envelope on map
# Validate polygon geometry (no self-intersections)
```

### Step 3: Census Tract Integration
```python
# Cell 7: Load Gulf Coast census tract centroids
# Download real census tract data for Gulf Coast states
# Extract centroids from tract geometries
import geopandas as gpd
tracts = gpd.read_file("https://www2.census.gov/geo/tiger/TIGER2020/TRACT/...")  # TX, LA, MS, AL, FL
tract_centroids = tracts.centroid
tract_points = [(row.y, row.x, row.GEOID) for row in tracts.itertuples()]
```

```python
# Cell 8: Find tracts within Ida envelope
# Point-in-polygon test
# Validate spatial filtering works correctly
```

### Step 4: Wind Speed Calculation
```python
# Cell 9: Calculate wind speeds for affected tracts
# Distance from tract centroid to storm path
# Linear interpolation: max_wind (at path) → 64kt (at envelope edge)
# Test on sample tracts
```

### Step 5: Scale to Multiple Storms (Optional)
```python
# Cell 10: Process recent storms with wind radii data
# Batch processing pipeline
# Export final storm-tract feature matrix
```

## Key Data Transformations

**Input**: Storm track points with wind radii
```
storm_id | lat | lon | max_wind | wind_radii_64_ne | wind_radii_64_se | wind_radii_64_sw | wind_radii_64_nw
```

**Intermediate**: Storm envelope polygon
```python
envelope = Polygon(boundary_points)  # Derived from wind radii
```

**Output**: Storm-tract impact matrix
```
storm_id | tract_id | max_wind_experienced | distance_to_track | exposure_duration
```

## Implementation Focus

- **Hurricane Ida**: Single storm test case (2021, well-documented)
- **Wind radii data**: Use 64-knot radii for envelope creation
- **Gulf Coast region**: TX, LA, MS, AL coastal areas
- **Census tract centroids**: Point-in-polygon for efficiency

## Success Criteria

1. **Envelope creation**: Valid polygon for Hurricane Ida
2. **Spatial filtering**: Identify ~50-200 affected census tracts
3. **Wind calculation**: Reasonable wind speeds (64-130 kt range)
4. **Visualization**: Clear map showing track + envelope + affected tracts

**Target**: Working prototype for single storm, then scale up