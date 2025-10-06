# Wind Coverage Envelope Transformation

## Purpose
Creates a spatial envelope (concave hull) around hurricane wind field extent using alpha shapes.

## Inputs
- HURDAT2 cleaned data: `../../data_sources/hurdat2/processed/`

## Outputs
- Envelope polygons: `outputs/{storm_id}_envelope.geojson`

## Key Algorithm
- Arc-based wind field geometry (30 points per quadrant)
- Proportional wind radii imputation for missing data
- Segmented alpha shape (α=0.6) with gap-aware segmentation

## Visuals
- **Methodology:** Arc vs chord comparison, imputation examples, alpha shape construction
- **Results:** Envelope maps for each storm

## Usage
```python
from transformations.wind_coverage_envelope.src.envelope_algorithm import create_wind_coverage_envelope
envelope = create_wind_coverage_envelope(storm_df, alpha=0.6)
```

## Documentation
See parent implementation plans for detailed algorithm explanation.
