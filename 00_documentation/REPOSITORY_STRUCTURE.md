# Repository Structure

**Last Updated:** 2025-10-05 (Post-Refactor)
**Previous Structure:** See `archive/REPOSITORY_STRUCTURE_pre-refactor_2025-10-05.md`

---

## Overview

This repository extracts hurricane impact features for census tract-level analysis. The structure uses **numbered folders** for logical organization and clear processing flow.

### Design Philosophy

1. **Numbered folders** - Process in logical order (plans → docs → sources → transforms → integration)
2. **Single-source folders** - Process one data source only (01_data_sources)
3. **Multi-source transformations** - Combine sources to extract features (02_transformations)
4. **Final assembly** - Integration and validation only (03_integration)

---

## Current Structure (Numbered Folders)

```
hurricane-data-etl/
│
├── -01_plans/                          # Implementation plans & architecture docs
│   ├── REFACTORING_IMPLEMENTATION_PLAN.md
│   ├── LEGACY_FOLDER_MIGRATION.md
│   └── REPOSITORY_RESTRUCTURE_PLAN.md
│
├── 00_documentation/                   # Completed project documentation
│   ├── README.md                       # Project overview (start here!)
│   ├── REPOSITORY_STRUCTURE.md         # This file
│   ├── FEATURE_METHODOLOGY.md          # Algorithm documentation
│   ├── DOCUMENTATION_REFACTORING_RECOMMENDATIONS.md
│   └── archive/                        # Pre-refactor docs
│
├── 01_data_sources/                    # Single-source data processing
│   │
│   ├── hurdat2/                        # HURDAT2 hurricane tracks
│   │   ├── src/                        # Processing scripts
│   │   │   ├── parse_raw.py           # Parse HURDAT2 text files
│   │   │   ├── profile_clean.py       # Data validation & cleaning
│   │   │   └── visualize_folium_qa.py # QA visualizations
│   │   ├── input_data/                 # Raw HURDAT2 text files
│   │   │   └── hurdat2-atlantic.txt
│   │   └── outputs/                    # Processed outputs
│   │       ├── qa_maps/               # HTML visualization maps
│   │       └── batch_processing_summary.csv
│   │
│   └── census/                         # Census tract boundaries
│       ├── src/                        # Processing scripts
│       │   └── tract_centroids.py     # Extract tract centroids
│       ├── data/                       # TIGER/Line shapefiles
│       └── outputs/                    # Processed tract centroids
│
├── 02_transformations/                 # Multi-source feature engineering
│   │
│   ├── wind_coverage_envelope/         # T1: Spatial extent using alpha shapes
│   │   └── src/
│   │       └── envelope_algorithm.py  # Alpha shape envelopes, wind radii imputation
│   │
│   ├── storm_tract_distance/           # T2: Spatial relationships
│   │   └── src/
│   │       └── storm_tract_distance.py # Distance calculations, main pipeline
│   │
│   ├── wind_interpolation/             # T3: Wind speed estimation
│   │   └── src/
│   │       └── wind_interpolation.py  # RMW plateau + exponential decay
│   │
│   ├── duration/                       # T4: Temporal exposure
│   │   └── src/
│   │       └── duration_calculator.py # 15-min interpolation, duration tracking
│   │
│   └── lead_time/                      # T5: Warning time features
│       └── src/
│           └── lead_time_calculator.py # Category threshold detection
│
├── 03_integration/                     # Final assembly & validation
│   ├── src/                            # Assembly scripts
│   │   ├── feature_pipeline.py        # Main feature extraction pipeline
│   │   ├── intensification_features.py # Storm intensification metrics
│   │   └── streamlit_app.py           # Interactive dashboard
│   ├── scripts/                        # Batch processing
│   │   └── batch_extract_features.py  # Process all 14 hurricanes
│   └── outputs/                        # Final datasets
│       └── ml_ready/                   # ML-ready feature tables
│
├── 04_src_shared/                      # Shared utilities
│   ├── __init__.py
│   └── geometry_utils.py               # Haversine, bearing calculations
│
├── 05_tests/                           # Test suite
│   ├── test_arc_polygons.py
│   ├── test_duration_calculator.py
│   ├── test_envelope_validity.py
│   ├── test_wind_interpolation.py
│   └── ...                             # 13 test files total
│
├── 06_outputs/                         # Consolidated outputs
│   ├── ml_ready/                       # Final ML-ready feature tables
│   │   ├── {storm_id}_features.csv    # Per-storm features
│   │   └── storm_tract_features.csv   # Unified dataset (all storms)
│   │
│   └── visuals/                        # All visualizations
│       ├── hurdat2/                    # Single-source HURDAT2 visuals
│       │   └── {storm_name}_{year}_wind_field.html
│       ├── hurdat2_census/             # Multi-source transformation visuals
│       │   ├── qaqc_*_distance.html
│       │   ├── qaqc_*_wind.html
│       │   ├── qaqc_*_duration.html
│       │   └── qaqc_*_lead_time_*.html
│       └── debug/                      # Debug/development plots
│
├── _legacy_data_sources/               # Archived pre-refactor code
│   └── README.md                       # ⚠️ DO NOT USE - historical reference only
│
├── .claude.md                          # AI assistant context
├── .gitignore
├── requirements.txt
└── pytest.ini
```

