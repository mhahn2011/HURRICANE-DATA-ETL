# Repository Restructure Implementation Plan

**Date Created:** 2025-10-05
**Status:** Proposed
**Priority:** High
**Estimated Time:** 4-6 hours

---

## Objective

Reorganize the hurricane-data-etl repository to clearly separate **data sources** from **transformations**, with rich visual documentation that supports both interactive exploration (HTML) and report generation (PNG).

---

## Design Philosophy

### Core Principles

1. **Data Sources vs Transformations**
   - `data_sources/`: Single-source processing only (no cross-source dependencies)
   - `transformations/`: Multi-source feature engineering (the intellectual work)
   - `integration/`: Final assembly and validation only

2. **Self-Contained Transformation Modules**
   - Each transformation is independently documented
   - Complete methodology narrative in each folder
   - Inputs, outputs, and visuals all co-located

3. **Dual Visual Format (HTML + PNG)**
   - HTML for dynamic exploration and development
   - PNG for reports, papers, and presentations
   - Methodology visuals explain HOW (arc diagrams, parameter sensitivity)
   - Results visuals show WHAT (distributions, coverage maps)

4. **Documentation at Point of Use**
   - METHODOLOGY.md in each transformation folder
   - Not a single monolithic document
   - Easier to maintain and understand

---

## Target Structure

