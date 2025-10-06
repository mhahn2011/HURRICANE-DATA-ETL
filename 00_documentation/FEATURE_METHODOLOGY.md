# Feature Methodology

**Last Updated:** 2025-10-05
**Status:** Arc Geometry Implemented ✅

---

## Overview

This document describes the algorithms and transformations used to extract hurricane impact features from HURDAT2 track data and US Census tract boundaries.

**Core Output:** Census tract-level features including wind speed, exposure duration, and lead time for machine learning applications.

---

## Computational Environment

### Coordinate Reference System
**EPSG:4326 (WGS84 lat/lon)**
- All geometries constructed in geographic coordinates (decimal degrees)
- Short-segment planar approximation for Shapely operations (<200 nm segments, error <0.1%)
- Great-circle calculations via custom spherical trigonometry
- Earth radius: 3440.065 NM (nautical miles)

### Key Libraries
- `shapely` 2.x - Polygon operations, spatial predicates, distance calculations
- `scipy.spatial.Delaunay` - Alpha shape triangulation (custom implementation)
- `numpy` - Array operations and linear interpolation
- `pandas` - Time series handling and temporal interpolation

### Precision Specifications
- **Spatial precision:** ±0.1 nm for segments <200 nm
- **Angular precision:** 1e-6 degrees in bearing calculations
- **Temporal precision:** Linear interpolation in UTC, precision to nearest second (no DST adjustments)
- **Polygon validity:** Auto-repair via `.buffer(0)` for self-intersections

---

## Feature 1: Arc-Based Wind Field Geometry

### Status: ✅ IMPLEMENTED (2025-10-05)

**Problem Solved:**
Previous implementation used straight chords between quadrant extent points, creating a diamond/quadrilateral shape. This systematically underestimated wind field area by 10-30% because HURDAT2 wind radii represent radial distances (circular arcs), not chord lengths.

### Implementation

**Arc Generation:**
Each quadrant (NE, SE, SW, NW) is sampled along its 90° circular arc with 30 points:

```
Quadrant bearings:
- NE: 45° to 135°  (30 sample points)
- SE: 135° to 225° (30 sample points)
- SW: 225° to 315° (30 sample points)
- NW: 315° to 45°  (30 sample points, wraps around 360°→0°)

Total: 120 points defining smooth circular boundary
```

**Function:** `generate_quadrant_arc_points()` in `02_transformations/wind_coverage_envelope/src/envelope_algorithm.py`

**Impact:**
- Wind field polygons now accurately represent radial extent
- Area increase: 10-30% compared to chord method
- Affects all downstream features (distance, wind speed, duration)

**Validation:**
- Test: `05_tests/test_arc_polygons.py::test_arc_polygon_area_exceeds_chord_polygon`
- Verified: Arc polygons consistently >5% larger than chord equivalents

---

## Feature 2: Wind Coverage Envelope (Alpha Shapes)

**Purpose:** Create concave hull around storm's complete wind field extent

### Algorithm

**Stage 1: Spherical Projection**
For each 6-hourly track observation, calculate geographic coordinates of wind radii extent points using great-circle navigation:

```
For each quadrant (NE, SE, SW, NW):
  - Sample 30 points along 90° arc
  - Use haversine forward formula to project from storm center
  - Inputs: center (lat, lon), bearing, radius (nm)
  - Output: Destination point (lat, lon)
```

**Stage 2: Wind Radii Imputation**
Handle missing wind radii data with proportional imputation:

```
Imputation triggers:
  - Current observation has ≥2 quadrants defined, OR
  - Previous observation has ≥2 quadrants defined

Imputation method:
  - Calculate shrinkage ratio from overlapping quadrants
  - Apply ratio to missing quadrants
  - Example: If NE decreased 60nm→45nm (ratio=0.75), apply 0.75 to impute SW

Metadata:
  - Track source with `was_imputed` flag
  - Propagate NaN when <2 quadrants available
```

**Meteorological Justification:**
Assumes radial coherence - adjacent wind field quadrants tend to expand/contract together during symmetric intensification. May over-extend inland quadrants during land interaction (friction asymmetrically shrinks one side).

