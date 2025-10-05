# HURDAT2 to ML Features Workflow

## Overview

Transform HURDAT2 raw format → Storm-Tract feature matrix using Alpha Shape (Concave Hull) Envelope Approach

**Input**: Raw HURDAT2 text file (mixed header/data format)
**Output**: CSV where each row = one storm's impact on one census tract
**Key Innovation**: Alpha shape concave hull envelope with spherical trigonometry for accurate wind field modeling

---

## ✅ Implementation Status

### Completed Features:
- ✅ Parse Raw HURDAT2 → Flat Table (`parse_raw.py`, `profile_clean.py`)
- ✅ Alpha Shape Envelope Algorithm with spherical trigonometry (`envelope_algorithm.py`)
- ✅ Tract-Storm Distance Calculation with quadrant detection (`storm_tract_distance.py`)
- ✅ Maximum Wind Speed Interpolation with RMW plateau + decay (`wind_interpolation.py`)
- ✅ Duration of Exposure with 15-minute temporal interpolation (`duration_calculator.py`)
- ✅ Envelope Visualization with geographic context (`visualize_envelope.py`)
- ✅ Folium QA/QC Wind Field Maps (`visualize_folium_qa.py`)
- ✅ Testing Infrastructure (pytest with envelope validity tests)
- ✅ Batch Processing (14 major hurricanes validated)

### In Progress:
- 🔄 Lead Time Features (Cat 1-5 thresholds) - planned, not yet implemented

### Key Files:
- `hurdat2/src/envelope_algorithm.py` - Alpha shape envelope creation
- `hurdat2/src/parse_raw.py` - HURDAT2 parser with RMW field
- `hurdat2/src/profile_clean.py` - Data cleaning
- `integration/src/storm_tract_distance.py` - Main feature extraction pipeline
- `integration/src/wind_interpolation.py` - Wind speed modeling
- `integration/src/duration_calculator.py` - Temporal exposure calculation
- `hurdat2/src/visualize_folium_qa.py` - Interactive wind field maps
- `tests/test_envelope_validity.py` - Test framework

---

## Step 1: Parse Raw HURDAT2 → Flat Table ✅ COMPLETE

### 1.1 Read & Restructure Format
```python
# Input: Mixed header/data lines
AL092021, IDA, 40,
20210829, 1655, L, HU, 29.1N, 90.2W, 130, 931, ...

# Output: Flat table with storm metadata
storm_id | storm_name | year | date | time | lat | lon | max_wind | wind_radii_64_ne | radius_max_wind | ...
AL092021 | IDA        | 2021 | 20210829 | 1655 | 29.1 | -90.2 | 130 | 45 | 10 | ...
```

### 1.2 Data Cleaning
- Convert coordinates to decimal degrees
- Handle missing values (-999 → NaN)
- Parse date/time to datetime objects
- Filter for Gulf Coast relevance (lat: 25-32°N, lon: 80-98°W)
- Parse **radius_max_wind (RMW)** from position 20 (available 2021+)
- **Focus on 64kt wind radii** for envelope creation

### 1.3 Feature Selection
**Essential Fields**:
- Storm metadata: storm_id, storm_name, year
- Position: date, time, latitude, longitude
- Intensity: max_wind, min_pressure
- **Wind field: wind_radii_34/50/64 (NE/SE/SW/NW quadrants)** ⭐
- **Radius of maximum wind (RMW)**: radius_max_wind (2021+ storms)
- Event markers: record_id (landfall = 'L'), status

**Output**: `clean_storm_tracks.csv`

---

## Step 2: Load Census Tract Geography ✅ COMPLETE

### 2.1 Census Tract Centroids
```python
from tract_centroids import load_tracts_with_centroids

# Load Gulf Coast census tracts with centroids, filtered to storm bounding box
tract_data = load_tracts_with_centroids(
    year=2019,
    bounds=track_bounds,
    columns=['GEOID', 'STATEFP', 'COUNTYFP', 'TRACTCE'],
    states=['22', '28', '01', '12', '48']  # LA, MS, AL, FL, TX
)
centroids = tract_data.centroids
```

### 2.2 Spatial Filtering
- **Bounding Box Filter**: Tracts within storm track bounds + 3° margin
- **Envelope Filter**: Only process tracts inside 64kt alpha shape envelope
- **Extract centroids**: Lat/lon coordinates for each tract
- **Efficiency**: 94% reduction in computation (7.3M → 438K checks for Ida)

**Output**: GeoDataFrame with tract centroids

---

## Step 3: Alpha Shape Envelope Approach ⭐ **CORE METHODOLOGY**

### 3.1 Algorithm Overview

**Replaced perpendicular distance method with alpha shape (concave hull) approach**