```
hurricane-data-etl/
│
├── data_sources/                          # Raw data ingestion & single-source processing
│   │
│   ├── hurdat2/                           # HURDAT2 hurricane tracks
│   │   ├── README.md                      # Data source description & workflow
│   │   ├── raw/                           # Original HURDAT2 text files
│   │   ├── src/                           # Parsing & cleaning scripts
│   │   │   ├── parse_raw.py
│   │   │   ├── profile_clean.py
│   │   │   └── validate_qa.py
│   │   ├── processed/                     # Cleaned data outputs
│   │   │   └── hurdat2_cleaned.csv
│   │   └── visuals/                       # Data source QA visuals
│   │       ├── html/                      # Interactive exploration
│   │       │   └── track_overview.html
│   │       └── png/                       # Report-ready images
│   │           └── track_coverage_map.png
│   │
│   ├── census/                            # Census TIGER/Line tracts
│   │   ├── README.md
│   │   ├── raw/                           # TIGER/Line shapefiles
│   │   ├── src/                           # Tract processing
│   │   │   └── extract_centroids.py
│   │   ├── processed/                     # Tract centroids & metadata
│   │   │   └── tract_centroids.geojson
│   │   └── visuals/
│   │       ├── html/
│   │       │   └── tract_map.html
│   │       └── png/
│   │           └── tract_boundaries.png
│   │
│   └── [future: rainfall/, surge/, damage/]
│
│
├── transformations/                       # Multi-source feature engineering
│   │
│   ├── wind_coverage_envelope/            # T1: Spatial extent (HURDAT2 only)
│   │   ├── README.md                      # Quick summary
│   │   ├── METHODOLOGY.md                 # Detailed algorithm explanation
│   │   ├── src/
│   │   │   ├── envelope_algorithm.py      # Alpha shape generation
│   │   │   └── wind_radii_imputation.py   # Missing data handling
│   │   ├── outputs/
│   │   │   └── {storm_id}_envelope.geojson
│   │   └── visuals/
│   │       ├── methodology/               # HOW transformation works
│   │       │   ├── html/
│   │       │   │   ├── arc_vs_chord_comparison.html
│   │       │   │   ├── imputation_before_after.html
│   │       │   │   └── alpha_shape_construction.html
│   │       │   └── png/
│   │       │       ├── arc_vs_chord_comparison.png
│   │       │       ├── imputation_explanation.png
│   │       │       └── alpha_parameter_sensitivity.png
│   │       └── results/                   # WHAT transformation produced
│   │           ├── html/
│   │           │   └── ida_envelope_interactive.html
│   │           └── png/
│   │               └── all_storms_envelopes.png
│   │
│   ├── storm_tract_distance/              # T2: Spatial relationships (HURDAT2 + Census)
│   │   ├── README.md
│   │   ├── METHODOLOGY.md
│   │   ├── src/
│   │   │   └── calculate_distances.py
│   │   ├── outputs/
│   │   │   └── {storm_id}_tract_distances.csv
│   │   └── visuals/
│   │       ├── methodology/
│   │       │   ├── html/
│   │       │   │   └── distance_classification_explanation.html
│   │       │   └── png/
│   │       │       └── distance_calculation_method.png
│   │       └── results/
│   │           ├── html/
│   │           │   └── tract_coverage_map.html
│   │           └── png/
│   │               └── distance_distribution.png
│   │
│   ├── wind_interpolation/                # T3: Wind speed estimation
│   │   ├── README.md
│   │   ├── METHODOLOGY.md                 # RMW plateau + exponential decay
│   │   ├── src/
│   │   │   └── interpolate_wind.py
│   │   ├── outputs/
│   │   │   └── {storm_id}_tract_winds.csv
│   │   └── visuals/
│   │       ├── methodology/
│   │       │   ├── html/
│   │       │   │   └── wind_decay_curves.html
│   │       │   └── png/
│   │       │       ├── rmw_plateau_concept.png
│   │       │       └── decay_function_explanation.png
│   │       └── results/
│   │           ├── html/
│   │           │   └── wind_speed_heatmap.html
│   │           └── png/
│   │               └── wind_distribution_histogram.png
│   │
│   ├── duration/                          # T4: Temporal exposure
│   │   ├── README.md
│   │   ├── METHODOLOGY.md                 # 15-min interpolation
│   │   ├── src/
│   │   │   └── calculate_duration.py
│   │   ├── outputs/
│   │   │   └── {storm_id}_tract_duration.csv
│   │   └── visuals/
│   │       ├── methodology/
│   │       │   ├── html/
│   │       │   │   ├── temporal_interpolation_animation.html
│   │       │   │   └── polygon_evolution_15min.html
│   │       │   └── png/
│   │       │       ├── temporal_resolution_comparison.png
│   │       │       └── duration_accumulation_example.png
│   │       └── results/
│   │           ├── html/
│   │           │   └── duration_by_tract.html
│   │           └── png/
│   │               └── duration_distribution.png
│   │
│   ├── lead_time/                         # T5: Warning time features
│   │   ├── README.md
│   │   ├── METHODOLOGY.md
│   │   ├── src/
│   │   │   └── calculate_lead_time.py
│   │   ├── outputs/
│   │   │   └── {storm_id}_tract_lead_time.csv
│   │   └── visuals/
│   │       ├── methodology/
│   │       │   ├── html/
│   │       │   │   └── category_threshold_detection.html
│   │       │   └── png/
│   │       │       └── lead_time_calculation_example.png
│   │       └── results/
│   │           ├── html/
│   │           │   └── lead_time_by_category.html
│   │           └── png/
│   │               └── lead_time_distributions.png
│   │
│   └── [future: compound_wind_rainfall/, surge_modeling/]
│
│
├── integration/                           # Final assembly & validation
│   ├── README.md
│   ├── src/
│   │   ├── assemble_features.py           # Combine transformation outputs
│   │   ├── filter_quality.py              # Apply quality thresholds
│   │   └── validate_consistency.py        # Cross-check features
│   ├── outputs/
│   │   └── ml_ready/                      # Final datasets
│   │       ├── storm_tract_features.csv
│   │       └── data_dictionary.csv
│   └── visuals/
│       ├── validation/                    # QA/QC of final data
│       │   ├── html/
│       │   │   └── validation_dashboard.html
│       │   └── png/
│       │       ├── feature_completeness.png
│       │       └── cross_validation_checks.png
│       └── results/                       # Summary visuals
│           ├── html/
│           │   └── final_feature_explorer.html
│           └── png/
│               ├── all_storms_summary.png
│               └── feature_correlation_matrix.png
│
│
├── shared/                                # Shared utilities
│   ├── geometry_utils.py                  # Haversine, bearing calculations
│   ├── time_utils.py                      # Temporal interpolation
│   └── visualization_utils.py             # Common plotting functions
│
│
├── tests/                                 # Unit & integration tests
│   ├── data_sources/
│   │   ├── test_hurdat2_parsing.py
│   │   └── test_census_extraction.py
│   ├── transformations/
│   │   ├── test_envelope_algorithm.py
│   │   ├── test_wind_interpolation.py
│   │   ├── test_duration_calculation.py
│   │   └── test_lead_time.py
│   └── integration/
│       └── test_feature_assembly.py
│
│
├── IMPLEMENTATION_PLANS/                  # Implementation documentation
│   └── REPOSITORY_RESTRUCTURE_PLAN.md     # This file
│
│
└── docs/                                  # Project-level documentation
    ├── README.md                          # Repository overview
    ├── DESIGN_PHILOSOPHY.md               # Architecture rationale
    ├── GETTING_STARTED.md                 # Setup & quickstart
    ├── DATA_SOURCES_OVERVIEW.md           # All data sources catalog
    ├── TRANSFORMATIONS_OVERVIEW.md        # All transformations catalog
    └── VALIDATION_RESULTS.md              # Cross-storm validation
```

---

## Implementation Phases

### Phase 1: Create Directory Structure (30 minutes)

**Goal:** Establish complete folder hierarchy

