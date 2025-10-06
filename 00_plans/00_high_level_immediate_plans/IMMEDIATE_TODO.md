# Immediate To-Do List

**Last Updated:** 2025-10-05
**Status:** Active

---

## Priority 1: Visual Documentation & QA/QC

### Task 1.1: Review & Improve Existing Visuals
**Goal:** Systematically review each visualization, determine proper location, and improve to show arc-based geometry

- [ ] **IDA_2021_wind_field.html** (currently in `hurdat2/outputs/qa_maps/`)
  - Currently shows: Wind radii as quadrilaterals (chord-based)
  - Needs: Update to show true circular arcs (radii, not chords)
  - Should live in: `hurdat2/outputs/qa_maps/` ✓ (correct location)
  - Purpose: HURDAT2 raw data visualization - shows what we START with

- [ ] Review all visualizations in `integration/outputs/`
  - Identify which are methodology/intermediate vs final results
  - Move methodology visuals to `hurdat2/outputs/`
  - Keep only integrated results in `integration/outputs/`

### Task 1.2: Create Visual Documentation Hierarchy
**Goal:** Clear visual story from raw data → transformations → results

**Category A: Raw Data Visuals** (`hurdat2/outputs/`)
- [ ] Wind field QA maps showing HURDAT2 quadrant radii as arcs
- [ ] Track visualization with intensity markers
- [ ] Wind radii asymmetry examples (show NE/SE/SW/NW differences)
- [ ] RMW availability timeline (which storms have it)

**Category B: Transformation Visuals** (`hurdat2/outputs/transformations/`)
- [ ] Alpha shape envelope construction process
  - Raw wind extent points (arc samples)
  - Segmented alpha shape hulls
  - Final unioned envelope
- [ ] Temporal interpolation comparison (6-hour vs 15-minute)
- [ ] Wind radii imputation examples (before/after)
- [ ] Arc vs chord comparison (THIS IS CRITICAL - shows the fix)
  - Side-by-side for single timestep
  - Area difference quantification
  - Tract inclusion comparison

**Category C: Feature Results** (`integration/outputs/results/`)
- [ ] Distance classification validation
- [ ] Wind speed distribution by source (rmw_plateau vs decay)
- [ ] Duration histograms by storm
- [ ] Lead time distributions by category
- [ ] Tract coverage maps (which tracts affected by which storms)

**Category D: Validation Visuals** (`integration/outputs/validation/`)
- [ ] Before/after arc correction comparison
- [ ] NOAA advisory spot-check comparisons
- [ ] Statistical summaries (14 hurricane comparison tables)

---

## Priority 2: Repository Structure Cleanup

### Task 2.1: Define Clear Folder Purposes

**Proposed Structure:**

```
hurdat2/
├── input_data/              # Raw HURDAT2 text files
├── src/                     # Parsing, cleaning, envelope, visualization
├── outputs/
│   ├── qa_maps/            # Interactive HTML maps of raw HURDAT2 data
│   ├── envelopes/          # Static envelope visualizations (PNG/PDF)
│   ├── transformations/    # Methodology visuals (arc vs chord, imputation, etc.)
│   └── cleaned_data/       # Cleaned/processed HURDAT2 tables (CSVs)

census/
├── src/                     # Tract loading, centroid extraction
├── data/                    # TIGER/Line shapefiles
└── outputs/                # Processed tract centroids (GeoJSON/CSV)

hurdat2_census/              # NEW: Storm-tract transformations (combining both sources)
├── src/                     # Feature extraction, wind interpolation, duration, lead time
├── outputs/
│   ├── transformations/    # Methodology visuals (wind decay curves, duration animations)
│   └── features/           # Intermediate feature tables (before final integration)

integration/
├── src/                     # Final assembly, filtering, validation only (NO transformations)
├── outputs/
│   ├── final/              # Final integrated feature tables (ML-ready)
│   ├── results/            # Result visualizations (distributions, maps)
│   └── validation/         # Validation reports and comparisons
```

### Task 2.2: File Migration Plan
- [ ] Create new subdirectories in `hurdat2/outputs/` and `integration/outputs/`
- [ ] Move existing files to appropriate locations
- [ ] Update any hardcoded paths in scripts
- [ ] Document new structure in README

---

## Priority 3: Arc Geometry Implementation (from ARC_POLYGON_IMPLEMENTATION_PLAN.md)

✅ **COMPLETED** - Arc generation functions implemented:
- `generate_quadrant_arc_points()` in `envelope_algorithm.py`
- `create_instantaneous_wind_polygon()` updated in `duration_calculator.py`
- `get_wind_extent_points()` updated in `envelope_algorithm.py`

### Remaining Arc Tasks:
- [ ] **Validation:** Run Ida comparison (chord vs arc)
  - Quantify area increase
  - Count tract difference
  - Measure duration/wind speed changes
