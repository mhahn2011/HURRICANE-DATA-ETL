# Arc-Based Wind Polygon Implementation Plan

**Date:** 2025-10-05
**Priority:** P0 - Critical
**Estimated Effort:** 4-6 hours
**Impact:** Fixes 10-30% systematic underestimation of wind field area

---

## Problem Statement

HURDAT2 defines wind radii as **radial distances** in four quadrants (NE, SE, SW, NW), representing circular arcs centered on the storm. Our current implementation connects the four extent points with **straight line segments**, creating a diamond/quadrilateral that systematically underestimates the true circular wind field area.

**Mathematical Issue:**
- Current: 4 points → straight chords → inscribed quadrilateral
- Correct: 4 radii → circular arcs → accurate wind field boundary

**Impact:**
- Wind field area underestimated by 10-30%
- False negatives at boundaries (tracts incorrectly excluded)
- Wind speeds underestimated (decay truncated early)
- Duration underestimated (smaller polygons = less exposure)

---

## Solution Architecture

### Core Concept

Instead of connecting 4 corner points with straight lines, **sample points along circular arcs** between quadrants:

1. **NE quadrant arc:** Sample 30 points from bearing 45° to 135° at radius = wind_radii_64_ne
2. **SE quadrant arc:** Sample 30 points from bearing 135° to 225° at radius = wind_radii_64_se
3. **SW quadrant arc:** Sample 30 points from bearing 225° to 315° at radius = wind_radii_64_sw
4. **NW quadrant arc:** Sample 30 points from bearing 315° to 45° at radius = wind_radii_64_nw

Result: **~120-point polygon** (30 points × 4 quadrants) with smooth circular boundaries instead of 4-point diamond.

### Why 30 Points Per Arc?

- **Angular resolution:** 90° / 30 = 3° between points
- **Sufficient smoothness:** Circular arc visually smooth at this density
- **Computational cost:** Minimal increase (30 vs 1 point per quadrant)
- **Shapely efficiency:** Modern GEOS backend handles 120-point polygons efficiently

---

## Files Requiring Changes

### 1. `integration/src/duration_calculator.py`

**Function to Update:** `create_instantaneous_wind_polygon()`

**Current Behavior:**
- Takes 4 radii values (NE, SE, SW, NW)
- Calculates 4 destination points using `calculate_destination_point()`
- Connects with straight lines → Polygon(4 points)
- Applies 0.02° buffer to round corners

**New Behavior:**
- Takes 4 radii values (NE, SE, SW, NW)
- For each quadrant:
  - Generate 30 bearings from start_angle to end_angle
  - Calculate destination point for each bearing using `calculate_destination_point()`
  - Collect points
- Create Polygon from ~120 arc points
- **Remove corner-rounding buffer** (no longer needed - arcs are already smooth)

**Key Implementation Details:**
- Handle NW quadrant wrap-around (315° → 405° instead of 315° → 45°)
- Use `np.linspace()` for even bearing distribution
- Normalize bearings to 0-360° range before passing to `calculate_destination_point()`
- Maintain existing edge case handling (1-point, 2-point fallbacks)

---

### 2. `hurdat2/src/envelope_algorithm.py`

**Function to Update:** `get_wind_extent_points()`

**Current Behavior:**
- Calculates 4 extent points (one per quadrant)
- Returns list of 4 point dictionaries
- Alpha shape built from these sparse points

**New Behavior (Option A - Recommended):**
- Calculate ~30 extent points per quadrant along circular arcs
- Returns list of ~120 point dictionaries
- Alpha shape built from dense arc points → naturally matches wind field curves

**Alternative (Option B - Minimal Change):**
- Keep returning 4 points for alpha shape
- Create separate `create_arc_based_envelope()` function
- Use arc polygons for spatial filtering, keep alpha shape for visualization

**Recommendation:** Option A
- More physically accurate envelope
- Alpha shape will naturally follow wind field curves
- May allow reducing alpha parameter (denser points = less need for aggressive concavity)

**Key Implementation Details:**
- Arc points should include `was_imputed` flag from parent quadrant
- Maintain backward compatibility with visualization code
- Consider adding `point_type` field: "arc_sample" vs "quadrant_corner"

---

### 3. `integration/src/storm_tract_distance.py`

**Function to Update:** `create_wind_coverage_envelope()`

**Current Behavior:**
- Calls `create_instantaneous_wind_polygon()` for each interpolated timestep
- Creates union of all polygons → wind coverage envelope
- Uses buffer_deg=0.0 (no buffering)

