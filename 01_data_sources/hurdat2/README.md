# HURDAT2 Hurricane Track Data

## Overview
HURDAT2 (Hurricane Database 2) provides best-track data for Atlantic and Pacific hurricanes.

## Data Source
- **Provider:** NOAA National Hurricane Center
- **URL:** https://www.nhc.noaa.gov/data/hurdat/
- **Format:** Fixed-width text file
- **Temporal Coverage:** 1851-present
- **Update Frequency:** Annual (post-season reanalysis)

## Processing Workflow
1. **Raw data:** `raw/hurdat2-atlantic.txt`
2. **Parsing:** `src/parse_raw.py` → Converts to structured CSV
3. **Output:** `processed/` → Cleaned storm data

## Quality Assurance
- **Visuals:** `visuals/html/` → QA maps and visualizations
- **Validation:** Check for missing timestamps, invalid coordinates

## Key Fields
- `storm_id`: Unique identifier (e.g., AL092021 for Ida)
- `timestamp`: 6-hourly observations (UTC)
- `lat`, `lon`: Storm center position
- `max_wind`: Maximum sustained wind (kt)
- `wind_radii_ne/se/sw/nw_64kt`: 64kt wind extent by quadrant (nm)

## Usage
```python
from data_sources.hurdat2.src.parse_raw import load_hurdat2
df = load_hurdat2('data_sources/hurdat2/raw/hurdat2-atlantic.txt')
```

## Streamlit Wind Field Viewer

An interactive viewer lives at `src/streamlit_wind_field_app.py`. It renders
arc-based wind-field polygons for a curated set of 14 Gulf Coast hurricanes.

```bash
streamlit run 01_data_sources/hurdat2/src/streamlit_wind_field_app.py
```

Configuration for the curated storm list resides in
`00_config/target_hurricanes.json`. Update that file if you need to adjust the
dashboard’s scope (all storm IDs must exist in HURDAT2).