**Stage 3: Segmented Alpha Shape**
Construct concave hull using alpha shape algorithm:

```
Alpha parameter: α = 0.6
- Derived through sensitivity analysis on Katrina, Rita, Ida
- Test range: [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
- Criteria: Visual coastal realism, area ratio, no spurious corridors
- Result: 0.6 balances tight fitting without over-fragmentation

Segmentation threshold: 5 consecutive missing observations
- <5: Over-fragmentation (separate hulls for transient gaps)
- >5: False bridges across true data voids
- Typical gap causes: Landfall, extratropical transition, pre-2004 data
```

**Implementation:** `02_transformations/wind_coverage_envelope/src/envelope_algorithm.py`

---

## Feature 3: Wind Speed Interpolation

**Purpose:** Estimate maximum wind speed experienced at tract centroid

### Two-Regime Model

**Regime 1: RMW Plateau**
```
If distance_to_track ≤ radius_max_wind:
  wind_speed = max_wind
  inside_eyewall = True
```

**Regime 2: Exponential Decay**
```
If distance_to_track > radius_max_wind:
  wind_speed = max_wind × exp(-0.15 × (distance - rmw) / rmw)
  inside_eyewall = False
```

**Parameters:**
- RMW (Radius of Maximum Winds): From HURDAT2 `radius_max_wind` column
- Fallback: 20 nm default if RMW missing
- Decay constant: 0.15 (empirically derived)

**Source Tracking:**
Each wind estimate tagged with `wind_source`:
- `rmw_plateau` - Within eyewall
- `decay` - Outside eyewall, exponential model
- `missing` - Insufficient data

**Implementation:** `02_transformations/wind_interpolation/src/wind_interpolation.py`

---

## Feature 4: Duration Calculation

**Purpose:** Calculate hours of exposure to wind threshold (e.g., 64kt winds)

### Method: 15-Minute Temporal Interpolation

**Interpolation:**
```
From 6-hourly observations:
  - Generate 15-minute intervals (24 timesteps between observations)
  - Linear interpolation of lat, lon, wind radii
  - Preserves storm motion smoothness (10-30mph → 2.5-7.5 miles per 15-min)
```

**Sensitivity Analysis:**
- 10-min intervals: <5% difference, 2× computational cost
- 20-min intervals: <8% difference, 75% of 15-min cost
- **Selected: 15-min** for balance of accuracy and performance

**Duration Accumulation:**
```
For each 15-min timestep:
  1. Create instantaneous wind polygon (arc-based)
  2. Check if tract centroid inside polygon
  3. If inside: accumulate 0.25 hours

Total duration = sum of exposure intervals
Minimum threshold: 0.25 hours (filters noise)
```

**Source Tracking:**
- `observed` - Based on 6-hourly HURDAT2 data
- `imputed` - Based on imputed wind radii
- `interpolated` - Based on 15-min temporal interpolation

**Implementation:** `02_transformations/duration/src/duration_calculator.py`

---

## Feature 5: Lead Time

**Purpose:** Calculate warning time before storm reaches category threshold at tract location

### Category Thresholds (Saffir-Simpson Scale)
```
Cat 1: 64 kt
Cat 2: 83 kt
Cat 3: 96 kt
Cat 4: 113 kt
Cat 5: 137 kt
```

### Algorithm

**For each category threshold:**
```
1. Find first timestep where max_wind ≥ threshold
2. Calculate time difference: threshold_time - current_time
3. Calculate distance to tract at threshold crossing
4. Output:
   - lead_time_catN_hours: Hours of warning
   - lead_time_catN_distance_km: Distance when threshold reached
```

**Edge Cases:**
- Storm never reaches threshold → `null`
- Storm already at threshold → lead_time = 0
- Multiple crossings → use first occurrence

**Implementation:** `02_transformations/lead_time/src/lead_time_calculator.py`

---

## Data Quality & Validation

### Imputation Tracking

All imputed/interpolated data flagged:
- `was_imputed` - Wind radii filled from previous observation
- `duration_source` - Source of duration estimate
- `wind_source` - Source of wind estimate

### Quality Filters

Applied in `03_integration/`:
- Minimum duration: 0.25 hours (15 minutes)
- Remove tracts with all-missing wind radii
- Validate polygon geometries (no self-intersections)

