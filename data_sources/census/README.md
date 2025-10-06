# US Census Tract Data

## Overview
Census tract boundaries and centroids for spatial analysis.

## Data Source
- **Provider:** US Census Bureau
- **Product:** TIGER/Line Shapefiles
- **URL:** https://www.census.gov/geographies/mapping-files.html
- **Year:** 2019/2020

## Processing Workflow
1. **Raw data:** `raw/*.shp` (TIGER/Line shapefiles)
2. **Extraction:** `src/tract_centroids.py` → Calculate centroids
3. **Output:** `processed/` → Tract centroids and metadata

## Quality Assurance
- **Visuals:** `visuals/html/` → Tract boundary maps
- **Validation:** Check for null geometries, invalid polygons

## Key Fields
- `GEOID`: 11-digit census tract identifier
- `centroid_lat`, `centroid_lon`: Tract centroid coordinates
- `land_area_sqkm`: Land area (for density calculations)

## Usage
```python
from data_sources.census.src.tract_centroids import load_tract_centroids
gdf = load_tract_centroids('data_sources/census/processed/')
```