---

## Why Numbered Folders?

### Advantages

1. **Logical Sorting:** Folders appear in processing order
   - `-01_plans/` → Planning documents (negative prefix = meta)
   - `00_documentation/` → Project documentation
   - `01_data_sources/` → Raw data ingestion
   - `02_transformations/` → Feature engineering
   - `03_integration/` → Final assembly
   - `04_src_shared/` → Shared utilities
   - `05_tests/` → Test suite

2. **Clear Organization:** Number prefix signals purpose
   - `0x` = Infrastructure/meta
   - `1x` = Data layer
   - `2x` = Transform layer
   - `3x` = Assembly layer
   - `4x` = Utilities
   - `5x` = Testing
   - `6x` = Outputs

3. **Easy Navigation:** File explorers and IDEs sort predictably

### Python Import Strategy

Since Python identifiers cannot start with numbers, we use `sys.path` manipulation:

```python
from pathlib import Path
import sys

# Add specific source directories to Python path
REPO_ROOT = Path(__file__).resolve().parents[N]  # N depends on file depth
sys.path.insert(0, str(REPO_ROOT / "02_transformations" / "duration" / "src"))
sys.path.insert(0, str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"))

# Then import normally
from duration_calculator import calculate_duration_for_tract
from parse_raw import parse_hurdat2_file
```

**Note:** Each test file and script sets up its own sys.path based on what it needs to import.

---

## Design Principles

### 1. Single-Source Folders (`01_data_sources/`)

**Rule:** Only process ONE data source. No cross-source dependencies.

**hurdat2/** contains:
- ✅ HURDAT2 parsing and cleaning
- ✅ Wind radii imputation (hurricane data only)
- ✅ QA/QC of hurricane data quality
- ❌ NO census tract information
- ❌ NO feature extraction requiring tract locations

**census/** contains:
- ✅ TIGER/Line shapefile loading
- ✅ Centroid extraction
- ✅ Tract metadata processing
- ❌ NO hurricane data
- ❌ NO storm-tract interactions

### 2. Multi-Source Transformations (`02_transformations/`)

**Rule:** All feature engineering that combines multiple data sources.

Each transformation is self-contained:
- **wind_coverage_envelope/** - Creates spatial envelopes (uses HURDAT2 only, but outputs consumed by others)
- **storm_tract_distance/** - Combines hurricane + census data
- **wind_interpolation/** - Wind speed at tract centroids
- **duration/** - Temporal exposure calculations
- **lead_time/** - Warning time features

**Key insight:** This layer does the **intellectual work** of deriving meaningful features from raw inputs.

### 3. Integration Layer (`03_integration/`)

**Rule:** Final assembly, filtering, and validation ONLY. No transformation logic.

**03_integration/** contains:
- ✅ Combining transformation outputs
- ✅ Quality filtering (e.g., removing <0.25hr exposures)
- ✅ Final validation and statistical summaries
- ✅ ML-ready dataset export
- ❌ NO feature engineering
- ❌ NO transformation algorithms

**Key insight:** This layer is a **passive assembler**. It takes transformed features and prepares them for consumption.

---

## Data Flow

```
Raw HURDAT2 text
    ↓
01_data_sources/hurdat2/src/ (parse, clean)
    ↓
01_data_sources/hurdat2/outputs/
    ↓
    ↓ ←─────────────────────────────────────────┐
    ↓                                            │
02_transformations/*/src/                       │
(envelope, distance, wind, duration, lead_time) │
    ↓                                            │
