# HURDAT2-Census Feature Extraction

This folder contains all transformation logic that combines HURDAT2 hurricane data with census tract locations to extract storm-tract features.

---

## Purpose

Extract features describing how each hurricane affected each census tract by combining:
- **HURDAT2 data** (storm tracks, wind radii, intensity)
- **Census tract data** (geographic locations, centroids)

This is the **transformation layer** - all feature engineering happens here. The `integration/` folder only assembles and validates final outputs.

---

## Source Files (`src/`)

### Core Feature Extraction Pipeline

**`storm_tract_distance.py`** - Main pipeline orchestrating all feature calculations
- Spatial filtering (which tracts in storm envelope)
- Distance features (proximity to track, quadrant detection)
- Coordinates all feature extraction modules
- Outputs intermediate feature tables

### Feature Modules

**`wind_interpolation.py`** - Wind speed estimation
- RMW plateau + decay model
- Hierarchical boundary enforcement (wind radii → RMW → decay)
- Interpolates max wind experienced at tract locations

**`duration_calculator.py`** - Temporal exposure calculation
- 15-minute temporal interpolation
- Arc-based wind polygons (circular quadrant boundaries)
- Continuous vs intermittent exposure detection

**`lead_time_calculator.py`** - Warning time features
- Category threshold detection (Cat 1-5)
- Time from intensification to closest approach
- Handles storms that never reach high categories

### QA/QC Visualization

**`qaqc_comprehensive_suite.py`** - Comprehensive validation suite
- Generates HTML reports for all features
- Distance, wind, duration, lead time visualizations

**`qaqc_lead_time_visualization.py`** - Lead time specific QA/QC
- Category-specific lead time maps
- Temporal progression visualization

---

## Outputs

### `outputs/features/`
Intermediate feature tables (CSVs) with storm-tract combinations:
- `{storm_id}_tract_distances.csv` - Distance and proximity features
- `{storm_id}_features_complete.csv` - All features (wind, duration, lead time)

**Schema:** One row per (storm, tract) pair with columns:
- Identifiers: `tract_geoid`, `storm_id`, `storm_name`, `storm_tract_id`
- Distance: `distance_nm`, `distance_km`, `nearest_quadrant`, `within_64kt`
- Wind: `max_wind_experienced_kt`, `center_wind_at_approach_kt`, `wind_source`, `inside_eyewall`
- Duration: `total_duration_hours`, `first_exposure_time`, `last_exposure_time`, `continuous_exposure`
- Lead time: `lead_time_cat1_hours`, `lead_time_cat2_hours`, ... `lead_time_cat5_hours`

### `outputs/transformations/`
Methodology visualizations showing how features are derived:
- `qaqc_01_distance.html` - Distance classification validation
- `qaqc_02_wind.html` - Wind interpolation methodology
- `qaqc_03_duration.html` - Duration calculation examples
- `qaqc_04_lead_time_cat*.html` - Lead time calculations by category

---

## Key Algorithms

### Arc-Based Wind Polygons ✓
**Status:** Implemented (v2.1)

Wind radii represent circular arcs, not straight chords. Implementation samples 30 points per quadrant arc to create accurate wind field boundaries.

**Impact:** Corrects 10-30% systematic underestimation of wind field area from previous chord-based method.

### RMW Plateau + Decay Model
**Status:** Active

Wind speed estimation uses hierarchical logic:
1. Check wind radii quadrilateral boundaries (64kt/50kt/34kt)
2. Inside RMW → plateau at max wind
3. Between RMW and boundary → linear decay to threshold
4. Outside all radii → decay to 64kt at envelope edge

**Metadata:** `wind_source` column tracks which method applied to each tract

### 15-Minute Temporal Interpolation
**Status:** Active

Duration calculation interpolates all track fields (position, intensity, wind radii) to 15-minute intervals, creating moving wind polygons to test tract exposure over time.

**Validation:** Sensitivity analysis shows <5% difference vs 10-minute intervals at 2× computational cost

---

## Dependencies

### Input Data Sources
- **HURDAT2 cleaned tracks** → from `hurdat2/outputs/cleaned_data/`
- **Census tract centroids** → from `census/outputs/`
- **Storm envelopes** → generated on-the-fly from HURDAT2 wind radii

### Python Modules
```python
from hurdat2.src.parse_raw import parse_hurdat2_file
from hurdat2.src.profile_clean import clean_hurdat2_data
from hurdat2.src.envelope_algorithm import create_storm_envelope, generate_quadrant_arc_points
from census.src.tract_centroids import load_tracts_with_centroids
```

---

## Usage

### Run Full Pipeline for Single Storm
```bash
python hurdat2_census/src/storm_tract_distance.py \
    --storm-id AL092021 \
    --states 22 28 01 12 48 \
    --output hurdat2_census/outputs/features/ida_tract_features.csv
```

### Generate QA/QC Reports
```bash
python hurdat2_census/src/qaqc_comprehensive_suite.py \
    --storm-id AL092021 \
    --output-dir hurdat2_census/outputs/transformations/
```

---

## Recent Changes

**v2.1 (2025-10-05)** - Arc-based wind polygon correction
- Replaced chord-based quadrilaterals with circular arc sampling
- Added `generate_quadrant_arc_points()` for accurate wind field geometry
- Updated duration calculator to use arc polygons
- Result: 10-30% increase in wind field coverage accuracy

**v2.0 (2025-10-04)** - Lead time features added
- Multi-threshold lead time (Cat 1-5)
- `lead_time_calculator.py` module created
- Handles storms that never reach high categories (NaN vs 0)

**v1.5 (2025-10-03)** - Wind model update
- RMW plateau + decay model
- Hierarchical boundary enforcement (wind radii prioritized)
- `wind_source` metadata column added

---

## Related Documentation

- **Methodology narrative:** `hurdat2/docs/FeatureTransformationNarrative.md`
- **Algorithm improvements:** `ALGORITHM_IMPROVEMENTS_RECOMMENDATIONS.md`
- **Implementation plan:** `ARC_POLYGON_IMPLEMENTATION_PLAN.md`
- **Workflow overview:** `hurdat2/docs/hurdat_workflow.md`