**Commands:**
```bash
cd /Users/Michael/hurricane-data-etl

# Create data_sources hierarchy
mkdir -p data_sources/hurdat2/{raw,processed,src,visuals/{html,png}}
mkdir -p data_sources/census/{raw,processed,src,visuals/{html,png}}

# Create transformations hierarchy
mkdir -p transformations/wind_coverage_envelope/{src,outputs,visuals/{methodology/{html,png},results/{html,png}}}
mkdir -p transformations/storm_tract_distance/{src,outputs,visuals/{methodology/{html,png},results/{html,png}}}
mkdir -p transformations/wind_interpolation/{src,outputs,visuals/{methodology/{html,png},results/{html,png}}}
mkdir -p transformations/duration/{src,outputs,visuals/{methodology/{html,png},results/{html,png}}}
mkdir -p transformations/lead_time/{src,outputs,visuals/{methodology/{html,png},results/{html,png}}}

# Create integration hierarchy
mkdir -p integration/{src,outputs/ml_ready,visuals/{validation/{html,png},results/{html,png}}}

# Create tests hierarchy
mkdir -p tests/{data_sources,transformations,integration}

# Create shared utilities
mkdir -p shared
```

**Validation:**
- Run `tree -L 3 data_sources transformations integration` to verify structure
- Ensure all `visuals/{methodology,results}/{html,png}` directories exist

---

### Phase 2: Move Data Source Files (45 minutes)

**Goal:** Reorganize single-source processing code and data

#### HURDAT2 Data Source

**Move raw data:**
```bash
# Current: hurdat2/input_data/
# Target:  data_sources/hurdat2/raw/
mv hurdat2/input_data/* data_sources/hurdat2/raw/
```

**Move processed data:**
```bash
# Current: hurdat2/outputs/cleaned_data/
# Target:  data_sources/hurdat2/processed/
mv hurdat2/outputs/cleaned_data/* data_sources/hurdat2/processed/
```

**Move source code:**
```bash
# Single-source processing only
cp hurdat2/src/parse_raw.py data_sources/hurdat2/src/
cp hurdat2/src/profile_clean.py data_sources/hurdat2/src/

# NOTE: envelope_algorithm.py moves to transformations (uses only HURDAT2 but creates features)
```

**Move QA visuals:**
```bash
# Current: hurdat2/outputs/qa_maps/
# Target:  data_sources/hurdat2/visuals/html/
mv hurdat2/outputs/qa_maps/*.html data_sources/hurdat2/visuals/html/
```

#### Census Data Source

**Move raw data:**
```bash
# Current: census/data/
# Target:  data_sources/census/raw/
mv census/data/* data_sources/census/raw/
```

**Move source code:**
```bash
# Current: census/src/
# Target:  data_sources/census/src/
mv census/src/* data_sources/census/src/
```

**Move processed data:**
```bash
# Current: census/outputs/
# Target:  data_sources/census/processed/
mv census/outputs/* data_sources/census/processed/
```

**Validation:**
- Verify all raw HURDAT2 text files in `data_sources/hurdat2/raw/`
- Verify cleaned CSVs in `data_sources/hurdat2/processed/`
- Verify tract shapefiles in `data_sources/census/raw/`

---

### Phase 3: Move Transformation Files (1.5 hours)

**Goal:** Organize multi-source feature engineering by transformation type

#### T1: Wind Coverage Envelope

**Move source code:**
```bash
# Current: hurdat2/src/envelope_algorithm.py
# Target:  transformations/wind_coverage_envelope/src/
mv hurdat2/src/envelope_algorithm.py transformations/wind_coverage_envelope/src/
```

**Move outputs:**
```bash
# Current: hurdat2/outputs/envelopes/
# Target:  transformations/wind_coverage_envelope/outputs/
mv hurdat2/outputs/envelopes/* transformations/wind_coverage_envelope/outputs/
```

**Move visuals:**
```bash
# Methodology visuals (arc vs chord, imputation, alpha shape)
# Current: hurdat2/outputs/transformations/
# Target:  transformations/wind_coverage_envelope/visuals/methodology/html/
mv hurdat2/outputs/transformations/arc_vs_chord*.html transformations/wind_coverage_envelope/visuals/methodology/html/
mv hurdat2/outputs/transformations/imputation*.html transformations/wind_coverage_envelope/visuals/methodology/html/
mv hurdat2/outputs/transformations/alpha_shape*.html transformations/wind_coverage_envelope/visuals/methodology/html/

# Results visuals (envelope maps)
mv hurdat2/outputs/envelopes/*.html transformations/wind_coverage_envelope/visuals/results/html/
```

#### T2: Storm-Tract Distance

**Move source code:**
```bash
# Current: hurdat2_census/src/storm_tract_distance.py
# Target:  transformations/storm_tract_distance/src/
mv hurdat2_census/src/storm_tract_distance.py transformations/storm_tract_distance/src/
```

