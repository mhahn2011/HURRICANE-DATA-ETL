# Feature Results Visualization Scripts

This directory contains scripts that generate interactive Folium maps to visualize the spatial distribution of extracted hurricane features across census tracts.

## Available Scripts

### 1. Storm-Tract Distance Features
**Location:** `storm_tract_distance/visuals/generate_feature_result_maps.py`

Generates three visualizations:
- `feature_results_distance_to_track.html` - Distance from tract centroids to hurricane track centerline
- `feature_results_wind_speed.html` - Maximum wind speeds experienced by each tract
- `feature_results_duration_in_envelope.html` - Duration of wind exposure for each tract

**Usage:**
```bash
cd /Users/Michael/hurricane-data-etl
python 02_transformations/storm_tract_distance/visuals/generate_feature_result_maps.py
```

### 2. Lead Time Features
**Location:** `lead_time/visuals/generate_lead_time_maps.py`

Generates five visualizations (one per Saffir-Simpson category):
- `feature_results_lead_time_cat1.html` - Warning time before Category 1 winds (64kt)
- `feature_results_lead_time_cat2.html` - Warning time before Category 2 winds (83kt)
- `feature_results_lead_time_cat3.html` - Warning time before Category 3 winds (96kt)
- `feature_results_lead_time_cat4.html` - Warning time before Category 4 winds (113kt)
- `feature_results_lead_time_cat5.html` - Warning time before Category 5 winds (137kt)

**Usage:**
```bash
cd /Users/Michael/hurricane-data-etl
python 02_transformations/lead_time/visuals/generate_lead_time_maps.py
```

## Output Location

All visualizations are saved to: `06_outputs/visuals/hurdat2_census/`

## Dependencies

These scripts require:
- Feature data: `06_outputs/ml_ready/ida_features.csv`
- HURDAT2 data: `01_data_sources/hurdat2/raw/hurdat2-atlantic.txt`
- Python packages: folium, pandas, shapely, numpy

## Color Schemes

Each visualization uses appropriate color scales:
- **Distance**: Blue (close) → Yellow → Red (far)
- **Wind Speed**: White (low) → Red (high), aligned with Saffir-Simpson categories
- **Duration**: White → Purple → Pink → Red → Black (increasing exposure)
- **Lead Time**: Green (long warning) → Red (short warning)
