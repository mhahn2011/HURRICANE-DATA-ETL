# Hurricane Data ETL Repository Setup

## Multi-Source Repository Structure

```bash
hurricane-data-etl/
├── README.md
├── .gitignore
├── requirements.txt
├── hurdat2/
│   ├── input_data/                # Raw HURDAT2 files
│   ├── src/
│   │   ├── parse_raw.py          # Parse weird format → clean table
│   │   ├── profile_clean.py      # EDA on clean table
│   │   └── transform_ml.py       # Transform → storm×tract features
│   ├── notebooks/
│   │   └── hurdat2_analysis.ipynb
│   └── outputs/
│       ├── clean_storm_tracks.csv
│       ├── eda_report.html
│       └── storm_tract_features.csv
├── fema/
│   ├── input_data/
│   ├── src/
│   │   ├── parse_raw.py
│   │   ├── profile_clean.py
│   │   └── transform_ml.py
│   └── outputs/
├── census/
│   ├── input_data/
│   ├── src/
│   │   ├── parse_raw.py
│   │   ├── profile_clean.py
│   │   └── transform_ml.py
│   └── outputs/
├── integration/
│   ├── src/
│   │   └── combine_sources.py
│   └── outputs/
│       └── ml_ready_dataset.csv
└── shared/
    ├── spatial_utils.py
    └── data_quality.py
```

## Repository Creation

```bash
# Create repository structure
mkdir hurricane-data-etl
cd hurricane-data-etl
git init

# Create multi-source directory structure
mkdir -p {hurdat2,fema,census,integration,shared}/{input_data,src,outputs}
mkdir -p {hurdat2,fema,census}/notebooks
mkdir -p integration/outputs/ml_ready_data

# Create core files
touch README.md .gitignore requirements.txt
touch {hurdat2,fema,census}/src/{parse_raw.py,profile_clean.py,transform_ml.py}
touch integration/src/combine_sources.py
touch shared/{spatial_utils.py,data_quality.py}
```

## Essential Configuration Files

### .gitignore
```gitignore
# Raw data files (never commit)
*/input_data/
*.txt
*.csv
*.json
*.xlsx

# Python
__pycache__/
*.pyc
.env
.venv/

# Jupyter
.ipynb_checkpoints/

# Large output files (optional)
*/outputs/eda_report.html
*/outputs/*_features.csv
```

### requirements.txt
```txt
# Core data processing
pandas>=2.0.0
numpy>=1.24.0
geopandas>=0.13.0

# Data acquisition
requests>=2.31.0

# EDA and profiling
ydata-profiling>=4.5.0
matplotlib>=3.7.0
seaborn>=0.12.0

# Geospatial calculations
pyproj>=3.6.0
shapely>=2.0.0
geopy>=2.3.0

# Polygon processing for envelope approach
rtree>=1.0.0

# Progress tracking
tqdm>=4.65.0

# Jupyter (optional)
jupyter>=1.0.0
```

### README.md Template
```markdown
# Hurricane Data ETL Pipeline

Multi-source data processing for hurricane impact modeling.

## Quick Start - HURDAT2

```bash
# Install dependencies
pip install -r requirements.txt

# Process HURDAT2 data
cd hurdat2
python src/parse_raw.py          # Raw format → clean table
python src/profile_clean.py      # Generate EDA report
python src/transform_ml.py       # Create storm×tract features
```

## Repository Structure

Each data source follows the same pattern:
- `input_data/` - Raw downloaded files (git ignored)
- `src/parse_raw.py` - Handle source-specific format issues
- `src/profile_clean.py` - EDA on clean tabular data
- `src/transform_ml.py` - Transform to ML granularity (storm×tract)
- `outputs/` - Processed datasets and reports

## Data Processing Pipeline

### Stage 1: Source-Specific Processing
```
Raw HURDAT2 → clean_storm_tracks.csv → storm_tract_features.csv
Raw FEMA → clean_damage_data.csv → damage_tract_features.csv
Raw Census → clean_demographics.csv → demographic_features.csv
```

### Stage 2: Integration
```
All *_tract_features.csv → ml_ready_dataset.csv
```

## Key Outputs

- `hurdat2/outputs/storm_tract_features.csv` - Storm impact features per tract
- `integration/outputs/ml_ready_dataset.csv` - Combined feature matrix
- `*/outputs/eda_report.html` - Data quality reports

## Implementation Priority

1. **Start with HURDAT2** - Core storm data
2. **Add Census demographics** - Social vulnerability 
3. **Integrate FEMA damage data** - Target variables
4. **Combine sources** - Final ML dataset
```

## Workflow per Data Source

### Standard Processing Steps
```bash
# For any source (hurdat2, fema, census):
cd {source_name}

# Step 1: Parse raw format → clean table
python src/parse_raw.py

# Step 2: Profile & understand clean data  
python src/profile_clean.py
# Opens: outputs/eda_report.html

# Step 3: Transform to ML granularity
python src/transform_ml.py
# Creates: outputs/{source}_tract_features.csv
```

### Integration Step
```bash
# Combine all sources
cd integration
python src/combine_sources.py
# Creates: outputs/ml_ready_dataset.csv
```

## Git Workflow

```bash
# Track code and documentation, not data
git add README.md .gitignore requirements.txt
git add */src/ shared/ integration/
git add */notebooks/

git commit -m "Hurricane ETL repository setup

- Multi-source structure: HURDAT2, FEMA, Census
- Consistent parse → profile → transform pipeline
- Shared utilities for spatial calculations
- Integration layer for ML feature matrix"

git remote add origin https://github.com/yourusername/hurricane-data-etl.git
git push -u origin main
```

## Shared Utilities

### spatial_utils.py
Common geospatial functions:
- Distance calculations (Haversine)
- Bearing calculations
- Quadrant assignments
- Wind decay models

### data_quality.py
Validation functions:
- Missing data assessment
- Outlier detection
- Spatial validation
- Cross-source consistency checks

## Future Integration

This repository creates standardized feature matrices that integrate easily with ML projects:

```python
# In separate ML repository
import pandas as pd
features = pd.read_csv('hurricane-data-etl/integration/outputs/ml_ready_dataset.csv')
```

The modular structure allows independent development of each data source while maintaining consistency for final integration.