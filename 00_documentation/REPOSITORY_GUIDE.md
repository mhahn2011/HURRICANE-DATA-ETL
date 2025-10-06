# Hurricane Data ETL Repository Guide

**Last Updated:** 2025-10-06 (Post-Migration Plan)
**Version:** 2.0

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Repository Structure](#repository-structure)
4. [Design Philosophy](#design-philosophy)
5. [Common Tasks](#common-tasks)
6. [Contributing](#contributing)
7. [Architecture Details](#architecture-details)
8. [Migration History](#migration-history)

---

## Overview

### Purpose

Extract hurricane impact features from HURDAT2 track data and US Census tract boundaries for machine learning analysis.

### Key Capabilities

- **Wind Speed Estimation:** Max wind at tract centroids using RMW plateau + exponential decay
- **Duration Calculation:** Hours of exposure to 64kt winds via 15-minute interpolation
- **Lead Time Detection:** Warning time before category thresholds reached
- **Distance Features:** Proximity to track with envelope-based filtering

### Output

ML-ready CSV files with ~37 features per storm-tract pair:
- Distance (km, nm)
- Wind (max, center, source tracking)
- Duration (hours, entry/exit times, continuous flag)
- Lead time (Cat 1-5 warning hours)
- Intensification (max rate, timing)

**Format:** `06_outputs/ml_ready/{storm_id}_features_complete.csv`

---

## Quick Start

### Installation

```bash
git clone <repository-url>
cd hurricane-data-etl
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Extract Features for Hurricane Ida

```bash
python 03_integration/src/feature_pipeline.py AL092021
# Output: 06_outputs/ml_ready/al092021_features_complete.csv (563 tracts)
```

### Process All 14 Storms

```bash
python 03_integration/scripts/batch_extract_features.py
# Outputs:
#   - 06_outputs/ml_ready/{storm}_features_complete.csv (14 files)
#   - 06_outputs/ml_ready/storm_tract_features.csv (master)
```

### Launch Interactive Dashboard

```bash
streamlit run 03_integration/src/streamlit_app.py
# Opens http://localhost:8501
# Select storm → View map, filters, charts, data table
```

### Run Tests

```bash
pytest 05_tests/ -v
# Expected: 48/51 tests passing
```

---

## Repository Structure

### Numbered Folder System

```
hurricane-data-etl/
│
├── 00_plans/                   # Implementation plans & architecture
│   └── MIGRATION_PLAN.md       # Current numbered structure migration
│
├── 00_documentation/           # Project documentation
│   ├── REPOSITORY_GUIDE.md     # This file (start here!)
│   ├── FEATURE_METHODOLOGY.md  # Algorithm explanations
│   └── ML_TOOLS_OVERVIEW.md    # MLflow, DVC, Hydra guide
│
├── 01_data_sources/            # Single-source data processing
│   ├── hurdat2/                # HURDAT2 hurricane tracks
│   │   ├── src/
│   │   │   ├── parse_raw.py           # Parse HURDAT2 text format
│   │   │   ├── profile_clean.py       # Data validation & cleaning
│   │   │   └── visualize_folium_qa.py # QA/QC HTML maps
│   │   ├── input_data/
│   │   │   └── hurdat2-atlantic.txt   # Raw HURDAT2 data
│   │   └── processed/
│   │       └── batch_processing_summary.csv
│   │
│   └── census/                 # Census TIGER/Line boundaries
│       ├── src/
│       │   └── tract_centroids.py     # Extract centroids from shapefiles
│       └── data/
│           └── tl_2019_*_tract.zip    # TIGER/Line shapefiles
│
├── 02_transformations/         # Multi-source feature engineering
│   ├── wind_coverage_envelope/
│   │   └── src/envelope_algorithm.py  # Alpha shapes, wind radii imputation
│   ├── storm_tract_distance/
│   │   └── src/storm_tract_distance.py # Distance calc, main pipeline
│   ├── wind_interpolation/
│   │   └── src/wind_interpolation.py  # RMW plateau + exponential decay
│   ├── duration/
│   │   └── src/duration_calculator.py # 15-min temporal interpolation
│   └── lead_time/
│       └── src/lead_time_calculator.py # Category threshold detection
│
├── 03_integration/             # Final assembly & validation
│   ├── src/
│   │   ├── feature_pipeline.py        # Main orchestration
│   │   ├── intensification_features.py # Storm-level metrics
│   │   └── streamlit_app.py           # Interactive dashboard
│   └── scripts/
│       └── batch_extract_features.py  # Process all 14 storms
│
├── 04_src_shared/              # Shared utilities
│   └── geometry_utils.py              # Haversine, bearings
│
├── 05_tests/                   # Test suite
│   ├── test_arc_polygons.py           # Arc geometry validation
│   ├── test_duration_calculator.py    # Temporal features
│   ├── test_wind_interpolation.py     # Wind estimation
│   └── ... (13 test files total)
│
├── 06_outputs/                 # All generated outputs
│   ├── ml_ready/              # ML-ready feature tables ⭐
│   │   ├── {storm_id}_features_complete.csv  # Per-storm
│   │   └── storm_tract_features.csv          # Master (all storms)
│   ├── visuals/               # Interactive HTML maps & plots
│   │   ├── hurdat2/          # Single-source HURDAT2 visuals
│   │   └── transformations/  # Multi-source QA/QC plots
│   └── reports/               # Summary tables, statistics
│
├── _legacy_data_sources/       # ⚠️ Being phased out (see migration plan)
├── requirements.txt
└── pytest.ini
```

---

## Design Philosophy

### 1. Numbered Folders = Processing Stages

**Rationale:** Visual representation of data flow

```
00_ → Planning & Documentation
01_ → Data Ingestion (immutable sources)
02_ → Transformations (feature engineering)
03_ → Integration (assembly, no logic)
04_ → Utilities (DRY principle)
05_ → Testing (quality assurance)
06_ → Outputs (final results)
```

**Benefits:**
- Folders sort in execution order
- New developers immediately understand flow
- Clear separation of concerns
- Matches ETL best practices (Airflow, DBT, Cookiecutter)

**Trade-off:** Python can't import from numbered folders directly → requires `sys.path` manipulation or `setup.py`

### 2. Single-Source vs Multi-Source Separation

**Rule:** `01_data_sources/` processes ONE data source only

**Examples:**
- ✅ `01_data_sources/hurdat2/` - HURDAT2 parsing, cleaning, imputation
- ✅ `01_data_sources/census/` - Tract loading, centroid extraction
- ❌ NO cross-source dependencies allowed in `01_`

**Rule:** `02_transformations/` combines multiple sources

**Examples:**
- ✅ `storm_tract_distance/` - Combines HURDAT2 + Census for spatial join
- ✅ `duration/` - Uses HURDAT2 track + Census centroids
- ✅ `wind_interpolation/` - Track data + tract locations → wind estimates

**Benefits:**
- Modularity: Can swap Census 2019 → 2020 without touching HURDAT2 code
- Testability: Unit test each source independently
- Reusability: HURDAT2 parser usable in other projects

### 3. Integration as Passive Assembler

**Rule:** `03_integration/` does NO transformation logic

**Responsibilities:**
- ✅ Combine transformation outputs
- ✅ Apply filtering/validation rules
- ✅ Export ML-ready datasets
- ❌ NO feature engineering
- ❌ NO complex calculations

**Benefits:**
- Transformations tested in isolation
- Easy to change assembly logic
- Clear validation layer
- Single responsibility principle

### 4. Self-Documenting Structure

**Each transformation is a bounded context:**

```
02_transformations/duration/
├── src/duration_calculator.py  # Implementation
├── tests/                       # Validation
├── README.md                    # Purpose & algorithm
└── outputs/                     # Intermediate results (optional)
```

**Benefits:**
- New dev knows exactly where duration code lives
- Each module is self-contained
- Easy to add new transformations (just add folder)
- Domain-Driven Design principles

---

## Common Tasks

### Extract Features for One Storm

```bash
# Basic usage
python 03_integration/src/feature_pipeline.py AL092021

# Custom output location
python 03_integration/src/feature_pipeline.py AL092021 \
  --output /custom/path/ida_features.csv

# Different census year
python 03_integration/src/feature_pipeline.py AL092021 \
  --census-year 2020

# Custom bounds margin (tract filtering)
python 03_integration/src/feature_pipeline.py AL092021 \
  --bounds-margin 5.0
```

**Output:** `06_outputs/ml_ready/al092021_features_complete.csv`

### Generate Wind Field Visualization

```bash
python 01_data_sources/hurdat2/src/visualize_folium_qa.py --storm-id AL092021
# Output: 06_outputs/visuals/hurdat2/IDA_2021_wind_field.html
```

**Open in browser:**
```bash
open 06_outputs/visuals/hurdat2/IDA_2021_wind_field.html
```

### Run Specific Tests

```bash
# All tests
pytest 05_tests/ -v

# Specific module
pytest 05_tests/test_arc_polygons.py -v

# With coverage
pytest 05_tests/ --cov=01_data_sources --cov=02_transformations --cov-report=html
```

### Add New Transformation

**Example: Adding "pressure_gradient" feature**

1. Create structure:
```bash
mkdir -p 02_transformations/pressure_gradient/{src,tests}
touch 02_transformations/pressure_gradient/src/__init__.py
touch 02_transformations/pressure_gradient/src/pressure_gradient_calculator.py
touch 02_transformations/pressure_gradient/tests/test_pressure_gradient.py
touch 02_transformations/pressure_gradient/README.md
```

2. Implement `pressure_gradient_calculator.py`:
```python
def calculate_pressure_gradient(track_df: pd.DataFrame) -> Dict:
    """Calculate pressure gradient features."""
    # Implementation here
    return {"max_pressure_drop": ..., "gradient_at_landfall": ...}
```

3. Add to integration pipeline:
```python
# 03_integration/src/feature_pipeline.py
pressure_features = calculate_pressure_gradient(track_df)
features[...] = pressure_features
```

4. Write tests:
```python
# 02_transformations/pressure_gradient/tests/test_pressure_gradient.py
def test_pressure_gradient_calculation():
    # Test logic here
    pass
```

### Debug Import Issues

```bash
# Check which modules are importable
python -c "import sys; sys.path.insert(0, '01_data_sources/hurdat2/src'); from parse_raw import parse_hurdat2_file; print('✅ Import successful')"

# Find all sys.path statements
grep -r "sys.path" --include="*.py" .

# Verify no legacy paths
grep -r "_legacy_data_sources" --include="*.py" .
```

---

## Contributing

### Adding New Features

**Single-source processing (e.g., new HURDAT2 field):**
→ Add to `01_data_sources/{source}/src/`

**Multi-source transformation (e.g., new feature combining track + tracts):**
→ Add to `02_transformations/{feature_name}/src/`

**Integration logic (e.g., new filtering rule):**
→ Add to `03_integration/src/`

### Testing Guidelines

**Structure:**
- Unit tests: In transformation folder (`02_transformations/{feature}/tests/`)
- Integration tests: In `05_tests/integration/`
- Data source tests: In `05_tests/data_sources/`

**Example:**
```python
# 02_transformations/duration/tests/test_duration_calculator.py
def test_duration_for_stationary_point():
    """Point inside envelope entire time should have duration = track length"""
    # Arrange
    centroid = Point(-90.0, 29.0)
    track = pd.DataFrame(...)  # 8-hour track

    # Act
    duration = calculate_duration_for_tract(centroid, track)

    # Assert
    assert duration['duration_in_envelope_hours'] == 8.0
```

### Code Style

- **Imports:** Use absolute imports where possible
- **Docstrings:** Google style for all public functions
- **Type hints:** Use for function signatures
- **Naming:** Snake_case for functions, PascalCase for classes
- **Line length:** 100 characters max

---

## Architecture Details

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 01_DATA_SOURCES                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐           ┌──────────┐                       │
│  │ HURDAT2  │           │  Census  │                       │
│  │  Parser  │           │  Loader  │                       │
│  └────┬─────┘           └────┬─────┘                       │
│       │                      │                              │
│       ├─ Clean track data   ├─ Tract centroids            │
│       ├─ Impute wind radii  └─ GEOID mappings             │
│       └─ QA/QC validation                                  │
│                                                              │
└──────────────┬───────────────┬───────────────────────────┘
               │               │
               ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│ 02_TRANSFORMATIONS (Feature Engineering)                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────┐  ┌───────────────────┐             │
│  │ Wind Coverage     │  │ Storm-Tract       │             │
│  │ Envelope          │→ │ Distance          │             │
│  └───────────────────┘  └───────────────────┘             │
│           ↓                       ↓                         │
│  ┌───────────────────┐  ┌───────────────────┐             │
│  │ Wind              │  │ Duration          │             │
│  │ Interpolation     │  │ Calculator        │             │
│  └───────────────────┘  └───────────────────┘             │
│           ↓                       ↓                         │
│  ┌───────────────────┐                                     │
│  │ Lead Time         │                                     │
│  │ Calculator        │                                     │
│  └───────────────────┘                                     │
│                                                              │
└──────────────────────┬─────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 03_INTEGRATION (Assembly & Validation)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────┐                                     │
│  │ Feature Pipeline  │  ← Orchestrates all transformations │
│  └─────────┬─────────┘                                     │
│            │                                                │
│            ├─ Combine features                             │
│            ├─ Apply filters (>0.25hr threshold)            │
│            ├─ Validate schemas                             │
│            └─ Export ML-ready CSV                          │
│                                                              │
└──────────────────────┬─────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 06_OUTPUTS                                                   │
├─────────────────────────────────────────────────────────────┤
│  ml_ready/                                                   │
│    ├─ al092021_features_complete.csv  (563 tracts)         │
│    └─ storm_tract_features.csv        (all 14 storms)      │
│                                                              │
│  visuals/                                                    │
│    ├─ IDA_2021_wind_field.html                             │
│    └─ qaqc_duration_histogram.png                          │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Graph

```
parse_raw.py → profile_clean.py → envelope_algorithm.py
                                         ↓
tract_centroids.py ────────────→ storm_tract_distance.py
                                         ↓
                     ┌──────────────────┴──────────────────┐
                     ↓                                      ↓
         wind_interpolation.py              duration_calculator.py
                     ↓                                      ↓
         lead_time_calculator.py ← intensification_features.py
                     ↓
              feature_pipeline.py
                     ↓
            batch_extract_features.py
```

### Import Strategy

**Problem:** Python can't import from folders starting with numbers

**Solution:** Use `sys.path` manipulation in each script

```python
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[N]  # N = depth
sys.path.extend([
    str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
    str(REPO_ROOT / "02_transformations" / "duration" / "src"),
])

# Then import normally
from parse_raw import parse_hurdat2_file
from duration_calculator import calculate_duration_for_tract
```

**Future improvement:** Create `setup.py` for installable package

---

## Migration History

### Pre-2025-10-05: Flat Structure

```
hurdat2/
census/
hurdat2_census/
integration/
tests/
```

**Issues:**
- Unclear which folders are sources vs transformations
- `hurdat2_census` mixed feature engineering with data
- No visual indication of processing order

### 2025-10-05: Numbered Structure Introduced

**Decision:** Adopt numbered folders to make ETL flow explicit

**Changes:**
- Introduced `01_`, `02_`, `03_`, `06_` prefixes
- Moved old folders to `_legacy_data_sources/`
- Copied code to new structure
- Updated documentation

**Status:** Partially complete (documentation updated, code migration in progress)

### 2025-10-06: Migration Plan Created

**Next steps:**
- Update import paths in 4 key files
- Update output paths to use `06_outputs/`
- Run full test suite
- Delete `_legacy_data_sources/`

**See:** `00_plans/MIGRATION_PLAN.md` for execution details

### Future: Installable Package

**Goals:**
- Create `setup.py` for `pip install -e .`
- Replace `sys.path` with proper imports
- Add environment-based configuration
- Integrate MLflow for experiment tracking

---

## Comparison to ML Standards

### Standard ML Structure

```
ml-project/
├── data/              # Raw, processed, features
├── notebooks/         # Exploration
├── src/               # Source code
├── models/            # Trained models
├── tests/
└── outputs/
```

### This Repository (ETL-Optimized)

```
hurricane-data-etl/
├── 01_data_sources/   # ≈ data/raw/
├── 02_transformations/ # ≈ src/features/
├── 03_integration/    # ≈ src/models/ (but no training)
├── 05_tests/          # ≈ tests/
└── 06_outputs/        # ≈ outputs/
```

**Key Difference:** This is a **feature extraction pipeline**, not a model training repo.

**Why numbered folders work here:**
- ETL pipelines have clear sequential stages
- Mirrors Airflow DAGs, DBT models, Cookiecutter Data Science
- Makes data flow explicit (01 → 02 → 03 → 06)

**When to use standard structure:**
- If adding model training (→ `models/` folder)
- If adding exploratory notebooks (→ `notebooks/` folder)
- If packaging for PyPI distribution

---

## Frequently Asked Questions

### Why numbered folders?

**Answer:** Makes ETL data flow explicit. Standard ML repos don't need this because they're model-centric, but feature pipelines benefit from visual stage representation.

### Can I use standard `src/` structure instead?

**Answer:** Yes, but you lose the visual ordering. If you prefer semantic names, use:
- `data/` instead of `01_data_sources/`
- `features/` instead of `02_transformations/`
- `pipelines/` instead of `03_integration/`

### How do imports work with numbered folders?

**Answer:** Currently via `sys.path` manipulation. Future: Create `setup.py` for `pip install -e .` to enable standard imports.

### Where should I put notebooks?

**Answer:** Create `notebooks/` in repo root. Not numbered because they're exploratory, not part of production pipeline.

### Is this structure overkill for small projects?

**Answer:** For <3 storms, yes. For 14+ storms with multiple features, the structure prevents chaos.

---

## Additional Resources

- **Algorithm Details:** `00_documentation/FEATURE_METHODOLOGY.md`
- **ML Tools Guide:** `00_documentation/ML_TOOLS_OVERVIEW.md`
- **Migration Plan:** `00_plans/MIGRATION_PLAN.md`
- **Test Suite:** `05_tests/README.md`
- **Dashboard Guide:** `03_integration/README_streamlit.md`

---

## Summary

**This repository uses a numbered folder system optimized for ETL pipelines:**
- Clear data flow (01 → 02 → 03 → 06)
- Separation of concerns (data ≠ transform ≠ assembly)
- Self-documenting structure (folder name = purpose)
- Matches industry patterns (Airflow, DBT, Cookiecutter)

**Not standard ML, but excellent for feature extraction pipelines.**

**Quick commands:**
```bash
# Extract features
python 03_integration/src/feature_pipeline.py AL092021

# Run tests
pytest 05_tests/ -v

# Launch dashboard
streamlit run 03_integration/src/streamlit_app.py
```