```python
def create_storm_envelope(track_df, wind_threshold='64kt', alpha=0.6):
    """Create concave hull envelope using wind radii extent points"""
    # For each track point:
    #   1. Calculate 4 wind extent points (NE/SE/SW/NW) using spherical trig
    #   2. Collect all extent points
    # Create alpha shape (concave hull) from all points
    # Return: envelope polygon, track line, extent points
```

### 3.2 Spherical Trigonometry for Wind Extent Points

```python
def calculate_destination_point(lat, lon, bearing, distance_nm):
    """Calculate destination point using great-circle navigation"""
    R_NM = 3440.065  # Earth radius in nautical miles
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing)
    angular_distance = distance_nm / R_NM

    dest_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance) +
        math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
    )

    dest_lon_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(dest_lat_rad)
    )

    return (math.degrees(dest_lon_rad), math.degrees(dest_lat_rad))
```

### 3.3 Alpha Shape Construction

- **Alpha parameter**: 0.6 (tuned for hurricane wind fields)
- **Handles sparse radii**: Fallback to buffers for 1-2 point cases
- **Concave hull**: Captures asymmetric wind field shape better than convex hull
- **Segmented approach**: Creates envelope per track point, then unions

### 3.4 Edge Cases Handled

- 1 point → buffer (0.001° radius)
- 2 points → LineString buffer
- 3+ points → convex hull (alpha shape requires 4+)
- 4+ points → alpha shape (concave hull)

---

## Step 4: Feature Extraction Pipeline ✅ COMPLETE

### 4.1 Distance from Storm Track ✅ VALIDATED

**Method**: Haversine great-circle distance from tract centroid to storm track LineString

```python
def compute_min_distance_features(centroids, track):
    # Create track LineString
    track_line = LineString(list(zip(track_lons, track_lats)))

    # For each centroid:
    #   - Calculate distance to track line (degrees)
    #   - Convert to nautical miles and kilometers
    #   - Find nearest track point for wind radii lookup
    #   - Determine quadrant (NE/SE/SW/NW)
    #   - Check if within 64kt wind radius for that quadrant
```

**Output columns**:
- `distance_nm` - Distance to track centerline (nautical miles)
- `distance_km` - Distance to track centerline (kilometers)
- `nearest_quadrant` - Quadrant relative to nearest track point (NE/SE/SW/NW)
- `radius_64_nm` - 64kt wind radius for tract's quadrant
- `within_64kt` - Boolean flag if tract within hurricane-force winds

**Status**: ✅ GOOD (validated in results_scratch_pad.md)

---

### 4.2 Maximum Wind Speed Experienced ✅ COMPLETE

**Method**: RMW plateau + decay model with wind radii boundary enforcement

**Algorithm**:
```python
def calculate_max_wind_experienced(centroid, track_line, track_df, envelope, wind_radii):
    # 1. Find nearest point on track to centroid
    # 2. Interpolate max_wind at that point
    # 3. Interpolate RMW at that point (or use fallback defaults)
    # 4. Determine which wind radii quadrilateral contains centroid (64kt/50kt/34kt)
    # 5. Calculate wind speed:
    #    - If inside RMW → plateau at max_wind
    #    - If between RMW and wind radii boundary → decay from max_wind to threshold
    #    - If outside all wind radii → decay from max_wind to 64kt at envelope edge
```

**RMW Fallback Logic** (for pre-2021 storms without RMW data):
- Cat 3+ (≥96kt): 20 NM
- Cat 1-2 (64-95kt): 30 NM
- Tropical Storm (<64kt): 40 NM

**Output columns**:
- `max_wind_experienced_kt` - Peak wind speed at tract location
- `center_wind_at_approach_kt` - Interpolated max_wind at nearest track point
- `radius_max_wind_at_approach_nm` - RMW at nearest track point
- `inside_eyewall` - Boolean flag if tract within RMW
- `wind_source` - Method used (rmw_plateau, rmw_decay_to_64kt, etc.)
- `distance_to_envelope_edge_nm` - Distance to envelope boundary

**Key Innovation**: Hierarchical logic prioritizes observed wind radii quadrilaterals as boundaries while using RMW for core intensity modeling. This resolves data inconsistencies where RMW circles sometimes extend beyond 64kt wind radii.

---

### 4.3 Duration of Wind Exposure ✅ COMPLETE

**Method**: 15-minute temporal interpolation with envelope membership testing

**Algorithm**:
```python
def calculate_duration_for_tract(centroid, track_df, wind_threshold='64kt', interval_minutes=15):
    # 1. Interpolate track at 15-minute intervals (lat, lon, max_wind, all wind radii)
    # 2. For each interpolated point:
    #    - Create wind extent polygon from 4 quadrant radii
    #    - Test if centroid inside polygon
    # 3. Count consecutive intervals inside
    # 4. Calculate total duration and continuous exposure flag
```