**Move outputs:**
```bash
# Current: hurdat2_census/outputs/features/*_tract_distances.csv
# Target:  transformations/storm_tract_distance/outputs/
mv hurdat2_census/outputs/features/*_tract_distances.csv transformations/storm_tract_distance/outputs/
```

**Move visuals:**
```bash
# Distance QA/QC maps
# Current: integration/outputs/qaqc_distance.html
# Target:  transformations/storm_tract_distance/visuals/results/html/
mv integration/outputs/qaqc_*.html transformations/storm_tract_distance/visuals/results/html/ 2>/dev/null || true
```

#### T3: Wind Interpolation

**Move source code:**
```bash
# Current: hurdat2_census/src/wind_interpolation.py
# Target:  transformations/wind_interpolation/src/
mv hurdat2_census/src/wind_interpolation.py transformations/wind_interpolation/src/
```

**Move outputs:**
```bash
# Wind features embedded in main feature tables - no separate files
# (This transformation is called by storm_tract_distance.py)
```

**Move visuals:**
```bash
# Wind QA/QC visuals
# Current: integration/outputs/qaqc_wind*.html
# Target:  transformations/wind_interpolation/visuals/results/html/
mv integration/outputs/qaqc_wind*.html transformations/wind_interpolation/visuals/results/html/ 2>/dev/null || true
```

#### T4: Duration

**Move source code:**
```bash
# Current: hurdat2_census/src/duration_calculator.py
# Target:  transformations/duration/src/
mv hurdat2_census/src/duration_calculator.py transformations/duration/src/
```

**Move outputs:**
```bash
# Duration features embedded in main feature tables
# (Part of storm_tract_distance.py pipeline)
```

**Move visuals:**
```bash
# Duration QA/QC visuals
# Current: integration/outputs/qaqc_duration*.html
# Target:  transformations/duration/visuals/results/html/
mv integration/outputs/qaqc_duration*.html transformations/duration/visuals/results/html/ 2>/dev/null || true
```

#### T5: Lead Time

**Move source code:**
```bash
# Current: hurdat2_census/src/lead_time_calculator.py
# Target:  transformations/lead_time/src/
mv hurdat2_census/src/lead_time_calculator.py transformations/lead_time/src/
```

**Move outputs:**
```bash
# Lead time features in main tables
```

**Move visuals:**
```bash
# Lead time QA/QC visuals
# Current: integration/outputs/qaqc_lead_time*.html
# Target:  transformations/lead_time/visuals/results/html/
mv integration/outputs/qaqc_lead_time*.html transformations/lead_time/visuals/results/html/ 2>/dev/null || true
```

**Validation:**
- Verify each transformation has source code in `src/`
- Verify visuals separated into `methodology/` and `results/`
- Check that HTML files are in appropriate locations

---

### Phase 4: Update Integration Folder (30 minutes)

**Goal:** Keep only final assembly and validation

**Keep in integration/src/:**
```bash
# These stay (final assembly only)
integration/src/feature_pipeline.py
integration/src/assemble_features.py (if exists)
integration/src/validate_consistency.py (if exists)
```

**Move to integration/outputs/ml_ready/:**
```bash
# Current: integration/outputs/final/
# Target:  integration/outputs/ml_ready/
mv integration/outputs/final/* integration/outputs/ml_ready/ 2>/dev/null || true
```

**Organize integration visuals:**
```bash
# Validation visuals
mkdir -p integration/visuals/validation/html
mv integration/outputs/validation/*.html integration/visuals/validation/html/ 2>/dev/null || true

# Results visuals (summary across all storms)
mkdir -p integration/visuals/results/html
mv integration/outputs/results/*.html integration/visuals/results/html/ 2>/dev/null || true
```

**Validation:**
- Verify `integration/src/` contains only assembly/validation code
- Verify no transformation logic remains in integration
- Check ML-ready datasets are in `outputs/ml_ready/`

---

### Phase 5: Update Import Paths (1 hour)

**Goal:** Fix all broken imports after file moves

**Strategy:**
1. Use shared utilities for common functions
2. Update transformation imports to new paths
3. Update integration imports

**Files to update:**

#### Create shared utilities:
```python
# shared/geometry_utils.py
# Move from envelope_algorithm.py:
- calculate_destination_point()
- haversine_distance()
- calculate_bearing()

# shared/time_utils.py
# Move from duration_calculator.py:
- interpolate_temporal_positions()
- generate_15min_intervals()

# shared/visualization_utils.py
# Common plotting functions
```

#### Update transformation imports:

**File: `transformations/storm_tract_distance/src/calculate_distances.py`**
```python
# OLD:
from hurdat2_census.src.wind_interpolation import interpolate_wind_speed
from hurdat2_census.src.duration_calculator import calculate_duration

# NEW:
from transformations.wind_interpolation.src.interpolate_wind import interpolate_wind_speed
from transformations.duration.src.calculate_duration import calculate_duration
from shared.geometry_utils import haversine_distance, calculate_bearing
```