- [ ] **Visual validation:** Create side-by-side arc vs chord visualization
- [ ] **Full deployment:** Re-run all 14 hurricanes with arc polygons
- [ ] **Documentation:** Update narrative to reflect arc correction as completed

---

## Priority 4: Update Documentation

### Task 4.1: Update FeatureTransformationNarrative.md
- [x] Remove "Known Limitation - Arc Geometry" warning
- [ ] Add "Arc Correction v2.1" section describing the fix
- [ ] Update buffer discussion (may no longer need rounding buffer with arcs)

### Task 4.2: Update hurdat_workflow.md
- [ ] Mark arc polygon implementation as complete
- [ ] Update envelope construction section with arc details
- [ ] Add new output schema with `duration_source` and `wind_source` columns

### Task 4.3: Update ALGORITHM_IMPROVEMENTS_RECOMMENDATIONS.md
- [ ] Mark P0 arc geometry item as COMPLETE
- [ ] Move to "Completed Improvements" section
- [ ] Add validation results when available

---

## Brainstorm: Visual Organization Philosophy

**Clean Boundary Principle:**

> **HURDAT2 folder** = Hurricane data ONLY
> - Raw HURDAT2 files
> - Parsing, cleaning, imputation
> - Envelope generation (alpha shapes from wind radii)
> - QA/QC of hurricane data quality
> - NO census data involved

> **Census folder** = Tract data ONLY
> - TIGER/Line shapefiles
> - Centroid extraction
> - Tract metadata processing
> - NO hurricane data involved

> **hurdat2_census folder** = Storm-tract transformations
> - Feature extraction algorithms (wind interpolation, duration, lead time)
> - Methodology that combines both data sources
> - Transformation visuals showing how features are derived
> - Intermediate feature tables

> **Integration folder** = Final assembly ONLY
> - Combines outputs from hurdat2_census with any other sources
> - Filtering, validation, quality checks
> - Final ML-ready datasets
> - Results and validation visuals
> - NO transformation logic

### Specific Visual Placement Recommendations:

**HURDAT2 folder should contain:**
1. ✅ **Wind field HTML maps** - Shows raw HURDAT2 quadrant structure
2. ✅ **Envelope construction visuals** - Shows alpha shape methodology
3. ✅ **Arc vs chord comparison** - Shows geometric correction
4. ✅ **Imputation before/after** - Shows data quality transformations
5. ✅ **Track visualizations** - Storm paths with intensity/structure

**hurdat2_census folder should contain:**
1. ✅ **Duration polygon animation** (15-min timesteps) - Transformation methodology
2. ✅ **Wind decay visualization** (RMW plateau + decay curves) - Feature derivation
3. ✅ **Tract-specific feature examples** - How wind/duration calculated for specific tracts
4. ✅ **Lead time calculation examples** - Category threshold detection

**Integration folder should contain:**
1. ✅ **Tract coverage maps** - Final results showing which tracts affected
2. ✅ **Feature distribution plots** - Histograms of final integrated features
3. ✅ **Validation reports** - Comparison tables, statistical summaries
4. ✅ **ML input datasets** - Final cleaned feature tables ready for modeling

---

## Next Actions (In Order)

1. **Create folder structure** (5 min)
   ```bash
   mkdir -p hurdat2/outputs/{qa_maps,envelopes,transformations,cleaned_data}
   mkdir -p integration/outputs/{features,results,validation}
   ```

2. **Update wind field HTML to show arcs** (30 min)
   - Modify `visualize_folium_qa.py` to use arc generation
   - Regenerate `IDA_2021_wind_field.html`
   - Visual confirmation: arcs extend beyond chords

3. **Create arc vs chord comparison visual** (1 hour)
   - Single Ida timestep, side-by-side
   - Overlay tract centroids
   - Show which tracts gained coverage with arcs

4. **Run Ida validation** (30 min)
   - Chord method: existing results
   - Arc method: re-run with new polygons
   - Generate comparison table

5. **Organize existing files** (30 min)
   - Move files to new structure
   - Update path references in scripts
   - Document moves in git commit

---

## Questions for Discussion

1. **Visual format preferences:**
   - Interactive HTML (Folium) vs static PNG/PDF?
   - Both? (HTML for exploration, PNG for documentation)

2. **Naming convention:**
   - `IDA_2021_wind_field.html` vs `ida_2021_raw_wind_radii.html`?
   - Prefer storm name vs ID in filenames?

3. **Validation visual priority:**
   - Arc vs chord comparison first? (Shows the fix)
   - Or full 14-storm results table? (Shows overall impact)

4. **Documentation depth:**
   - Embed explanatory text in HTML maps?
   - Or separate markdown files linking to visuals?

---

## Success Criteria

- [ ] Clear visual narrative: Raw data → Transformations → Results
- [ ] All visuals in logical folders matching their purpose
- [ ] Arc-based geometry implemented and validated
- [ ] Documentation updated to reflect current state
- [ ] Repository navigable by new team member without guidance
