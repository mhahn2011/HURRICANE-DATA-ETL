# Wind Field Visualization Improvements Plan

**Map**: `IDA_2021_wind_field.html`
**Date**: 2025-10-05
**Status**: Ready for Implementation

---

## Current Issues Identified

### 1. **Missing Legend for Dot Color Coding** ✅
**Problem**: Tract centroids are color-coded by duration but no legend explains the color scheme.

**Current Color Scheme** (inferred from code):
- Color gradient based on `duration_in_envelope_hours`
- Likely using a heatmap gradient (blue → yellow → red)

**Required Fix**: Add legend showing duration color scale

### 2. **Tooltip Labels Too Narrow** ✅
**Problem**: Max wind speed labels in tooltips are truncated/not wide enough.

**Required Fix**: Increase tooltip width to accommodate full wind speed text

### 3. **Quadrilaterals vs Radial Arcs** ✅ **CRITICAL**
**Problem**: Displaying straight-line quadrilaterals instead of true radial arc geometry.

**Current**: Wind radii connected with straight chords (diamond shapes)
**Should be**: True circular arcs between quadrant extent points

**This is the same issue identified in `ALGORITHM_IMPROVEMENTS_RECOMMENDATIONS.md`**

---

## Implementation Plan

### Priority 1: Arc-Based Wind Field Geometry (CRITICAL)

**Rationale**: Aligns visualization with HURDAT2 radial definition and corrects 10-30% area underestimation.

**Implementation Steps**:

1. **Create Arc Polygon Generator** (in `envelope_algorithm.py` or new utility module):

```python
def create_arc_based_wind_polygon(
    center_lat: float,
    center_lon: float,
    wind_radii_ne: float,
    wind_radii_se: float,
    wind_radii_sw: float,
    wind_radii_nw: float,
    arc_points: int = 30
) -> Polygon | None:
    """Create wind polygon with true circular arcs between quadrants.

    Args:
        center_lat, center_lon: Storm center coordinates
        wind_radii_*: Radial extent in nautical miles for each quadrant
        arc_points: Number of points to sample along each 90° arc

    Returns:
        Polygon with smooth circular boundaries
    """
    from envelope_algorithm import calculate_destination_point

    radii_dict = {
        'ne': wind_radii_ne,
        'se': wind_radii_se,
        'sw': wind_radii_sw,
        'nw': wind_radii_nw,
    }

    quadrant_bearings = {
        'ne': (45, 135),    # Start at 45°, end at 135°
        'se': (135, 225),
        'sw': (225, 315),
        'nw': (315, 45)     # Wraps around 360°→0°
    }

    polygon_points = []

    for quadrant in ['ne', 'se', 'sw', 'nw']:
        radius = radii_dict[quadrant]
        if pd.isna(radius) or radius <= 0:
            continue

        start_bearing, end_bearing = quadrant_bearings[quadrant]

        # Handle wrap-around for NW quadrant
        if end_bearing < start_bearing:
            end_bearing += 360

        # Sample points along the arc
        bearings = np.linspace(start_bearing, end_bearing, arc_points)

        for bearing in bearings:
            bearing_normalized = bearing % 360
            dest_lon, dest_lat = calculate_destination_point(
                center_lat, center_lon, bearing_normalized, radius
            )
            polygon_points.append((dest_lon, dest_lat))

    if len(polygon_points) < 3:
        return None

    return Polygon(polygon_points)
```

2. **Update Visualization Script**:
   - Replace `create_instantaneous_wind_polygon()` with `create_arc_based_wind_polygon()`
   - Update function signature to pass `arc_points=30` for smooth arcs
   - Maintain backward compatibility by keeping quadrilateral option with flag

3. **Update Tooltip Labels**:
   - Change "Wind Radii Quadrilateral" → "Wind Radii Field (Arc-Based)"
   - Note in tooltip: "Radial arcs (not straight chords)"

---

### Priority 2: Add Duration Legend

**Implementation**:

Add HTML legend to Folium map similar to existing implementations:

```python
# After creating the map, before saving
legend_html = '''
<div style="position: fixed;
    bottom: 50px; left: 50px; width: 250px;
    background-color: white; z-index:9999; font-size:14px;
    border:2px solid grey; border-radius: 5px; padding: 10px">

    <p style="margin: 0 0 10px 0; font-weight: bold;">Duration in 64kt Winds</p>

    <div style="background: linear-gradient(to right,
        rgb(0,0,255), rgb(0,255,255), rgb(0,255,0),
        rgb(255,255,0), rgb(255,0,0));
        height: 20px; margin-bottom: 5px;"></div>

    <div style="display: flex; justify-content: space-between; font-size: 11px;">
        <span>0 hrs</span>
        <span>2 hrs</span>
        <span>4 hrs</span>
        <span>6 hrs</span>
        <span>8+ hrs</span>
    </div>

    <p style="margin: 10px 0 5px 0; font-size: 12px;"><b>Wind Field Types:</b></p>
    <p style="margin: 3px 0;">
        <span style="color: blue; font-weight: bold;">━━━</span> Observed (6-hr data)
    </p>
    <p style="margin: 3px 0;">
        <span style="color: purple; font-weight: bold;">- - -</span> Interpolated (15-min)
    </p>
    <p style="margin: 3px 0;">
        <span style="color: orange; font-weight: bold;">· · ·</span> Imputed (estimated)
    </p>
</div>
'''

m.get_root().html.add_child(folium.Element(legend_html))
```

---

### Priority 3: Widen Tooltip Labels

**Current Issue**: Tooltips likely have default width that truncates text like:
```
Wind Radii: NE=45 SE=40...  [TRUNCATED]
```

**Implementation**:

Update tooltip creation with explicit width:

```python
# In plot_quadrilateral() function
tooltip_html = f"""
<div style="min-width: 300px;">
    <b>Time:</b> {timestamp.strftime('%Y-%m-%d %H:%M UTC')}<br>
    <b>Type:</b> {'Imputed' if is_imputed else 'Interpolated' if is_interpolated else 'Observed'}<br>
    <b>Wind Radii (64kt):</b><br>
    &nbsp;&nbsp;NE: {wind_radii_ne:.0f} nm<br>
    &nbsp;&nbsp;SE: {wind_radii_se:.0f} nm<br>
    &nbsp;&nbsp;SW: {wind_radii_sw:.0f} nm<br>
    &nbsp;&nbsp;NW: {wind_radii_nw:.0f} nm
</div>
"""

folium.Tooltip(tooltip_html, sticky=True, style="min-width: 320px;")
```

---

## Implementation Checklist

### Phase 1: Arc Geometry (This Week)
- [ ] Implement `create_arc_based_wind_polygon()` function
- [ ] Add unit tests comparing arc vs chord area
- [ ] Update `qaqc_wind_radii_visualization.py` to use arc polygons
- [ ] Regenerate Ida wind field map
- [ ] Visual QA: Verify arcs look smooth and realistic

### Phase 2: Legend & Tooltips (This Week)
- [ ] Add duration color scale legend (bottom-left)
- [ ] Add wind field type legend (line styles)
- [ ] Widen tooltip containers to 300-320px
- [ ] Test tooltip rendering on sample polygons
- [ ] Regenerate Ida wind field map with all improvements

### Phase 3: Validation (Next Week)
- [ ] Create side-by-side comparison: chord vs arc geometry
- [ ] Quantify area difference for Ida polygons
- [ ] Document visual improvements in this file
- [ ] Update main algorithm if arc geometry proves beneficial

---

## Expected Visual Changes

### Before (Current):
- Straight-line quadrilaterals (diamond shapes)
- No legend for tract colors
- Truncated wind speed tooltips
- Unclear what colors/dashes mean

### After (Improved):
- Smooth circular arcs (true radial geometry)
- Clear legend showing duration color scale
- Full wind radii values visible in wide tooltips
- Legend explaining observed/interpolated/imputed types

---

## Technical Notes

### Arc Point Density
- **30 points per quadrant** = 120 total points for full wind field
- Each 90° arc sampled at 3° intervals
- Smooth enough for visual realism, not too dense for performance

### Polygon Validity
- Arc polygons may self-intersect if radii vary wildly between quadrants
- Apply `.buffer(0)` to repair invalid geometries
- Log warnings for self-intersecting cases

### Performance Impact
- Arc polygon creation: ~2-3x slower than quadrilaterals
- For 887 timesteps (Ida interpolated): adds ~1-2 seconds
- Acceptable tradeoff for visual/analytical accuracy

---

## Testing Plan