**Temporal Interpolation**: Linear interpolation of ALL fields:
- Position: lat, lon
- Intensity: max_wind
- Wind radii: All 12 radii fields (34/50/64kt × NE/SE/SW/NW)

**Output columns**:
- `total_duration_hours` - Total time tract experienced ≥64kt winds
- `first_exposure_time` - Timestamp when winds first reached threshold
- `last_exposure_time` - Timestamp when winds last exceeded threshold
- `continuous_exposure` - Boolean flag if exposure was uninterrupted
- `interpolated_points_count` - Number of 15-min intervals checked

**Results**: Hurricane Ida Louisiana tracts: 0-6.5 hour exposure, 79% continuous

---

### 4.4 Lead Time Features 🔄 PLANNED

**Method**: Time from storm reaching intensity threshold to closest approach

**Algorithm** (planned):
```python
def calculate_lead_times(track_df, centroid, approach_time):
    # For each category threshold (Cat 1-5):
    #   1. Find first time storm reached that intensity
    #   2. Calculate lead_time = approach_time - threshold_time
    #   3. Handle cases where storm never reaches category
```

**Thresholds**:
- Cat 1: ≥64kt
- Cat 2: ≥83kt
- Cat 3: ≥96kt
- Cat 4: ≥113kt
- Cat 5: ≥137kt

**Output columns** (planned):
- `lead_time_cat1_hours`
- `lead_time_cat2_hours`
- `lead_time_cat3_hours`
- `lead_time_cat4_hours`
- `lead_time_cat5_hours`

**Note**: Separate features for each category since many storms never reach Cat 4/5

**Status**: Plan created (`LEAD_TIME_EXTRACTION_PLAN.md`), implementation pending

---

## Step 5: Visualization & QA/QC ✅ COMPLETE

### 5.1 Static Envelope Visualization
- Matplotlib-based plots with Cartopy geographic context
- Shows track centerline, wind extent points, and alpha shape envelope
- Saves to `hurdat2/outputs/envelopes/`

### 5.2 Interactive Folium Wind Field Maps
- Wind radii quadrilaterals at each track point (34kt, 50kt, 64kt)
- Color-coded layers: yellow (34kt), orange (50kt), red (64kt)
- RMW circles for 2021+ storms (purple)
- Track centerline and intensity markers
- Interactive popups with wind data, timestamps
- Layer toggle controls
- Self-contained HTML output

**Usage**:
```bash
python hurdat2/src/visualize_folium_qa.py \
    --storm-id AL092021 \
    --output hurdat2/outputs/qa_maps/IDA_2021_wind_field.html
```

---

## Step 6: Output Feature Matrix ✅ COMPLETE

### 6.1 Current Schema

Each row: **One storm's impact on one census tract**

| Column | Description | Units | Status |
|--------|-------------|-------|--------|
| `tract_geoid` | Census tract FIPS code | - | ✅ |
| `STATEFP` | State FIPS code | - | ✅ |
| `COUNTYFP` | County FIPS code | - | ✅ |
| `storm_id` | HURDAT2 storm identifier | - | ✅ |
| `storm_name` | Storm name | - | ✅ |
| `storm_tract_id` | Unique storm-tract key | - | ✅ |
| `centroid_lat` | Tract centroid latitude | degrees | ✅ |
| `centroid_lon` | Tract centroid longitude | degrees | ✅ |
| `distance_nm` | Distance to track centerline | nautical miles | ✅ |
| `distance_km` | Distance to track centerline | kilometers | ✅ |
| `nearest_quadrant` | Quadrant at closest approach | NE/SE/SW/NW | ✅ |
| `radius_64_nm` | 64kt radius for quadrant | nautical miles | ✅ |
| `within_64kt` | Inside hurricane-force winds | boolean | ✅ |
| `max_wind_experienced_kt` | Peak wind speed at tract | knots | ✅ |
| `center_wind_at_approach_kt` | Max wind at nearest track point | knots | ✅ |
| `radius_max_wind_at_approach_nm` | RMW at approach | nautical miles | ✅ |
| `inside_eyewall` | Inside RMW | boolean | ✅ |
| `wind_source` | Wind calculation method | string | ✅ |
| `distance_to_envelope_edge_nm` | Distance to envelope boundary | nautical miles | ✅ |
| `total_duration_hours` | Duration of ≥64kt winds | hours | ✅ |
| `first_exposure_time` | First time ≥threshold | datetime | ✅ |
| `last_exposure_time` | Last time ≥threshold | datetime | ✅ |
| `continuous_exposure` | Uninterrupted exposure | boolean | ✅ |
| `interpolated_points_count` | Number of 15-min intervals | count | ✅ |
| `lead_time_cat1_hours` | Warning time from Cat 1 | hours | 🔄 |
| `lead_time_cat2_hours` | Warning time from Cat 2 | hours | 🔄 |
| `lead_time_cat3_hours` | Warning time from Cat 3 | hours | 🔄 |
| `lead_time_cat4_hours` | Warning time from Cat 4 | hours | 🔄 |
| `lead_time_cat5_hours` | Warning time from Cat 5 | hours | 🔄 |

