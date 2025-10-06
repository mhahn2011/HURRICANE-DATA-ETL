# Storm-Tract Distance Transformation

## Purpose
Calculates spatial relationships between hurricane tracks and census tracts.

## Inputs
- HURDAT2 track data: `../../data_sources/hurdat2/processed/`
- Census tract centroids: `../../data_sources/census/processed/`
- Wind coverage envelope: `../wind_coverage_envelope/outputs/`

## Outputs
- Distance features: `outputs/{storm_id}_tract_distances.csv`

## Key Features
- Minimum distance from tract centroid to storm track
- Nearest approach time
- Quadrant classification
- Within-envelope flag

## Visuals
- **Results:** Distance distribution maps and QA/QC visualizations

## Usage
```python
from transformations.storm_tract_distance.src.storm_tract_distance import calculate_distances
distances_df = calculate_distances(storm_df, tracts_gdf)
```
