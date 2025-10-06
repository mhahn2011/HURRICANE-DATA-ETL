# Hurricane Data ETL

**Extract hurricane impact features for census tract-level machine learning analysis**

[![Tests](https://img.shields.io/badge/tests-48%2F51%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)]()

---

## 🚀 Quick Start

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
# Output: 06_outputs/ml_ready/al092021_features.csv
```

### Generate Wind Field Visualization

```bash
python 01_data_sources/hurdat2/src/visualize_folium_qa.py --storm-id AL092021
# Output: 06_outputs/visuals/hurdat2/IDA_2021_wind_field.html
open 06_outputs/visuals/hurdat2/IDA_2021_wind_field.html
```

### Run Tests

```bash
pytest 05_tests/ -v
```

---

## 📊 What This Project Does

Combines **HURDAT2 hurricane track data** with **US Census tract boundaries** to create ML-ready features:

- **🌬️ Wind Speed** - Maximum wind experienced at tract centroid
- **⏱️ Duration** - Hours of exposure to wind thresholds (34kt, 50kt, 64kt)
- **⚠️ Lead Time** - Warning time before category thresholds reached
- **📍 Distance** - Proximity to storm track

---

## 📁 Repository Structure

```
hurricane-data-etl/
├── 00_plans/               # Implementation plans & architecture docs
├── 00_documentation/       # Project documentation (START HERE!)
├── 01_data_sources/        # HURDAT2 & Census data processing
├── 02_transformations/     # Feature engineering (wind, duration, lead time)
├── 03_integration/         # Final assembly & validation
├── 04_src_shared/          # Shared utilities
├── 05_tests/               # Test suite (48/51 passing)
└── 06_outputs/             # All outputs (ML datasets & visualizations)
    ├── ml_ready/          # Final feature CSVs
    └── visuals/           # Interactive maps & plots
```

**📖 Full Documentation:** [`00_documentation/README.md`](00_documentation/README.md)

---

## 🎯 Key Features

### ✅ Arc-Based Wind Geometry
- True circular arcs (not chord approximations)
- 10-30% area improvement over previous methods
- 30 sample points per quadrant

### ✅ Wind Coverage Envelope
- Alpha shape concave hulls
- Handles missing wind radii with proportional imputation
- Segmented for data gaps

### ✅ Advanced Wind Interpolation
- RMW plateau + exponential decay model
- Accounts for eyewall structure
- Source tracking for all estimates

### ✅ Temporal Resolution
- 15-minute interpolation from 6-hourly observations
- Duration accumulation with 0.25-hour minimum threshold
- Lead time detection for all Saffir-Simpson categories

---

## 📈 Output Examples

### ML-Ready Feature Table

```csv
geoid,storm_id,storm_name,year,distance_to_track_km,max_wind_kt,duration_64kt_hours,lead_time_cat3_hours
28047950100,AL092021,IDA,2021,45.2,78,6.5,18.2
22071001800,AL092021,IDA,2021,12.8,105,12.0,24.5
```

### Interactive Wind Field Map

![Wind Field Example](https://via.placeholder.com/800x400?text=Interactive+Folium+Map)

See: `06_outputs/visuals/hurdat2/IDA_2021_wind_field.html`

---

## 🌀 Storm Coverage

**14 Gulf Coast Hurricanes (2005-2022):**

| Year | Storms |
|------|--------|
| 2005 | Katrina, Rita, Dennis |
| 2008 | Gustav, Ike |
| 2017 | Harvey, Irma |
| 2018 | Michael |
| 2020 | Laura, Delta, Zeta, Sally |
| 2021 | Ida |
| 2022 | Ian |

**Geographic Extent:** Louisiana, Mississippi, Texas, Alabama, Florida

---

## 📚 Documentation Index

| Document | Purpose |
|----------|---------|
| [**README.md**](00_documentation/README.md) | Project overview & quick start |
| [**FEATURE_METHODOLOGY.md**](00_documentation/FEATURE_METHODOLOGY.md) | Algorithm documentation |
| [**REPOSITORY_STRUCTURE.md**](00_documentation/REPOSITORY_STRUCTURE.md) | Folder organization & design principles |
| [**06_outputs/README.md**](06_outputs/README.md) | Output directory guide |
| [**06_outputs/visuals/README.md**](06_outputs/visuals/README.md) | Visualization guide |

---

## 🧪 Testing

```bash
# All tests
pytest 05_tests/ -v

# Specific test
pytest 05_tests/test_arc_polygons.py -v

# With coverage
pytest 05_tests/ --cov=01_data_sources --cov=02_transformations
```

**Status:** 48/51 tests passing

---

## 🛠️ Common Tasks

### Process All 14 Storms

```bash
python 03_integration/scripts/batch_extract_features.py
# Output: 06_outputs/ml_ready/storm_tract_features.csv
```

### Extract Distance Features

```bash
python 02_transformations/storm_tract_distance/src/storm_tract_distance.py \
  --storm-id AL092021 \
  --output 06_outputs/ml_ready/custom_output.csv
```

### Generate QAQC Visualizations

```bash
# See legacy scripts for examples
ls _legacy_data_sources/hurdat2_census/src/qaqc_*.py
```

---

## 🔬 Methodology Highlights

### Coordinate System
- **EPSG:4326** (WGS84 lat/lon)
- Spherical trigonometry for arc generation
- Great-circle distance calculations

### Wind Field Model
- **Inside RMW:** Constant max wind
- **Outside RMW:** Exponential decay (λ=0.15)
- **Default RMW:** 20 nm when missing

### Data Quality
- Wind radii imputation with proportional scaling
- Source tracking for all derived values
- Validation against NOAA advisories

**Full Details:** [FEATURE_METHODOLOGY.md](00_documentation/FEATURE_METHODOLOGY.md)

---

## 📊 Project Status

**Current Phase:** Production-ready feature extraction

**Recent Updates:**
- ✅ Arc-based wind geometry (2025-10-05)
- ✅ Repository restructure to numbered folders (2025-10-06)
- ✅ Output consolidation in 06_outputs/ (2025-10-06)
- ✅ Comprehensive documentation (2025-10-06)

---

## 🤝 Contributing

### Adding New Features

**Single-source processing:**
→ Add to `01_data_sources/{source}/src/`

**Multi-source transformation:**
→ Add to `02_transformations/{feature_name}/src/`

**Integration logic:**
→ Add to `03_integration/src/`

### Running Tests for New Code

```bash
# Create test file
touch 05_tests/test_your_feature.py

# Run tests
pytest 05_tests/test_your_feature.py -v
```

---

## 📄 License

[Add license information here]

---

## 📞 Contact

[Add contact information here]

---

## 🙏 Acknowledgments

### Data Sources
- **HURDAT2:** NOAA National Hurricane Center
- **Census TIGER/Line:** US Census Bureau

### Algorithms
- Alpha Shapes: Edelsbrunner et al. (1983)
- Wind Decay Model: Adapted from Holland (1980)

---

## 🔗 Quick Links

- **Main Documentation:** [00_documentation/README.md](00_documentation/README.md)
- **Outputs Guide:** [06_outputs/README.md](06_outputs/README.md)
- **Visualizations:** [06_outputs/visuals/README.md](06_outputs/visuals/README.md)
- **Test Suite:** [05_tests/](05_tests/)
- **Implementation Plans:** [00_plans/](00_plans/)

---

**Ready to explore?** Start with [`00_documentation/README.md`](00_documentation/README.md) for the full project overview!