**File: `transformations/wind_coverage_envelope/src/envelope_algorithm.py`**
```python
# NEW:
from shared.geometry_utils import calculate_destination_point, haversine_distance
```

**File: `transformations/duration/src/calculate_duration.py`**
```python
# NEW:
from shared.time_utils import interpolate_temporal_positions
from shared.geometry_utils import haversine_distance
```

#### Update integration imports:

**File: `integration/src/feature_pipeline.py`**
```python
# OLD:
from hurdat2_census.src.storm_tract_distance import calculate_storm_tract_features

# NEW:
from transformations.storm_tract_distance.src.calculate_distances import calculate_storm_tract_features
from data_sources.hurdat2.src.parse_raw import load_hurdat2
from data_sources.census.src.extract_centroids import load_tract_centroids
```

**Validation:**
- Run `python -m pytest tests/` to catch import errors
- Test each transformation module independently
- Verify integration pipeline runs end-to-end

---

### Phase 6: Create Documentation Files (2 hours)

**Goal:** Create README.md and METHODOLOGY.md for each module

#### Data Source READMEs

**File: `data_sources/hurdat2/README.md`**
```markdown
# HURDAT2 Hurricane Track Data

## Overview
HURDAT2 (Hurricane Database 2) provides best-track data for Atlantic and Pacific hurricanes.

## Data Source
- **Provider:** NOAA National Hurricane Center
- **URL:** https://www.nhc.noaa.gov/data/hurdat/
- **Format:** Fixed-width text file
- **Temporal Coverage:** 1851-present
- **Update Frequency:** Annual (post-season reanalysis)

## Processing Workflow
1. **Raw data:** `raw/hurdat2_atlantic.txt`
2. **Parsing:** `src/parse_raw.py` → Converts to structured CSV
3. **Cleaning:** `src/profile_clean.py` → Validates & removes errors
4. **Output:** `processed/hurdat2_cleaned.csv`

## Quality Assurance
- **Visuals:** `visuals/html/track_overview.html`
- **Validation:** Check for missing timestamps, invalid coordinates

## Key Fields
- `storm_id`: Unique identifier (e.g., AL092021 for Ida)
- `timestamp`: 6-hourly observations (UTC)
- `lat`, `lon`: Storm center position
- `max_wind`: Maximum sustained wind (kt)
- `wind_radii_ne/se/sw/nw_64kt`: 64kt wind extent by quadrant (nm)

## Usage
```python
from data_sources.hurdat2.src.parse_raw import load_hurdat2
df = load_hurdat2('data_sources/hurdat2/raw/hurdat2_atlantic.txt')
```
```

