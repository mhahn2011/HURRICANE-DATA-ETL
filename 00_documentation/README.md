# Hurricane Data ETL - Project Documentation

**Extract hurricane impact features for census tract-level machine learning analysis**

---

## Quick Start

### What This Project Does

Combines HURDAT2 historical hurricane track data with US Census tract boundaries to create ML-ready features:
- **Wind Speed** - Maximum wind experienced at tract centroid
- **Duration** - Hours of exposure to wind thresholds (34kt, 50kt, 64kt)
- **Lead Time** - Warning time before category thresholds reached
- **Distance** - Proximity to storm track

### Installation

```bash
# Clone repository
git clone <repository-url>
cd hurricane-data-etl

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Feature Extraction

```bash
# Extract features for Hurricane Ida (2021)
python 02_transformations/storm_tract_distance/src/storm_tract_distance.py --storm-id AL092021

# Or use the main pipeline
python 03_integration/src/feature_pipeline.py --storm-id AL092021

# Process all 14 Gulf Coast hurricanes
python 03_integration/scripts/batch_extract_features.py
```

### Run Tests

```bash
# All tests
python -m pytest 05_tests/ -v

# Specific test
python -m pytest 05_tests/test_wind_interpolation.py -v
```

---

## Documentation Index

### 📚 Core Documentation

| Document | Purpose |
|----------|---------|
| **[REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md)** | Folder organization, design principles, contributor guide |
| **[FEATURE_METHODOLOGY.md](FEATURE_METHODOLOGY.md)** | Algorithm documentation, computational methods, validation |

### 📋 Implementation Plans

Located in `00_plans/`:
- REFACTORING_IMPLEMENTATION_PLAN.md
- IMPLEMENTATION_PLANS/ (completed and active plans)

---

## Repository Structure

```
hurricane-data-etl/
│
├── 01_data_sources/        # Single-source data processing
│   ├── hurdat2/           # HURDAT2 hurricane tracks
│   └── census/            # Census tract boundaries
│
├── 02_transformations/     # Multi-source feature engineering
│   ├── wind_coverage_envelope/
│   ├── storm_tract_distance/
│   ├── wind_interpolation/
│   ├── duration/
│   └── lead_time/
│
├── 03_integration/         # Final assembly & validation
├── 04_src_shared/          # Shared utilities
├── 05_tests/               # Test suite (48/51 passing)
├── 06_outputs/             # All outputs (ML datasets & visualizations)
└── 00_documentation/       # This folder
```

**See [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) for details.**

---

## Key Features

### ✅ Implemented

- **Arc-Based Wind Field Geometry** - 10-30% area improvement
- **Wind Coverage Envelope** - Alpha shape concave hulls
- **Wind Speed Interpolation** - RMW plateau + exponential decay  
- **Duration Calculation** - 15-minute temporal interpolation
- **Lead Time Features** - Category threshold detection

**See [FEATURE_METHODOLOGY.md](FEATURE_METHODOLOGY.md) for algorithms.**

---

## Testing

**51 tests total** (48 passing, 1 failing, 1 skipped, 1 xfailed)

```bash
# Run all tests
python -m pytest 05_tests/ -v
```

---

## Common Tasks

### Extract Features for a Storm

```bash
python 02_transformations/storm_tract_distance/src/storm_tract_distance.py \
  --storm-id AL092021 \
  --output 06_outputs/ml_ready/ida_features.csv
```

### Generate Visualizations

```bash
python 01_data_sources/hurdat2/src/visualize_folium_qa.py \
  --storm-id AL092021

# Output saved to: 06_outputs/visuals/hurdat2/IDA_2021_wind_field.html
```

---

## Project Status

**Current Phase:** Production-ready feature extraction

**Recent Updates:**
- ✅ Arc-based wind geometry implemented (2025-10-05)
- ✅ Repository restructured to numbered folders (2025-10-05)
- ✅ Documentation refactored and consolidated (2025-10-05)
- ✅ 48/51 tests passing

---

**Start exploring:** [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) → [FEATURE_METHODOLOGY.md](FEATURE_METHODOLOGY.md)