### Visual Validation
1. Compare arc vs chord for highly asymmetric storm (Ida at landfall)
2. Verify smooth arcs at all timesteps (no jagged edges)
3. Check legend visibility on different screen sizes
4. Test tooltip width on long wind radii values

### Quantitative Validation
```python
# Compare areas
chord_polygon = create_instantaneous_wind_polygon(...)  # Old method
arc_polygon = create_arc_based_wind_polygon(...)        # New method

area_diff_pct = (arc_polygon.area / chord_polygon.area - 1) * 100
print(f"Arc polygon area is {area_diff_pct:.1f}% larger than chord polygon")

# Expected: 10-30% larger for typical asymmetric wind fields
```

---

## Rollout Strategy

### Step 1: Ida Proof-of-Concept
- Implement all three fixes for Ida visualization
- Generate `IDA_2021_wind_field_v2.html`
- Review with team for approval

### Step 2: Backfill Historical Storms
- Apply arc polygon fix to all 14 hurricanes
- Regenerate wind field maps in `hurdat2/outputs/qa_maps/`
- Archive old quadrilateral versions as `*_chord_geometry.html`

### Step 3: Update Core Pipeline
- If arc geometry proves valuable, update:
  - `envelope_algorithm.py` - envelope construction
  - `duration_calculator.py` - exposure calculations
  - `storm_tract_distance.py` - wind coverage envelope
- Re-run full feature extraction pipeline
- Compare tract counts and duration distributions

---

## Documentation Updates Required

After implementation:

1. **Update FeatureTransformationNarrative.md**:
   - Add section explaining arc vs chord geometry choice
   - Include visual comparison diagram
   - Document 10-30% area correction impact

2. **Update README for qa_maps/**:
   - Explain visualization color scheme
   - Document legend interpretation
   - Add screenshot showing arc geometry vs old chord method

3. **Update ALGORITHM_IMPROVEMENTS_RECOMMENDATIONS.md**:
   - Mark arc geometry as **IMPLEMENTED**
   - Add validation results once available
   - Update priority matrix

---

## Success Criteria

✅ **Visualization Fixed When**:
1. Wind fields show smooth circular arcs (not diamonds)
2. Legend clearly explains all color coding
3. Tooltips display full wind radii without truncation
4. Labels accurately state "arc-based" geometry

✅ **Algorithm Validated When**:
1. Arc polygons consistently 10-30% larger than chord polygons
2. Tract counts increase for envelope-based filtering
3. Duration values increase for edge tracts
4. No new false positives introduced

---

## Files to Modify

1. **`hurdat2/src/qaqc_wind_radii_visualization.py`**
   - Replace polygon generation
   - Add legend HTML
   - Widen tooltips

2. **`hurdat2/src/envelope_algorithm.py`** (or new `wind_geometry.py`)
   - Add `create_arc_based_wind_polygon()`
   - Update existing callers

3. **`integration/src/duration_calculator.py`**
   - Replace `create_instantaneous_wind_polygon()` with arc version
   - Update function signature

4. **`integration/src/storm_tract_distance.py`**
   - Update wind coverage envelope to use arc polygons
   - Re-validate filtering logic

---

## Risk Assessment

**Low Risk**:
- Adding legend (pure HTML overlay)
- Widening tooltips (cosmetic change)

**Medium Risk**:
- Arc polygon implementation (new geometry logic, need validation)

**Mitigation**:
- Keep chord polygon code as fallback option
- Add feature flag: `use_arc_geometry=True/False`
- Extensive visual QA before deploying to core pipeline

---

## Next Steps

1. **Immediate**: Implement arc polygon function and test on Ida
2. **This Week**: Add legend and widen tooltips, regenerate Ida map
3. **Next Week**: Validate area differences, extend to all storms
4. **Month 1**: Update core pipeline if validation successful
5. **Month 2**: Publish methodology paper with corrected geometry

---

## Contact & Questions

For implementation questions or validation results, refer to:
- `/Users/Michael/hurricane-data-etl/ALGORITHM_IMPROVEMENTS_RECOMMENDATIONS.md` (parent document)
- `/Users/Michael/hurricane-data-etl/hurdat2/docs/FeatureTransformationNarrative.md` (methodology)
- `/Users/Michael/hurricane-data-etl/tests/test_wind_coverage_envelope.py` (test framework)