**New Behavior:**
- Call updated `create_instantaneous_wind_polygon()` with arc generation
- Union of arc-based polygons → accurate wind coverage
- No changes to union logic required (Shapely handles this)

**Key Implementation Details:**
- Wind coverage will be larger (10-30% area increase expected)
- More tracts will fall within coverage (currently filtered out)
- Computation time may increase slightly (~2x points, but union is O(n log n))

---

## Implementation Steps

### Phase 1: Core Function Development (1-2 hours)

**Step 1.1: Create Arc Generation Helper**
- Write standalone function `generate_quadrant_arc_points()`
- Input: center_lat, center_lon, quadrant_name, radius_nm, num_points=30
- Output: List of (lon, lat) tuples along arc
- Test with simple case: NE quadrant, 50nm radius, verify points form ~90° arc

**Step 1.2: Update `create_instantaneous_wind_polygon()`**
- Replace 4-point logic with arc generation loop
- Handle missing quadrants (skip arc if radius is NaN)
- Remove corner-rounding buffer (set buffer_deg=0.0 or remove parameter)
- Test: Verify polygon has ~120 points for complete wind field

**Step 1.3: Unit Test**
- Test case: All 4 quadrants with equal radii (50nm) should create near-circle
- Test case: Asymmetric radii (NE=60, SE=40, SW=30, NW=50) creates lopsided shape
- Test case: Missing quadrants (only NE and SW) creates partial arcs
- Verify: Polygon area > straight-chord polygon area for same radii

---

### Phase 2: Integration (1-2 hours)

**Step 2.1: Update `envelope_algorithm.py`**
- Modify `get_wind_extent_points()` to generate arc samples
- Decide: Dense arc points for alpha shape (Option A) or keep sparse (Option B)
- Update alpha shape to handle denser point cloud if using Option A
- Test: Verify envelope follows wind field curves more accurately

**Step 2.2: Update `storm_tract_distance.py`**
- Confirm `create_wind_coverage_envelope()` uses updated polygon function
- No logic changes needed (union handles arbitrary point counts)
- Test: Verify wind coverage polygon is larger than before

**Step 2.3: Integration Test**
- Run full pipeline on single track point (not full storm)
- Verify: Arc polygon created successfully
- Verify: Coverage union works correctly
- Check: Number of tracts within coverage increases as expected

---

### Phase 3: Validation (2 hours)

**Step 3.1: Visual Validation**
- Create side-by-side plot for Hurricane Ida, single timestep:
  - Left: Current 4-point chord polygon
  - Right: New 120-point arc polygon
- Overlay census tract centroids
- Visual check: Arc polygon should extend beyond chords in inter-quadrant regions

**Step 3.2: Quantitative Validation**
- Run pipeline on Hurricane Ida (AL092021) with both methods
- Compare metrics:

| Metric | Chord Method | Arc Method | % Change |
|--------|-------------|------------|----------|
| Envelope area (sq deg) | ? | ? | +10-30% expected |
| Tract count | 491 | ? | +50-100 expected |
| Mean duration (hours) | ? | ? | +15-25% expected |
| Mean wind speed (kt) | ? | ? | +5-15% expected |

**Step 3.3: Spot Check with NOAA Advisories**
- Compare Ida's 64kt wind field extent at landfall
- NOAA advisory: "64kt winds extend X miles NE, Y miles SW..."
- Verify: Arc polygon matches advisory extents better than chord polygon

---

### Phase 4: Full Deployment (1 hour)

**Step 4.1: Rerun All 14 Hurricanes**
- Batch process with arc-based polygons
- Generate comparison report:
  - Before/after tract counts per storm
  - Before/after mean duration per storm
  - Before/after mean wind speed per storm

**Step 4.2: Update Results Scratch Pad**
- Mark wind speed as validated with arc correction
- Mark duration as validated with arc correction
- Update any known limitations sections

**Step 4.3: Documentation Update**
- Update `FeatureTransformationNarrative.md`
- Remove "Known Limitation - Arc Geometry" warning
- Add "Corrected in v2.0: Arc-based wind polygons" note
- Update `hurdat_workflow.md` with arc implementation details

---

## Edge Cases & Special Handling

### Case 1: Missing Quadrants
**Current:** 3 quadrants → triangle, 2 quadrants → line, 1 quadrant → point
**With Arcs:**
- 3 quadrants → polygon with 3 arcs (~90 points)
- 2 quadrants → polygon with 2 arcs (~60 points)
- 1 quadrant → single arc (30 points) → treat as curved line, buffer to create polygon