### Validation Approach

**Cross-validation with NOAA advisories:**
- Compare envelope extents with advisory wind extent graphics
- Spot-check wind speeds against station observations (ASOS/METAR)
- Verify temporal progression against advisory timestamps

**Test coverage:**
- Unit tests: `05_tests/test_*.py` (13 test files)
- Integration tests: Full pipeline runs on Hurricane Ida
- Validation: 14 historical Gulf Coast hurricanes (2005-2022)

---

## Known Limitations

### Addressed ✅
- **Arc geometry** - FIXED: Now uses true circular arcs (30 points per quadrant)
- **Wind radii imputation** - IMPLEMENTED: Proportional scaling with source tracking

### Current Limitations ⚠️

1. **RMW Availability**
   - HURDAT2 `radius_max_wind` often missing (especially pre-2004)
   - Fallback: 25 nm default (may over/underestimate eyewall size)
   - Future: Develop RMW imputation model

2. **Symmetric Decay Model**
   - Exponential decay assumes radial symmetry
   - Reality: Wind field asymmetry due to storm motion, land interaction
   - Future: Directional wind speed model accounting for storm translation

3. **Constant-Degree Buffer**
   - Rounding buffer uses 0.02° regardless of latitude
   - Creates latitude-dependent distance bias (1.3nm at 25°N, 1.1nm at 35°N)
   - Future: Convert to constant nautical mile buffer

4. **Linear Temporal Interpolation**
   - Assumes linear storm motion between observations
   - Reality: Storms can accelerate/decelerate, recurve
   - Acceptable for 15-min intervals, may need refinement for longer gaps

---

## Implementation Files

### Data Sources
- `01_data_sources/hurdat2/src/parse_raw.py` - HURDAT2 parsing
- `01_data_sources/hurdat2/src/profile_clean.py` - Data validation
- `01_data_sources/census/src/tract_centroids.py` - Census tract processing

### Transformations
- `02_transformations/wind_coverage_envelope/src/envelope_algorithm.py` - Envelopes, imputation, arc generation
- `02_transformations/storm_tract_distance/src/storm_tract_distance.py` - Main pipeline, distance calculations
- `02_transformations/wind_interpolation/src/wind_interpolation.py` - Wind speed estimation
- `02_transformations/duration/src/duration_calculator.py` - Duration calculation
- `02_transformations/lead_time/src/lead_time_calculator.py` - Lead time features

### Integration
- `03_integration/src/feature_pipeline.py` - Final assembly
- `03_integration/scripts/batch_extract_features.py` - Batch processing (14 storms)

---

## Future Enhancements

### High Priority (P1)
- **RMW Imputation Model** - Estimate missing radius of maximum winds from storm characteristics
- **Validation Framework** - Automated comparison with NOAA advisories and station data

### Medium Priority (P2)
- **Directional Wind Asymmetry** - Account for storm motion and land interaction in wind field
- **Constant Nautical Mile Buffer** - Replace degree-based buffer with distance-based

### Low Priority (P3)
- **Holland (1980) Wind Profile** - Physics-based radial wind profile
- **Probabilistic Imputation** - Machine learning with uncertainty bounds
- **Continuous Quadrant Interpolation** - Azimuthal weighting instead of quadrant steps

---

## References

### Data Sources
- **HURDAT2:** NOAA National Hurricane Center
  - https://www.nhc.noaa.gov/data/hurdat/
- **Census TIGER/Line:** US Census Bureau
  - https://www.census.gov/geographies/mapping-files.html

### Algorithms
- **Alpha Shapes:** Edelsbrunner et al. (1983) via scipy.spatial.Delaunay
- **Haversine Formula:** Great-circle distance calculations
- **Wind Decay Model:** Empirical exponential decay (adapted from Holland 1980 simplification)

### Validation
- 14 Gulf Coast hurricanes (2005-2022): Katrina, Rita, Dennis, Gustav, Ike, Harvey, Irma, Michael, Laura, Delta, Zeta, Sally, Ida, Ian

---

For repository structure and workflow, see `00_documentation/REPOSITORY_STRUCTURE.md`
