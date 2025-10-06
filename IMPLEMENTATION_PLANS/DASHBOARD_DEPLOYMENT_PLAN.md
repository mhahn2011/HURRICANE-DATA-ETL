# Dashboard Deployment Plan

## Context
Streamlit dashboard exists and runs successfully but requires feature CSV files to display storm data. Feature pipeline has been refactored to delegate to the modern `storm_tract_distance` pipeline.

## Status: Phase 1 Complete ✅

### 1. Fix Feature Pipeline Bug ✅ COMPLETE
- ✅ Replaced hand-rolled extractor with wrapper around `storm_tract_distance.run_pipeline`
- ✅ Fixed by delegating to modern pipeline instead of manual spatial join
- ✅ Added CLI interface with argparse
- ✅ Default output path: `integration/outputs/{storm_id}_features_complete.csv`

### 2. Generate Feature CSV for Ida ✅ COMPLETE
- ✅ Successfully generated via: `python integration/src/feature_pipeline.py AL092021`
- ✅ Output: 563 rows × 37 columns (229 KB)
- ✅ Validated schema includes all required columns
- ✅ Duration statistics look reasonable (mean: 4.2 hrs, range: 0.25-8 hrs)
- ✅ Includes intensification features (lead time, max intensification rate, etc.)

### 3. Test Dashboard with Single Storm ⏳ READY TO TEST
- ✅ Dashboard running at http://localhost:8501
- ✅ Streamlit dependencies installed
- ⏸️ Manual browser testing needed to confirm:
  - Storm appears in selector dropdown
  - Map renders with envelope and track
  - Filters work correctly
  - Charts display duration/distance/wind distributions
  - Data table shows all 563 tracts

### 4. Generate Features for All 14 Storms ⏳ READY TO RUN
- ✅ Batch script exists: `integration/scripts/batch_extract_features.py`
- ✅ Script updated to save per-storm CSVs alongside master rollup
- ✅ Reads storm list from `hurdat2/outputs/batch_processing_summary.csv`
- ⏸️ **Action needed:** Run batch processor
  ```bash
  python integration/scripts/batch_extract_features.py
  ```
- Expected output:
  - Individual files: `integration/outputs/{storm_id}_features_complete.csv` (14 files)
  - Master rollup: `integration/outputs/storm_tract_features.csv`
  - Console summary with tract counts per storm

### 5. Final Dashboard Validation ⏸️ PENDING BATCH RUN
- Open http://localhost:8501 in browser
- Confirm all 14 storms appear in dropdown
- Test switching between storms
- Verify filtering controls work across all datasets
- Check performance with largest datasets (Harvey, Irma likely largest)
- Validate chart rendering for all storms

### 6. Documentation ⏸️ TODO
- Update README_streamlit.md:
  - Add CLI usage examples for feature generation
  - Document 37-column schema
  - Add troubleshooting for missing features files
- Add example workflow:
  ```bash
  # Single storm
  python integration/src/feature_pipeline.py AL092021

  # All 14 storms
  python integration/scripts/batch_extract_features.py

  # Launch dashboard
  streamlit run integration/src/streamlit_app.py
  ```

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

### Completed ✅
1. ✅ Fix pipeline bug (15 min) - Refactored to use modern pipeline
2. ✅ Test with Ida (10 min) - Generated 563-tract CSV successfully
3. ✅ Install Streamlit dependencies - Dashboard running

### Remaining ⏸️
4. **Test dashboard with Ida** (5 min)
   - Open http://localhost:8501 in browser
   - Verify Ida loads and all features work

5. **Batch process remaining 13 storms** (20-30 min)
   ```bash
   python integration/scripts/batch_extract_features.py
   ```

6. **Final validation** (10 min)
   - Test all 14 storms in dashboard
   - Verify chart performance
   - Check edge cases

7. **Update documentation** (10 min)
   - Add CLI usage to README_streamlit.md
   - Document schema
   - Add troubleshooting guide

**Completed: ~25 minutes**
**Remaining: ~45-55 minutes**
**Total: ~70-80 minutes**
