# Repository Structure

**Last Updated:** 2025-10-05

---

## Overview

This repository extracts hurricane impact features for census tract-level analysis. The structure follows a clean separation of concerns:

1. **Single-source folders** - Process one data source only
2. **Multi-source transformation folder** - Combine sources to extract features
3. **Integration folder** - Final assembly and validation only

---

## Folder Organization

```
hurricane-data-etl/
│
├── hurdat2/                    # HURDAT2 hurricane data processing
│   ├── input_data/            # Raw HURDAT2 text files
│   ├── src/                   # Parsing, cleaning, envelope generation
│   │   ├── parse_raw.py
│   │   ├── profile_clean.py
│   │   ├── envelope_algorithm.py
│   │   ├── visualize_folium_qa.py
│   │   └── plot_*.py (HURDAT2-only visualizations)
│   ├── outputs/
│   │   ├── qa_maps/          # Interactive HTML maps of raw wind fields
│   │   ├── envelopes/        # Static envelope visualizations
│   │   ├── transformations/  # Methodology visuals (arc vs chord, imputation)
│   │   └── cleaned_data/     # Processed HURDAT2 tables
│   └── docs/
│       ├── hurdat_workflow.md
│       └── FeatureTransformationNarrative.md
│
├── census/                     # Census tract data processing
│   ├── data/                  # TIGER/Line shapefiles
│   ├── src/                   # Tract loading, centroid extraction
│   │   └── tract_centroids.py
│   └── outputs/               # Processed tract centroids
│
├── hurdat2_census/            # Storm-tract feature extraction (TRANSFORMATIONS)
│   ├── src/                   # Feature engineering combining both sources
│   │   ├── storm_tract_distance.py      # Main pipeline
│   │   ├── wind_interpolation.py        # Wind speed estimation
│   │   ├── duration_calculator.py       # Temporal exposure
│   │   ├── lead_time_calculator.py      # Warning time features
│   │   ├── qaqc_comprehensive_suite.py
│   │   └── qaqc_*.py (transformation visualizations)
│   ├── outputs/
│   │   ├── features/         # Intermediate storm-tract feature tables (CSVs)
│   │   └── transformations/  # Methodology visuals (QA/QC HTML reports)
│   └── README.md
│
├── integration/               # Final assembly & validation (NO TRANSFORMATIONS)
│   ├── src/                   # Assembly, filtering, validation scripts only
│   │   ├── feature_pipeline.py
│   │   └── (minimal assembly logic)
│   └── outputs/
│       ├── final/            # Final ML-ready datasets
│       ├── results/          # Result visualizations (distributions, maps)
│       └── validation/       # Validation reports, comparison tables
│
├── tests/                     # Unit and integration tests
│
└── docs/                      # Project-level documentation
    ├── ALGORITHM_IMPROVEMENTS_RECOMMENDATIONS.md
    ├── ARC_POLYGON_IMPLEMENTATION_PLAN.md
    ├── IMMEDIATE_TODO.md
    └── results_scratch_pad.md
```

---

## Design Principles

### 1. Single-Source Folders (hurdat2/, census/)

**Rule:** Only process ONE data source. No cross-source dependencies.