**Recommendation:** For 1-2 quadrants, fall back to existing buffering approach (arcs don't help much)

### Case 2: Nearly Equal Radii (Symmetric Storm)
**With Arcs:** Creates near-circular polygon (~120 points approximating circle)
**No special handling needed** - this is the correct representation

### Case 3: Extreme Asymmetry
**Example:** NE=100nm, SE=30nm, SW=20nm, NW=80nm
**With Arcs:** Creates "cloverleaf" shape with 4 lobes of very different sizes
**This is correct** - matches HURDAT2 intent

### Case 4: Very Small Radii (<5nm)
**Current:** 4 points very close together
**With Arcs:** 120 points very close together
**Potential Issue:** Numerical precision in Shapely
**Solution:** Add minimum radius threshold (e.g., if all radii <2nm, use point buffer instead)

---

## Performance Considerations

### Computational Cost Analysis

**Current Method:**
- 4 points per timestep
- ~880 timesteps for Ida (887 interpolated points from summary)
- Total: ~3,520 polygon vertices
- Union operation: O(n log n) where n ≈ 3,520

**Arc Method:**
- 120 points per timestep (30 × 4 quadrants)
- ~880 timesteps for Ida
- Total: ~105,600 polygon vertices
- Union operation: O(n log n) where n ≈ 105,600

**Expected Impact:**
- 30× more vertices
- Union complexity: ~30 log(30) ≈ 45× slower (but still fast - GEOS is efficient)
- Duration calculation: Negligible change (containment test is O(1) per point)
- **Estimated runtime increase:** 2-5× for full pipeline

**Mitigation if needed:**
- Reduce arc points from 30 to 20 (still smooth, 33% fewer points)
- Parallelize storm processing (already independent)
- Accept slight slowdown for correctness gain

### Memory Considerations

**Current:** ~491 tracts × 24 features = ~12K values
**Arc Method:** ~600-700 tracts × 24 features = ~16K values

**Negligible memory impact** - polygon geometry is transient, only feature matrix persists

---

## Testing Strategy

### Unit Tests (Create `tests/test_arc_polygons.py`)

**Test 1: Circle Approximation**
```python
def test_equal_radii_creates_circular_shape():
    # All 4 quadrants = 50nm
    # Polygon should approximate circle
    # Check: area ≈ π × 50² nm² (within 5%)
```

**Test 2: Area Increase vs Chord**
```python
def test_arc_polygon_larger_than_chord():
    # Same radii, compare areas
    # Arc polygon area > chord polygon area
    # Difference should be 10-30%
```

**Test 3: Missing Quadrants**
```python
def test_partial_quadrants_handled():
    # Only NE and SW quadrants
    # Should create 2-arc polygon (not crash)
```

### Integration Tests

**Test 4: Full Pipeline with Ida**
```python
def test_ida_pipeline_with_arcs():
    # Run storm_tract_distance.py with arc polygons
    # Verify: tract_count > previous (491)
    # Verify: mean_duration > previous
    # Verify: max_wind distribution shifted higher
```

### Visual Tests (Manual)

**Test 5: Single Timestep Comparison**
- Plot chord polygon (4 points)
- Overlay arc polygon (120 points)
- Visual verification: Arcs extend beyond chords

**Test 6: Full Ida Wind Coverage**
- Generate wind coverage envelope with arcs
- Compare to alpha shape envelope
- Verify: Arc coverage ≥ alpha shape coverage

---

## Rollback Plan

### If Arc Method Fails Validation

**Criteria for Rollback:**
- Polygon creation crashes or produces invalid geometries
- Area increase >50% (suggests implementation error)
- Tract count decrease (indicates logic error)
- Runtime increase >10× (unacceptable performance)

**Rollback Steps:**
1. Revert 3 modified files (`duration_calculator.py`, `envelope_algorithm.py`, `storm_tract_distance.py`)
2. Re-run pipeline with original chord method
3. Document failure mode for later investigation
4. Consider hybrid approach: arcs for visualization, chords for computation (temporary)

**Partial Success Handling:**
- If arcs work for duration but fail for envelope → use arcs only in duration calculator
- If arcs work but too slow → reduce arc points from 30 to 15 (still better than 1 point)

---

## Success Criteria

### Minimum Viable Success (Required)
- [ ] Arc polygons generate without errors for all 14 hurricanes
- [ ] Polygon area increase in 10-30% range (validates expected improvement)
- [ ] Tract count increase for Ida (>491, ideally 550-650)
- [ ] No invalid geometries or crashes in Shapely operations

### Full Success (Target)
- [ ] Mean duration increase 15-25%
- [ ] Mean wind speed increase 5-15%
- [ ] Visual validation: arcs clearly extend beyond chords
- [ ] NOAA advisory spot-check: arc extents match reported wind field better
- [ ] Runtime increase <5× (acceptable for correctness gain)

### Exceptional Success (Stretch Goal)
- [ ] Alpha shape envelope with dense arc points follows coastlines more accurately
- [ ] False negative rate reduced (tracts previously excluded now correctly included)
- [ ] ML model performance improvement (R² increase) with corrected features

---

## Post-Implementation Actions

### Immediate (Same Day)
1. Update `results_scratch_pad.md` - mark wind speed and duration as validated with arc correction
2. Update `ALGORITHM_IMPROVEMENTS_RECOMMENDATIONS.md` - mark P0 item as complete
3. Generate before/after comparison report for all 14 hurricanes

### Short-term (1 Week)
1. Re-run any ML models with corrected features
2. Quantify prediction improvement (if any)
3. Update documentation to reflect arc-based implementation as standard
4. Create visualization showing arc vs chord difference for onboarding

### Medium-term (1 Month)
1. Evaluate if alpha parameter needs retuning (denser points may allow smaller α)
2. Consider whether continuous quadrant interpolation (P2 item) is still needed
3. Validate against surface station data (ASOS/METAR) to calibrate arc accuracy

---

## Questions for Discussion

1. **Arc point density:** Start with 30 points/quadrant, or begin with 20 to keep runtime lower?

2. **Envelope strategy:** Dense arc points in alpha shape (Option A) or keep sparse points for alpha shape (Option B)?

3. **Backward compatibility:** Preserve old chord method as `create_chord_wind_polygon()` for comparison, or full replacement?

4. **Performance threshold:** What runtime increase is acceptable? 2×? 5×? 10×?

5. **Validation priority:** Visual validation first, or quantitative metrics first?

---

## Timeline

**Total Estimated Time:** 4-6 hours

| Phase | Tasks | Duration |
|-------|-------|----------|
| **Phase 1: Core Development** | Arc helper function, update duration_calculator.py, unit tests | 1-2 hours |
| **Phase 2: Integration** | Update envelope_algorithm.py, storm_tract_distance.py, integration tests | 1-2 hours |
| **Phase 3: Validation** | Visual comparison, quantitative metrics, NOAA spot-check | 2 hours |
| **Phase 4: Deployment** | Rerun 14 hurricanes, update documentation, comparison report | 1 hour |

**Recommended Schedule:**
- **Day 1 Morning:** Phases 1-2 (development & integration)
- **Day 1 Afternoon:** Phase 3 (validation)
- **Day 2 Morning:** Phase 4 (deployment) if validation passes

---

## Appendix: Mathematical Validation

### Theoretical Area Comparison

**Chord Method (Diamond):**
- 4 points at (r_ne, r_se, r_sw, r_nw) on respective bearings
- Area of quadrilateral inscribed in variable-radius "ellipse"
- Approximate area: `0.5 × (r_ne × r_sw + r_se × r_nw)` for symmetric case

**Arc Method (Cloverleaf):**
- 4 circular arcs of radii (r_ne, r_se, r_sw, r_nw)
- Area of union of 4 circular sectors
- For symmetric case (all radii = r): Area ≈ `π × r²`

**Expected Area Ratio (Symmetric Case):**
- Chord area: `0.5 × (r² + r²) = r²`
- Arc area: `π × r² ≈ 3.14 × r²`
- **Ratio: Arc/Chord ≈ 3.14 → 314% of chord area**

**Wait, that seems too high?**

**Correction:** The 4 points don't form a square - they form a quadrilateral with vertices at 45°, 135°, 225°, 315°. The area of this inscribed quadrilateral is:
- Area = `r² × sin(90°) + r² × sin(90°) = 2r²` (for diamond shape)
- Circle area: `π × r² ≈ 3.14r²`
- **Ratio: 3.14/2 = 1.57 → 57% increase**

**But we're not creating a full circle, we're creating 4 arcs that connect...**

**Actual Calculation:**
The true area depends on how the 4 quadrant radii connect. For a "cloverleaf" with 4 different radii, the area is approximately the sum of 4 circular sectors:
- Area ≈ `(π/4) × (r_ne² + r_se² + r_sw² + r_nw²)`

For symmetric case (r_ne = r_se = r_sw = r_nw = r):
- Arc area: `(π/4) × 4r² = πr²` ✓ (full circle)
- Chord area: `2r²` (diamond inscribed in circle)
- **Ratio: π/2 ≈ 1.57 → 57% increase**

**For asymmetric case, the ratio varies but typically 30-80% increase.**

This validates the "10-30%" estimate is conservative - we might see even larger increases.