03_integration/src/                             │
(assemble, filter, validate)                    │
    ↓                                            │
03_integration/outputs/ml_ready/                │
(Final ML datasets)                             │
                                                 │
01_data_sources/census/src/                     │
(load tracts, extract centroids)                │
    ↓                                            │
01_data_sources/census/outputs/ ────────────────┘
```

---

## File Naming Conventions

### Scripts
- `parse_*.py` - Data parsing/loading
- `profile_*.py` - Data cleaning/validation
- `envelope_*.py` - Geometric algorithms
- `visualize_*.py` - Visualization generation
- `*_calculator.py` - Feature calculation modules

### Outputs
- `{storm_id}_tract_features.csv` - Feature tables
- `{storm_name}_{year}_*.html` - Named storm visualizations
- `batch_processing_summary.csv` - Batch processing results

---

## Contributor Guidelines

### Adding New Features

**If feature requires only HURDAT2 data:**
→ Add to `01_data_sources/hurdat2/src/`

**If feature requires only census data:**
→ Add to `01_data_sources/census/src/`

**If feature combines both sources:**
→ Add to `02_transformations/{feature_name}/src/`

**If feature combines transformation outputs:**
→ Add to `03_integration/src/`

### Adding New Visualizations

Determine the visual's purpose:
- **Raw input data** → `01_data_sources/{source}/outputs/`
- **Transformation methodology** → `02_transformations/{transform}/outputs/`
- **Final results** → `03_integration/outputs/`

### Running Tests

```bash
# All tests
python -m pytest 05_tests/ -v

# Specific test
python -m pytest 05_tests/test_arc_polygons.py -v

# With coverage
python -m pytest 05_tests/ --cov=01_data_sources --cov=02_transformations
```

### Updating Documentation

- **Algorithm changes:** Update `00_documentation/FEATURE_METHODOLOGY.md`
- **Structure changes:** Update this file (`REPOSITORY_STRUCTURE.md`)
- **New features:** Update `00_documentation/README.md`

---

## Future Additions

As the project grows, follow the same pattern:

**New data sources:**
- `01_data_sources/rainfall/` - Precipitation data
- `01_data_sources/surge/` - Storm surge models
- `01_data_sources/damage/` - Insurance claims

**New transformations:**
- `02_transformations/compound_wind_rainfall/` - Multi-hazard features
- `02_transformations/surge_inundation/` - Flood exposure

Each follows the pattern: single-source folders process independently, transformations combine sources, integration assembles final datasets.

---

## Migration History

### 2025-10-05: Numbered Folder Restructure

**From:** Flat structure with `hurdat2/`, `census/`, `hurdat2_census/`, `integration/`, `shared/`, `tests/`

**To:** Numbered structure with:
- `01_data_sources/` (hurdat2, census)
- `02_transformations/` (wind_coverage_envelope, storm_tract_distance, wind_interpolation, duration, lead_time)
- `03_integration/` (feature_pipeline, batch processing)
- `04_src_shared/` (geometry utilities)
- `05_tests/` (test suite)

**Rationale:**
- Clear processing order
- Better organization for navigation
- Separates concerns (data → transform → integrate)

**See:** `00_documentation/archive/` for pre-refactor documentation

---

## Quick Reference

**Find something?**
- Algorithm documentation → `00_documentation/FEATURE_METHODOLOGY.md`
- Project overview → `00_documentation/README.md`
- Implementation plans → `-01_plans/`
- Test a feature → `05_tests/test_{feature}.py`
- Run main pipeline → `python 03_integration/src/feature_pipeline.py --storm-id AL092021`

**Find outputs?**
- ML-ready datasets → `06_outputs/ml_ready/`
- Visualizations → `06_outputs/visuals/`
- Wind field maps → `06_outputs/visuals/hurdat2/`
- QAQC maps → `06_outputs/visuals/hurdat2_census/`

**Questions?** Check the `00_documentation/` folder first!