**hurdat2/** contains:
- ✅ HURDAT2 parsing and cleaning
- ✅ Wind radii imputation (only hurricane data)
- ✅ Envelope generation (only hurricane data)
- ✅ QA/QC of hurricane data quality
- ❌ NO census tract information
- ❌ NO feature extraction requiring tract locations

**census/** contains:
- ✅ TIGER/Line shapefile loading
- ✅ Centroid extraction
- ✅ Tract metadata processing
- ❌ NO hurricane data
- ❌ NO storm-tract interactions

### 2. Multi-Source Transformation Folder (hurdat2_census/)

**Rule:** All transformations combining multiple sources. Contains feature engineering logic.

**hurdat2_census/** contains:
- ✅ Feature extraction algorithms (wind, duration, lead time)
- ✅ Spatial joins (tracts within storm envelopes)
- ✅ Transformation methodology visuals
- ✅ Intermediate feature tables
- ✅ QA/QC validating transformation correctness

**Key insight:** This folder does the **intellectual work** of deriving features. It combines raw inputs and transforms them into meaningful measurements.

### 3. Integration Folder (integration/)

**Rule:** Final assembly, filtering, and validation ONLY. No transformation logic.

**integration/** contains:
- ✅ Combining outputs from hurdat2_census with other potential sources
- ✅ Filtering for quality (e.g., removing tracts with <0.25hr exposure)
- ✅ Final validation and statistical summaries
- ✅ ML-ready dataset export
- ❌ NO feature engineering
- ❌ NO transformation algorithms

**Key insight:** This folder is a **passive assembler**. It takes transformed features and prepares them for consumption.

---

## Visual Organization

### Where Should Visuals Live?

**Decision flowchart:**

1. **Does it visualize raw input data?**
   - HURDAT2 wind fields → `hurdat2/outputs/qa_maps/`
   - Tract boundaries → `census/outputs/`

2. **Does it show a transformation methodology?**
   - Arc vs chord comparison → `hurdat2/outputs/transformations/`
   - Wind decay curves → `hurdat2_census/outputs/transformations/`
   - Duration polygon animation → `hurdat2_census/outputs/transformations/`

3. **Does it show final results?**
   - Feature distributions → `integration/outputs/results/`
   - Tract coverage maps → `integration/outputs/results/`
   - Validation reports → `integration/outputs/validation/`

---

## Data Flow

```
Raw HURDAT2 text
    ↓
hurdat2/src/ (parse, clean, envelope)
    ↓
hurdat2/outputs/cleaned_data/
    ↓
    ↓ ←──────────────────────────────────┐
    ↓                                     │
hurdat2_census/src/                      │
(combine with census centroids)          │
    ↓                                     │
hurdat2_census/outputs/features/         │
(intermediate storm-tract tables)        │
    ↓                                     │
integration/src/                         │
(assemble, filter, validate)             │
    ↓                                     │
integration/outputs/final/               │
(ML-ready datasets)                      │
                                         │
census/data/ (TIGER/Line)                │
    ↓                                     │
census/src/ (load tracts, extract centroids)
    ↓                                     │
census/outputs/ ─────────────────────────┘
```

---

## File Naming Conventions

### Scripts
- `parse_*.py` - Data parsing/loading
- `profile_*.py` - Data cleaning/validation
- `envelope_*.py` - Geometric algorithms
- `visualize_*.py` - Visualization generation
- `qaqc_*.py` - Quality assurance/quality control
- `plot_*.py` - Static plotting (PNG/PDF)
- `*_calculator.py` - Feature calculation modules

### Outputs
- `{storm_id}_tract_features.csv` - Feature tables
- `qaqc_*.html` - Interactive QA/QC reports
- `{storm_name}_{year}_*.html` - Named storm visualizations
- `*_comparison.csv` - Validation/comparison tables

---

## Migration Summary (2025-10-05)

**Created:**
- `hurdat2_census/` folder structure
- `hurdat2/outputs/{qa_maps,envelopes,transformations,cleaned_data}/`
- `integration/outputs/{final,results,validation}/`

**Moved to hurdat2_census/src/:**
- `storm_tract_distance.py`
- `wind_interpolation.py`
- `duration_calculator.py`
- `lead_time_calculator.py`
- `qaqc_comprehensive_suite.py`
- `qaqc_lead_time_visualization.py`

**Moved to hurdat2/src/:**
- `qaqc_wind_radii_visualization.py`
- `plot_ida_folium.py`
- `plot_ida_static.py`
- `plot_ida_envelope.py`

**Moved to hurdat2_census/outputs/features/:**
- All `ida_*_features*.csv` files
- All `ida_tract_distances*.csv` files

**Moved to hurdat2_census/outputs/transformations/:**
- All `qaqc_*.html` visualization files

**Remained in integration/:**
- `feature_pipeline.py` (final assembly)
- `debug_distance_calculation.py` (utility)
- `outputs/final/` (ML-ready datasets)
- `outputs/results/` (final result visualizations)

---

## Notes for Contributors

### Adding New Features

**If feature requires only HURDAT2 data:**
→ Add to `hurdat2/src/`

**If feature requires only census data:**
→ Add to `census/src/`

**If feature combines both sources:**
→ Add to `hurdat2_census/src/`

**If feature combines hurdat2_census outputs with other sources:**
→ Add to `integration/src/`

### Adding New Visualizations

**Ask: "What does this visualize?"**
- Raw input data → source folder (`hurdat2/` or `census/`)
- Transformation methodology → `hurdat2_census/outputs/transformations/`
- Final results → `integration/outputs/results/`

### Updating Documentation

- **Algorithm changes:** Update `hurdat2/docs/FeatureTransformationNarrative.md`
- **Workflow changes:** Update `hurdat2/docs/hurdat_workflow.md`
- **Structure changes:** Update this file (`REPOSITORY_STRUCTURE.md`)
- **Immediate tasks:** Update `IMMEDIATE_TODO.md`

---

## Future Additions

Potential new folders as project grows:

- `rainfall/` - If adding precipitation data from another source
- `surge/` - If adding storm surge modeling
- `damage/` - If adding insurance claims or damage assessment data
- `hurdat2_census_rainfall/` - If combining all three sources for compound features

Each would follow the same pattern: single-source folders process independently, multi-source folders transform and extract features, integration assembles final datasets.
