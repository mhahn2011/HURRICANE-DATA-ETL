# Feature Extraction Implementation Plan

## Goal
Create a unified feature extraction pipeline that generates **one comprehensive CSV table** containing all storm-tract features for ML analysis.

---

## Current State Assessment

### ✅ Existing Outputs

**1. Spatial Join Output:**
- File: `hurdat2/outputs/ida_tract_pairs.csv`
- Columns: `storm_id, storm_name, year, tract_geoid`
- Records: ~hundreds (tracts within Ida's envelope)
- Created by: `hurdat2/src/tract_spatial_join.py`

**2. Distance Features Output:**
- File: `integration/outputs/ida_gulf_distances.csv`
- Columns: `tract_geoid, storm_id, storm_name, storm_time, distance_nm, distance_km, nearest_quadrant, radius_64_nm, within_64kt, storm_tract_id`
- Records: 7,275 (all Gulf Coast tracts)
- Created by: `integration/src/storm_tract_distance.py`

### ⚠️ Issue Identified
We have **two separate outputs** with overlapping information:
- `ida_tract_pairs.csv` - Only tracts INSIDE envelope
- `ida_gulf_distances.csv` - ALL Gulf Coast tracts (most outside envelope)

**We need**: One unified table with tracts inside envelope + all features

---

## Unified Output Schema

### Final Table: `integration/outputs/storm_tract_features.csv`

Each row = One storm's impact on one census tract (inside envelope only)

| Column | Type | Description | Source | Status |
|--------|------|-------------|--------|--------|
| `storm_tract_id` | str | Unique ID: `{storm_id}_{tract_geoid}` | Generated | ✅ Exists |
| `storm_id` | str | HURDAT2 identifier (e.g., AL092021) | HURDAT2 | ✅ Exists |
| `storm_name` | str | Storm name (e.g., IDA) | HURDAT2 | ✅ Exists |
| `year` | int | Storm year | HURDAT2 | ✅ Exists |
| `tract_geoid` | str | 11-digit census tract FIPS | Census | ✅ Exists |
| `tract_state_fp` | str | 2-digit state FIPS | Census | 🔄 Add |
| `tract_county_fp` | str | 3-digit county FIPS | Census | 🔄 Add |
| **DISTANCE FEATURES** |
| `distance_to_track_nm` | float | Min distance from centroid to track (nm) | Calculated | ✅ Exists |
| `distance_to_track_km` | float | Min distance from centroid to track (km) | Calculated | ✅ Exists |
| `nearest_approach_time` | datetime | Time of closest approach | Calculated | ✅ Exists |
| **WIND FEATURES** |
| `max_wind_experienced_kt` | float | Interpolated peak wind at tract | **NEW** | 🆕 To build |
| `center_wind_at_approach_kt` | float | Storm center wind at nearest point | **NEW** | 🆕 To build |
| `distance_to_envelope_edge_nm` | float | Distance from track to envelope in tract direction | **NEW** | 🆕 To build |
| **DURATION FEATURES** |
| `duration_in_envelope_hours` | float | Time centroid spent within envelope | **NEW** | 🆕 To build |
| `first_entry_time` | datetime | When centroid entered envelope | **NEW** | 🆕 To build |
| `last_exit_time` | datetime | When centroid exited envelope | **NEW** | 🆕 To build |
| **INTENSIFICATION FEATURES** |
| `max_intensification_rate_kt_per_24h` | float | Storm's max 24h wind increase | **NEW** | 🆕 To build |
| `time_of_max_intensification` | datetime | When max intensification occurred | **NEW** | 🆕 To build |
| `cat4_first_time` | datetime | First time storm reached Cat 4 (113kt) | **NEW** | 🆕 To build |
| `lead_time_to_max_wind_hours` | float | Hours between Cat4 and tract max wind | **NEW** | 🆕 To build |

---

## Implementation Architecture

```
Input Data:
├── hurdat2/input_data/hurdat2-atlantic.txt          # Raw HURDAT2 data
├── census/input_data/tl_2019_*_tract.zip           # Census shapefiles (5 states)
└── hurdat2/outputs/batch_processing_summary.csv    # 14 hurricane metadata

Core Processing Modules:
├── hurdat2/src/
│   ├── parse_raw.py                    # ✅ Parse HURDAT2
│   ├── profile_clean.py                # ✅ Clean data
│   └── envelope_algorithm.py           # ✅ Create envelopes (alpha=0.6)
│
├── census/src/
│   └── tract_centroids.py              # ✅ Load tract centroids
│
└── integration/src/
    ├── storm_tract_distance.py         # ✅ Calculate distances
    ├── wind_interpolation.py           # 🆕 NEW: Max wind features
    ├── duration_calculator.py          # 🆕 NEW: Duration features
    ├── intensification_features.py     # 🆕 NEW: Intensification metrics
    └── feature_pipeline.py             # 🆕 NEW: Orchestrates all features

Batch Processing:
└── integration/scripts/
    └── batch_extract_features.py       # 🆕 NEW: Process all 14 storms

Final Output:
└── integration/outputs/
    └── storm_tract_features.csv        # 🆕 Unified feature table
```

---

## Module-by-Module Implementation Plan

### Module 1: Wind Interpolation (`integration/src/wind_interpolation.py`)

**Purpose**: Calculate max wind experienced at tract centroid using envelope-based linear decay

**Inputs**:
- Storm track LineString (from `envelope_algorithm.create_storm_envelope()`)
- Storm track DataFrame with `max_wind` column
- Tract centroid Point (from census)
- Envelope Polygon (from `envelope_algorithm`)
- Distance to track (from `storm_tract_distance.py`)

**Algorithm**:
```python
def calculate_max_wind_experienced(
    centroid_point: Point,
    track_linestring: LineString,
    track_df: pd.DataFrame,
    envelope_polygon: Polygon,
    distance_to_track_km: float
) -> dict:
    """
    Calculate interpolated wind speed at tract centroid.

    Steps:
    1. Find nearest point on track LineString to centroid
    2. Identify which two track observations bracket that point
    3. Linearly interpolate max_wind between those observations
    4. Draw ray from nearest track point through centroid
    5. Find where ray intersects envelope boundary
    6. Calculate distance from track to envelope edge
    7. Linear decay: wind = center_wind - (center_wind - 64) * (dist_to_track / dist_to_edge)

    Returns:
        {
            'max_wind_experienced_kt': float,
            'center_wind_at_approach_kt': float,
            'distance_to_envelope_edge_nm': float
        }
    """
```

**Key Functions**:
- `find_nearest_point_on_track(centroid, track_linestring)` → Returns Point on track
- `interpolate_wind_at_point(point_on_track, track_df)` → Returns interpolated max_wind
- `calculate_envelope_edge_distance(track_point, centroid, envelope)` → Ray intersection distance
- `linear_wind_decay(center_wind, distance_to_track, distance_to_edge)` → Wind at centroid

**Output**: Dictionary with 3 wind features per tract

---

### Module 2: Duration Calculator (`integration/src/duration_calculator.py`)

**Purpose**: Calculate how long tract centroid was within storm envelope

**Inputs**:
- Storm track DataFrame with datetime column
- Tract centroid Point
- Envelope Polygon

**Algorithm**:
```python
def calculate_duration_in_envelope(
    centroid_point: Point,
    track_df: pd.DataFrame,
    envelope_polygon: Polygon
) -> dict:
    """
    Calculate temporal exposure to storm.

    Steps:
    1. For each track point (6-hour intervals), check if centroid is within envelope
    2. Track transitions: outside → inside (entry), inside → outside (exit)
    3. Sum total time inside envelope
    4. Record first entry and last exit times

    Note: Centroid may enter/exit multiple times if storm loops

    Returns:
        {
            'duration_in_envelope_hours': float,
            'first_entry_time': datetime,
            'last_exit_time': datetime
        }
    """
```

**Key Functions**:
- `check_point_in_envelope_over_time(centroid, track_df, envelope)` → Boolean array
- `calculate_total_duration(boolean_array, time_resolution_hours=6)` → Total hours
- `find_entry_exit_times(boolean_array, timestamps)` → First/last times

**Output**: Dictionary with 3 duration features per tract

---

### Module 3: Intensification Features (`integration/src/intensification_features.py`)

**Purpose**: Calculate storm intensification metrics

**Inputs**:
- Storm track DataFrame with `max_wind` and datetime columns

**Algorithm**:
```python
def calculate_intensification_features(track_df: pd.DataFrame) -> dict:
    """
    Calculate storm-level intensification metrics.

    Note: These are STORM-level features (same for all tracts of a given storm)

    Steps:
    1. Calculate 24-hour rolling wind change: max_wind[t] - max_wind[t-24h]
    2. Find maximum intensification rate
    3. Find first time storm reached Cat 4 (113 kt)

    Returns:
        {
            'max_intensification_rate_kt_per_24h': float,
            'time_of_max_intensification': datetime,
            'cat4_first_time': datetime or None
        }
    """
```

**Key Functions**:
- `calculate_rolling_wind_change(track_df, window_hours=24)` → Array of rates
- `find_max_intensification(wind_changes)` → Max rate and time
- `find_category_threshold_time(track_df, threshold_kt=113)` → First time above threshold

**Additional Feature**:
```python
def calculate_lead_time(
    cat4_time: datetime,
    nearest_approach_time: datetime
) -> float:
    """
    Calculate warning time between Cat 4 and max impact.

    Positive value = had warning time
    Negative value = storm intensified after passing
    """
    if cat4_time is None:
        return None
    return (nearest_approach_time - cat4_time).total_seconds() / 3600.0  # hours
```

**Output**: Dictionary with 4 intensification features

---

### Module 4: Feature Pipeline Orchestrator (`integration/src/feature_pipeline.py`)

**Purpose**: Coordinate all feature extraction for a single storm

**Main Function**:
```python
def extract_all_features_for_storm(
    storm_id: str,
    hurdat_data_path: str = "hurdat2/input_data/hurdat2-atlantic.txt",
    census_year: int = 2019,
    gulf_states: list = ['22', '28', '48', '01', '12'],
    alpha: float = 0.6,
    wind_threshold: str = '64kt'
) -> pd.DataFrame:
    """
    Extract all features for one storm.

    Steps:
    1. Load and clean HURDAT2 data
    2. Filter to specific storm
    3. Create envelope (alpha=0.6, 64kt threshold)
    4. Load Gulf Coast census tract centroids
    5. Spatial join: Find tracts within envelope
    6. For each tract in envelope:
        a. Calculate distance features
        b. Calculate wind features
        c. Calculate duration features
    7. Calculate storm-level intensification features
    8. Merge all features into single DataFrame

    Returns:
        DataFrame with all features (one row per tract in envelope)
    """
```

**Workflow**:
```python
# Pseudocode structure
def extract_all_features_for_storm(storm_id, ...):
    # 1. Load data
    track_df = load_and_filter_storm(storm_id)
    centroids_gdf = load_tract_centroids(gulf_states, census_year)

    # 2. Create envelope
    envelope, track_line, _ = create_storm_envelope(track_df, wind_threshold, alpha)

    # 3. Spatial join
    tracts_in_envelope = centroids_gdf[centroids_gdf.intersects(envelope)]

    # 4. Calculate storm-level features (same for all tracts)
    intensification_features = calculate_intensification_features(track_df)

    # 5. Calculate tract-level features
    results = []
    for idx, tract_row in tracts_in_envelope.iterrows():
        centroid = tract_row.geometry

        # Distance features
        dist_features = compute_min_distance_features([tract_row], track_df).iloc[0]

        # Wind features
        wind_features = calculate_max_wind_experienced(
            centroid, track_line, track_df, envelope, dist_features['distance_km']
        )

        # Duration features
        duration_features = calculate_duration_in_envelope(
            centroid, track_df, envelope
        )

        # Lead time (tract-specific)
        lead_time = calculate_lead_time(
            intensification_features['cat4_first_time'],
            dist_features['storm_time']
        )

        # Merge all features
        row = {
            **tract_row[['GEOID', 'STATEFP', 'COUNTYFP']].to_dict(),
            **dist_features.to_dict(),
            **wind_features,
            **duration_features,
            **intensification_features,
            'lead_time_to_max_wind_hours': lead_time
        }
        results.append(row)

    return pd.DataFrame(results)
```

**Output**: DataFrame with all features for one storm

---

### Module 5: Batch Processing Script (`integration/scripts/batch_extract_features.py`)

**Purpose**: Process all 14 hurricanes and generate final unified CSV

**Main Function**:
```python
def batch_extract_all_storms():
    """
    Process all 14 Gulf Coast hurricanes (2005-2022).

    Storms to process:
        KATRINA (2005), RITA (2005), DENNIS (2005)
        GUSTAV (2008), IKE (2008)
        HARVEY (2017), IRMA (2017)
        MICHAEL (2018)
        LAURA (2020), DELTA (2020), ZETA (2020), SALLY (2020)
        IDA (2021)
        IAN (2022)

    Steps:
    1. Load storm list from batch_processing_summary.csv
    2. For each storm:
        a. Extract all features using feature_pipeline.py
        b. Append to master DataFrame
    3. Save unified output: integration/outputs/storm_tract_features.csv
    4. Generate summary statistics
    """
```

**Implementation**:
```python
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from feature_pipeline import extract_all_features_for_storm

def main():
    # Load storm list
    summary_path = Path("hurdat2/outputs/batch_processing_summary.csv")
    storms = pd.read_csv(summary_path)

    all_features = []

    for idx, storm_row in storms.iterrows():
        storm_id = storm_row['storm_id']
        storm_name = storm_row['name']
        year = storm_row['year']

        print(f"\n{'='*60}")
        print(f"Processing: {storm_name} ({year}) - {storm_id}")
        print(f"{'='*60}")

        try:
            # Extract features for this storm
            storm_features = extract_all_features_for_storm(storm_id)
            all_features.append(storm_features)

            print(f"✅ Extracted {len(storm_features)} tract features")

        except Exception as e:
            print(f"❌ Error processing {storm_name}: {e}")
            continue

    # Concatenate all storms
    final_df = pd.concat(all_features, ignore_index=True)

    # Save unified output
    output_path = Path("integration/outputs/storm_tract_features.csv")
    output_path.parent.mkdir(exist_ok=True, parents=True)
    final_df.to_csv(output_path, index=False)

    # Summary
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Total storms processed: {len(all_features)}")
    print(f"Total storm-tract records: {len(final_df):,}")
    print(f"Output saved to: {output_path}")
    print(f"\nRecords by storm:")
    print(final_df.groupby(['storm_name', 'year']).size().sort_values(ascending=False))

if __name__ == "__main__":
    main()
```

**Output**:
- `integration/outputs/storm_tract_features.csv` - Final unified table
- Console summary with record counts

---

## Testing Strategy

### Unit Tests

**1. Wind Interpolation Tests** (`tests/test_wind_interpolation.py`)
```python
def test_linear_decay_at_track_center():
    """Wind at track center should equal max_wind"""

def test_linear_decay_at_envelope_edge():
    """Wind at envelope edge should equal 64kt"""

def test_wind_interpolation_between_observations():
    """Verify linear interpolation of max_wind between track points"""
```

**2. Duration Tests** (`tests/test_duration_calculator.py`)
```python
def test_duration_for_stationary_point():
    """Point inside envelope entire time should have duration = track length"""

def test_duration_for_point_outside_envelope():
    """Point never inside envelope should have duration = 0"""

def test_multiple_entry_exit_events():
    """Handle storms that loop back"""
```

**3. Intensification Tests** (`tests/test_intensification_features.py`)
```python
def test_max_intensification_detection():
    """Correctly identify rapid intensification events"""

def test_cat4_threshold_detection():
    """Find first time storm reaches Cat 4"""

def test_storms_that_never_reach_cat4():
    """Handle storms that stay below Cat 4"""
```

### Integration Tests

**Test with Hurricane Ida** (known ground truth):
```python
def test_ida_full_pipeline():
    """
    Validate full pipeline with Ida (2021)

    Expected outputs:
    - ~hundreds of tracts (based on ida_tract_pairs.csv)
    - Max wind experienced should be <= Ida's peak (130 kt)
    - Duration should be reasonable (6-48 hours)
    - Lead time should be positive (had warning)
    """
```

---

## Execution Plan

### Phase 1: Build Core Modules (Estimated: 3-4 hours)

1. **Wind Interpolation Module** (60 min)
   - Create `integration/src/wind_interpolation.py`
   - Implement ray-envelope intersection
   - Test with Ida

2. **Duration Calculator** (45 min)
   - Create `integration/src/duration_calculator.py`
   - Implement temporal tracking
   - Test with Ida

3. **Intensification Features** (30 min)
   - Create `integration/src/intensification_features.py`
   - Calculate rolling wind changes
   - Test with Katrina (known rapid intensification)

4. **Feature Pipeline** (60 min)
   - Create `integration/src/feature_pipeline.py`
   - Orchestrate all modules
   - Test end-to-end with Ida

### Phase 2: Batch Processing (Estimated: 1-2 hours)

5. **Batch Script** (45 min)
   - Create `integration/scripts/batch_extract_features.py`
   - Process all 14 storms
   - Generate unified CSV

6. **Validation** (30 min)
   - Verify output schema
   - Check for missing values
   - Validate ranges (e.g., wind speeds reasonable)
   - Compare counts to existing outputs

### Phase 3: Documentation (Estimated: 30 min)

7. **Update Workflow Doc**
   - Document final feature definitions
   - Add example usage
   - Record any assumptions

---

## File Locations Summary

### Inputs (Existing)
- `hurdat2/input_data/hurdat2-atlantic.txt`
- `census/input_data/tl_2019_*_tract.zip`
- `hurdat2/outputs/batch_processing_summary.csv`

### New Code Files
- `integration/src/wind_interpolation.py`
- `integration/src/duration_calculator.py`
- `integration/src/intensification_features.py`
- `integration/src/feature_pipeline.py`
- `integration/scripts/batch_extract_features.py`

### New Test Files
- `tests/test_wind_interpolation.py`
- `tests/test_duration_calculator.py`
- `tests/test_intensification_features.py`

### Outputs
- **Primary**: `integration/outputs/storm_tract_features.csv` ⭐
- **Intermediate** (can archive):
  - `hurdat2/outputs/ida_tract_pairs.csv`
  - `integration/outputs/ida_gulf_distances.csv`
  - `integration/outputs/ida_la_distances.csv`

---

## Open Questions / Decisions Needed

1. **Duration Definition**:
   - Current plan: Time within envelope (simple)
   - Alternative: Time experiencing >64kt winds (more complex)
   - **Decision**: Stick with "time in envelope" for MVP?

2. **Wind Decay Outside Envelope**:
   - Current plan: Only calculate for tracts inside envelope
   - All tracts in unified table are inside envelope
   - **Decision**: Confirmed - no extrapolation needed

3. **Intensification Lead Time**:
   - Current plan: Time between Cat 4 and max impact at tract
   - What if storm never reaches Cat 4?
   - **Decision**: Return `None` for storms <Cat 4?

4. **Temporal Resolution**:
   - HURDAT2 is 6-hour intervals
   - **Decision**: Keep 6-hour granularity or interpolate to hourly?

5. **Multiple Envelope Entries**:
   - If storm loops, tract could enter/exit multiple times
   - **Decision**: Sum all exposure periods or track separately?

---

## Success Criteria

✅ **Output Validation**:
- One CSV with ~10,000-50,000 rows (14 storms × hundreds-thousands of tracts each)
- All 19 columns present with no unexpected nulls
- Wind speeds: 0-160 kt range
- Durations: 0-72 hours range
- All storm_tract_ids unique

✅ **Data Quality**:
- No tracts outside envelope in final table
- Distance features match existing `ida_gulf_distances.csv` for Ida
- Wind experienced ≤ max_wind for each storm
- Duration ≥ 0 for all tracts

✅ **Performance**:
- Process all 14 storms in <30 minutes
- Memory usage <4GB

---

## Next Steps

Once this plan is approved, we'll proceed in order:
1. Build wind interpolation module (most complex)
2. Build duration calculator
3. Build intensification features
4. Integrate into pipeline
5. Run batch processing
6. Validate and iterate