**Current Output**: `integration/outputs/{storm}_tract_distances.csv`

---

## Project Status

### Completed Milestones
1. ✅ **Data Pipeline**: HURDAT2 parsing with RMW field extraction
2. ✅ **Envelope Algorithm**: Alpha shape with spherical trigonometry
3. ✅ **Spatial Filtering**: Bounding box + envelope membership (94% efficiency gain)
4. ✅ **Distance Features**: Great-circle distance, quadrant detection, wind radii comparison
5. ✅ **Wind Speed Modeling**: RMW plateau + decay with wind radii boundaries
6. ✅ **Duration Calculation**: 15-minute temporal interpolation
7. ✅ **Visualization**: Folium interactive QA/QC maps
8. ✅ **Batch Processing**: 14 major hurricanes validated

### Current Work
- 🔄 Lead time feature implementation (5 category thresholds)

### What's Left

#### High Priority
1. **Lead Time Features**: Implement Cat 1-5 lead time calculation
2. **Batch Processing**: Run full pipeline on all 14 hurricanes with updated wind model
3. **Data Validation**: Statistical validation of wind speed distributions
4. **Documentation**: Update API docs with new wind_source column

#### Medium Priority
5. **Performance**: Optimize wind radii lookups (currently recalculating for each tract)
6. **Testing**: Add unit tests for wind interpolation with wind radii
7. **Error Handling**: Improve handling of storms with no RMW data

#### Low Priority (Post-MVP)
- Storm forward speed features
- Approach bearing features
- Asymmetry index calculation
- Multi-threshold duration analysis (34kt, 50kt)
- Rainfall estimation (requires additional data sources)

---

## Key Algorithms & Implementation Details

### Alpha Shape Envelope (`envelope_algorithm.py`)
- **Input**: Storm track DataFrame with wind_radii_64_* columns
- **Output**: Shapely Polygon envelope, track LineString, extent points
- **Key function**: `calculate_destination_point()` - spherical trigonometry
- **Alpha parameter**: 0.6 (empirically tuned)

### Wind Interpolation (`wind_interpolation.py`)
- **Input**: Centroid Point, track LineString, track DataFrame, envelope, wind_radii dict
- **Output**: Dictionary with 8 wind metrics
- **Key innovation**: Hierarchical boundary enforcement (wind radii → RMW → decay)
- **Fallback logic**: Category-based RMW defaults for pre-2021 storms

### Duration Calculator (`duration_calculator.py`)
- **Input**: Centroid Point, track DataFrame, threshold, interval minutes
- **Output**: Dictionary with 5 duration metrics
- **Key technique**: Linear interpolation of all track fields at 15-min intervals
- **Edge case handling**: 2-point LineString buffer for sparse wind radii

### Storm-Tract Pipeline (`storm_tract_distance.py`)
- **CLI interface**: Argparse with storm-id, census-year, bounds-margin, states, output
- **Spatial filtering**: Two-stage (bounding box → envelope membership)
- **Feature assembly**: Concatenates distance, wind, duration DataFrames

---

## Data Quality Notes

### HURDAT2 Limitations
- **Wind radii availability**: Only 2004+ (pre-2004 shows -999)
- **RMW availability**: Only 2021+ (Ida, Ian have data; others use defaults)
- **Occasional gaps**: Even post-2004, some track points missing wind radii
- **RMW vs Wind Radii inconsistencies**: RMW sometimes exceeds 64kt radius (resolved by hierarchical logic)

### Validation Results
- **14 hurricanes processed**: 100% success rate for envelope generation
- **Hurricane Ida**: 491 Louisiana tracts, wind speeds 34-121kt (physically reasonable)
- **Duration ranges**: 0-6.5 hours for Ida, 79% continuous exposure
- **Distance metrics**: Validated with haversine calculations

---

## References

- HURDAT2 Format: https://www.nhc.noaa.gov/data/hurdat/hurdat2-format-nov2019.pdf
- RMW in HURDAT2: Added 2021, best track quality-controlled observations
- Alpha Shape Algorithm: Edelsbrunner et al. (1983) via alphashape library
- Spherical Trigonometry: Vincenty formula for great-circle navigation
