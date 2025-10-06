# Dashboard Deployment Plan

## Context
Streamlit dashboard exists and runs successfully but requires feature CSV files to display storm data. Feature pipeline exists but has a bug preventing feature extraction.

## Workflow

### 1. Fix Feature Pipeline Bug
- Locate TractData intersects error in `feature_pipeline.py:68`
- Verify `load_tracts_with_centroids()` returns GeoDataFrame not TractData object
- Ensure spatial join uses proper GeoPandas method
- Test with single storm (Ida) before batch processing

### 2. Generate Feature CSV for Ida
- Run corrected pipeline for AL092021
- Validate output schema matches dashboard expectations
- Verify required columns: `tract_geoid`, `centroid_lat`, `centroid_lon`, `distance_km`, `storm_id`, `storm_name`
- Confirm optional columns present: `duration_in_envelope_hours`, `max_wind_experienced_kt`
- Save to `integration/outputs/ida_features_complete.csv`

### 3. Test Dashboard with Single Storm
- Verify dashboard detects new features file
- Confirm storm appears in selector dropdown
- Test all dashboard features: map, filters, charts, data table
- Check for rendering errors or missing data

### 4. Generate Features for All 14 Storms
- Create batch processing script if not exists
- Process storms sequentially with error handling
- Generate `*_features_complete.csv` for each storm
- Validate each output before proceeding

### 5. Final Dashboard Validation
- Confirm all 14 storms load correctly
- Test switching between storms
- Verify filtering controls work across all datasets
- Check performance with largest datasets

### 6. Documentation
- Update README_streamlit.md with prerequisites
- Document feature CSV schema requirements
- Add troubleshooting section for common issues
- Include example commands for feature generation

## File Organization

### Input Files
- `hurdat2/input_data/hurdat2-atlantic.txt`
- Census shapefiles in `census/input_data/`

### Code Files to Fix
- `integration/src/feature_pipeline.py`
- `hurdat2_census/src/tract_centroids.py` (if needed)

### Output Structure
```
integration/outputs/
├── ida_features_complete.csv
├── katrina_features_complete.csv
├── harvey_features_complete.csv
└── ...
```

### Dashboard Files
- `integration/src/streamlit_app.py`
- `integration/README_streamlit.md`

## Test Strategy

### Unit Tests
- Test spatial join logic with mock GeoDataFrame
- Verify feature extraction returns expected column set
- Test distance calculation accuracy

### Integration Tests
- Run full pipeline for Ida
- Compare output with existing partial datasets
- Validate tract counts match envelope filtering

### Dashboard Tests
- Manual verification of all interactive components
- Test edge cases: empty filters, single tract storms
- Performance test with concurrent storm loading

## Success Criteria
- Dashboard runs without errors at http://localhost:8501
- All 14 storms selectable with complete data
- Maps render correctly with envelopes and tracks
- Charts display accurate distributions
- Feature tables downloadable as CSV
- Process completes in under 30 minutes total

## Deployment Steps
1. Fix pipeline bug (15 min)
2. Test with Ida (10 min)
3. Batch process all storms (20 min)
4. Final validation (10 min)
5. Update documentation (10 min)

**Total: ~65 minutes**