**File: `data_sources/census/README.md`**
```markdown
# US Census Tract Data

## Overview
Census tract boundaries and centroids for spatial analysis.

## Data Source
- **Provider:** US Census Bureau
- **Product:** TIGER/Line Shapefiles
- **URL:** https://www.census.gov/geographies/mapping-files.html
- **Year:** 2020 (latest decennial census)

## Processing Workflow
1. **Raw data:** `raw/*.shp` (TIGER/Line shapefiles)
2. **Extraction:** `src/extract_centroids.py` → Calculate centroids
3. **Output:** `processed/tract_centroids.geojson`

## Quality Assurance
- **Visuals:** `visuals/html/tract_map.html`
- **Validation:** Check for null geometries, invalid polygons

## Key Fields
- `GEOID`: 11-digit census tract identifier
- `centroid_lat`, `centroid_lon`: Tract centroid coordinates
- `land_area_sqkm`: Land area (for density calculations)

## Usage
```python
from data_sources.census.src.extract_centroids import load_tract_centroids
gdf = load_tract_centroids('data_sources/census/processed/tract_centroids.geojson')
```
```

#### Transformation READMEs & METHODOLOGY.md

**File: `transformations/wind_coverage_envelope/README.md`**
```markdown
# Wind Coverage Envelope Transformation

## Purpose
Creates a spatial envelope (concave hull) around hurricane wind field extent using alpha shapes.

## Inputs
- HURDAT2 cleaned data: `data_sources/hurdat2/processed/hurdat2_cleaned.csv`

## Outputs
- Envelope polygons: `outputs/{storm_id}_envelope.geojson`

## Key Algorithm
- Arc-based wind field geometry (30 points per quadrant)
- Proportional wind radii imputation for missing data
- Segmented alpha shape (α=0.6) with 30km gap threshold

## Visuals
- **Methodology:** Arc vs chord comparison, imputation examples, alpha shape construction
- **Results:** Envelope maps for each storm

## Usage
```python
from transformations.wind_coverage_envelope.src.envelope_algorithm import create_wind_coverage_envelope
envelope = create_wind_coverage_envelope(storm_df, alpha=0.6, max_gap_km=30)
```

## Documentation
See `METHODOLOGY.md` for detailed algorithm explanation.
```

**File: `transformations/wind_coverage_envelope/METHODOLOGY.md`**
```markdown
# Wind Coverage Envelope: Methodology

[Extract relevant sections from hurdat2/docs/FeatureTransformationNarrative.md]

## 1. Arc-Based Wind Field Geometry

### Problem
HURDAT2 wind radii are radial distances, not chord lengths. Straight-line quadrilaterals underestimate area by 10-30%.

### Solution
Sample 30 points along each 90° arc using spherical trigonometry:

```python
def generate_quadrant_arc_points(center_lat, center_lon, radius_nm,
                                  start_bearing, end_bearing, num_points=30):
    bearings = np.linspace(start_bearing, end_bearing, num_points)
    points = []
    for bearing in bearings:
        dest_lon, dest_lat = calculate_destination_point(
            center_lat, center_lon, bearing, radius_nm
        )
        points.append((dest_lon, dest_lat))
    return points
```

### Validation
- Expected area increase: 10-30% vs chord-based polygons
- Tested on Hurricane Ida (2021)

## 2. Wind Radii Imputation

[Continue with detailed sections...]
```

**Repeat for all transformations:**
- `transformations/storm_tract_distance/README.md` + `METHODOLOGY.md`
- `transformations/wind_interpolation/README.md` + `METHODOLOGY.md`
- `transformations/duration/README.md` + `METHODOLOGY.md`
- `transformations/lead_time/README.md` + `METHODOLOGY.md`

**Template for each METHODOLOGY.md:**
1. Problem statement
2. Algorithm description
3. Mathematical formulation
4. Parameter choices & justification
5. Limitations & assumptions
6. Validation approach

**Validation:**
- Each transformation has both README.md and METHODOLOGY.md
- README is concise (1 page)
- METHODOLOGY is comprehensive (3-5 pages)

---

### Phase 7: Migrate Tests (30 minutes)

**Goal:** Organize tests to match new structure

**Move test files:**
```bash
# Data source tests
mv tests/test_hurdat2_parsing.py tests/data_sources/ 2>/dev/null || true
mv tests/test_census_extraction.py tests/data_sources/ 2>/dev/null || true

# Transformation tests
mv tests/test_envelope_algorithm.py tests/transformations/ 2>/dev/null || true
mv tests/test_wind_interpolation.py tests/transformations/ 2>/dev/null || true
mv tests/test_duration_calculator.py tests/transformations/test_duration.py 2>/dev/null || true
mv tests/test_lead_time.py tests/transformations/ 2>/dev/null || true
mv tests/test_arc_polygons.py tests/transformations/ 2>/dev/null || true

# Integration tests
mv tests/test_feature_pipeline.py tests/integration/ 2>/dev/null || true
```

**Update test imports:**
```python
# tests/transformations/test_envelope_algorithm.py
# OLD:
from hurdat2.src.envelope_algorithm import create_wind_coverage_envelope

# NEW:
from transformations.wind_coverage_envelope.src.envelope_algorithm import create_wind_coverage_envelope
```

**Validation:**
- Run `pytest tests/data_sources/`
- Run `pytest tests/transformations/`
- Run `pytest tests/integration/`
- Verify all tests pass with new structure

---

### Phase 8: Update Path References in Scripts (45 minutes)

**Goal:** Fix hardcoded paths in all scripts

**Files to update:**

#### Transformation scripts

**File: `transformations/wind_coverage_envelope/src/envelope_algorithm.py`**
```python
# Update any hardcoded paths
# OLD:
INPUT_PATH = '../input_data/hurdat2_atlantic.txt'
OUTPUT_PATH = '../outputs/envelopes/'

# NEW:
INPUT_PATH = '../../data_sources/hurdat2/processed/hurdat2_cleaned.csv'
OUTPUT_PATH = '../outputs/'
```

**File: `transformations/storm_tract_distance/src/calculate_distances.py`**
```python
# OLD:
HURDAT2_PATH = '../../hurdat2/outputs/cleaned_data/hurdat2_cleaned.csv'
CENSUS_PATH = '../../census/outputs/tract_centroids.geojson'

# NEW:
HURDAT2_PATH = '../../data_sources/hurdat2/processed/hurdat2_cleaned.csv'
CENSUS_PATH = '../../data_sources/census/processed/tract_centroids.geojson'
```

#### Integration scripts

**File: `integration/src/feature_pipeline.py`**
```python
# Update all input paths to point to transformation outputs
ENVELOPE_PATH = '../../transformations/wind_coverage_envelope/outputs/'
DISTANCE_PATH = '../../transformations/storm_tract_distance/outputs/'
OUTPUT_PATH = '../outputs/ml_ready/'
```

**Strategy:**
- Use relative paths from script location
- Or use environment variables for project root
- Document expected paths in each README.md

**Validation:**
- Run each script independently
- Verify outputs land in correct directories
- Check that scripts can find input files

---

### Phase 9: Create Top-Level Documentation (1 hour)

**Goal:** Update project-level docs to reflect new structure

**File: `docs/README.md`** (Main project README)
```markdown
# Hurricane Data ETL Pipeline

## Overview
Extracts hurricane impact features for census tract-level analysis.

## Repository Structure

### Data Sources
- `data_sources/hurdat2/` - HURDAT2 hurricane tracks
- `data_sources/census/` - Census tract boundaries

### Transformations
- `transformations/wind_coverage_envelope/` - Spatial extent envelopes
- `transformations/storm_tract_distance/` - Distance classifications
- `transformations/wind_interpolation/` - Wind speed estimation
- `transformations/duration/` - Temporal exposure
- `transformations/lead_time/` - Warning time features

### Integration
- `integration/` - Final feature assembly and validation

## Quick Start
[Installation, setup, running pipeline]

## Documentation
- `docs/DATA_SOURCES_OVERVIEW.md` - All data sources
- `docs/TRANSFORMATIONS_OVERVIEW.md` - All transformations
- `docs/DESIGN_PHILOSOPHY.md` - Architecture decisions
```

**File: `docs/DATA_SOURCES_OVERVIEW.md`**
```markdown
# Data Sources Overview

## HURDAT2
- **Location:** `data_sources/hurdat2/`
- **Description:** [Brief description]
- **Documentation:** `data_sources/hurdat2/README.md`

## Census Tracts
- **Location:** `data_sources/census/`
- **Description:** [Brief description]
- **Documentation:** `data_sources/census/README.md`
```

**File: `docs/TRANSFORMATIONS_OVERVIEW.md`**
```markdown
# Transformations Overview

## T1: Wind Coverage Envelope
- **Location:** `transformations/wind_coverage_envelope/`
- **Purpose:** Create spatial extent using alpha shapes
- **Inputs:** HURDAT2 cleaned data
- **Outputs:** Envelope polygons
- **Documentation:** `transformations/wind_coverage_envelope/METHODOLOGY.md`

[Repeat for all transformations]
```

**File: `docs/DESIGN_PHILOSOPHY.md`**
```markdown
# Design Philosophy

## Separation of Concerns
1. **Data Sources:** Single-source processing
2. **Transformations:** Multi-source feature engineering
3. **Integration:** Final assembly

## Visual Documentation
- **HTML:** Interactive exploration
- **PNG:** Report-ready exports
- **Methodology vs Results:** How vs What

[Continue with design rationale]
```

**Validation:**
- All top-level docs reference correct paths
- Links between docs work correctly
- New contributor can navigate repository

---

### Phase 10: Generate PNG Exports (Ongoing)

**Goal:** Create report-ready static images from HTML visuals

**Strategy:**
1. Use Playwright or Selenium for automated screenshots
2. Or manually export key frames from HTML
3. Store in parallel `png/` directories

**Example automation script:**
```python
# scripts/export_html_to_png.py
from playwright.sync_api import sync_playwright
import os

def export_html_to_png(html_path, png_path, width=1200, height=800):
    """Convert HTML file to PNG screenshot."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': width, 'height': height})
        page.goto(f'file://{os.path.abspath(html_path)}')
        page.screenshot(path=png_path, full_page=True)
        browser.close()

# Export all methodology visuals
html_files = [
    'transformations/wind_coverage_envelope/visuals/methodology/html/arc_vs_chord_comparison.html',
    'transformations/wind_interpolation/visuals/methodology/html/wind_decay_curves.html',
    # ... etc
]

for html_file in html_files:
    png_file = html_file.replace('/html/', '/png/').replace('.html', '.png')
    export_html_to_png(html_file, png_file)
```

**Manual export process:**
1. Open HTML in browser
2. Take screenshot (Cmd+Shift+4 on Mac)
3. Save to corresponding `png/` directory
4. Name consistently (same base name as HTML)

**Priority PNGs:**
- Arc vs chord comparison
- Wind decay curves
- Duration accumulation examples
- Lead time calculation diagrams
- Final feature distributions

**Validation:**
- Each key HTML has corresponding PNG
- PNGs are high resolution (min 1200px width)
- File names match HTML names

---

## Post-Migration Tasks

### Update Git

**Track moves in git:**
```bash
git add -A
git status  # Review all moves
git commit -m "refactor: reorganize repository into data_sources and transformations structure

- Separate data sources (hurdat2, census) from transformations
- Create self-contained transformation modules with methodology docs
- Add dual visual format (HTML + PNG) support
- Update all import paths and documentation

See IMPLEMENTATION_PLANS/REPOSITORY_RESTRUCTURE_PLAN.md for details"
```

### Clean Up Old Directories

**Remove empty directories:**
```bash
# After verifying all files moved successfully
rmdir hurdat2/input_data 2>/dev/null
rmdir hurdat2/outputs/cleaned_data 2>/dev/null
rmdir hurdat2/outputs/envelopes 2>/dev/null
rmdir hurdat2_census/outputs/features 2>/dev/null
# etc.

# OR keep old structure temporarily as backup
mv hurdat2 _old_hurdat2
mv hurdat2_census _old_hurdat2_census
```

### Update .gitignore

**Add entries:**
```bash
# .gitignore additions
data_sources/*/raw/*
!data_sources/*/raw/.gitkeep
transformations/*/outputs/*
!transformations/*/outputs/.gitkeep
integration/outputs/ml_ready/*
!integration/outputs/ml_ready/.gitkeep
*.png  # If PNGs are generated, not committed
```

### Update CI/CD (if applicable)

**Update test paths:**
```yaml
# .github/workflows/tests.yml (if exists)
- name: Run tests
  run: |
    pytest tests/data_sources/
    pytest tests/transformations/
    pytest tests/integration/
```

---

## Validation Checklist

### Structure Validation
- [ ] All `data_sources/` folders have `README.md`
- [ ] All `transformations/` folders have `README.md` + `METHODOLOGY.md`
- [ ] All visual folders have `html/` and `png/` subdirectories
- [ ] Integration contains only assembly/validation code

### Code Validation
- [ ] All imports updated to new paths
- [ ] Shared utilities extracted to `shared/`
- [ ] No circular dependencies
- [ ] All scripts run without path errors

### Test Validation
- [ ] All tests pass: `pytest tests/`
- [ ] Tests organized by module type
- [ ] No broken imports in test files

### Documentation Validation
- [ ] Top-level README.md updated
- [ ] Each data source has README.md
- [ ] Each transformation has README.md + METHODOLOGY.md
- [ ] All paths in docs are correct

### Visual Validation
- [ ] HTML visuals in correct `methodology/` or `results/` folders
- [ ] Key HTML files have corresponding PNGs
- [ ] Visuals render correctly (no broken paths)

### End-to-End Validation
- [ ] Can run full pipeline from data sources → transformations → integration
- [ ] Outputs land in expected directories
- [ ] Final ML-ready datasets generated successfully

---

## Rollback Plan

If issues arise during migration:

1. **Keep old structure temporarily:**
   ```bash
   # Don't delete old folders immediately
   # Rename instead
   mv hurdat2 _backup_hurdat2
   mv hurdat2_census _backup_hurdat2_census
   ```

2. **Test incrementally:**
   - Migrate one transformation at a time
   - Verify it works before moving to next

3. **Git branches:**
   ```bash
   git checkout -b feature/repository-restructure
   # Do all work on branch
   # Only merge when fully validated
   ```

---

## Benefits Summary

✅ **Clear narrative flow:** Data source → Transformation → Integration
✅ **Self-documenting:** Each folder tells its own story
✅ **Report-ready:** PNG visuals for papers/presentations
✅ **Modular testing:** Each transformation independently testable
✅ **Easy onboarding:** New contributors can understand one module at a time
✅ **Future-proof:** Easy to add new data sources or transformations
✅ **Version control friendly:** Clear separation reduces merge conflicts

---

## Timeline Estimate

| Phase | Task | Time |
|-------|------|------|
| 1 | Create directory structure | 30 min |
| 2 | Move data source files | 45 min |
| 3 | Move transformation files | 1.5 hrs |
| 4 | Update integration folder | 30 min |
| 5 | Update import paths | 1 hr |
| 6 | Create documentation files | 2 hrs |
| 7 | Migrate tests | 30 min |
| 8 | Update path references | 45 min |
| 9 | Create top-level docs | 1 hr |
| 10 | Generate PNG exports | Ongoing |
| **Total** | | **~9 hours** |

With testing and validation, expect **1-2 days** for complete migration.

---

## Questions for Review

Before starting implementation:

1. **Naming conventions:**
   - OK with `data_sources/` vs `sources/`?
   - OK with `transformations/` vs `features/`?

2. **Shared utilities:**
   - Extract to `shared/` or keep in transformations?
   - Preference for utility organization?

3. **Visual exports:**
   - Automate PNG generation or manual?
   - Commit PNGs to git or generate on demand?

4. **Old structure:**
   - Keep as backup temporarily?
   - Or delete immediately after migration?

5. **Migration approach:**
   - All at once or incremental (one transformation at a time)?
   - Use git branch or work on main?

---

## Status: READY FOR REVIEW

**Next Step:** Review plan with team, address questions, then begin Phase 1.

**Contact:** Update this plan with decisions and begin execution.
