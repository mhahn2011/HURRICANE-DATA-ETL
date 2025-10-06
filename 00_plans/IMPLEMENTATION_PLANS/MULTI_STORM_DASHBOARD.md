# Multi-Storm Dashboard Support - Implementation Plan

**Created:** 2025-10-06
**Status:** 📋 Not Started
**Priority:** High
**Effort:** Medium (4-6 hours)

---

## Context Summary

The Streamlit dashboard currently works with Hurricane Ida data. To enable full multi-storm exploration, we need to extract features for all 14 Gulf Coast hurricanes and ensure the dashboard dropdown automatically detects and displays them.

**Goal:** Enable users to select and explore any of the 14 Gulf Coast hurricanes (2005-2022) from the dashboard dropdown.

---

## Current State

### What Works ✅
- Dashboard auto-detects CSVs in `06_outputs/ml_ready/`
- Dropdown selector dynamically populates from available files
- Hurricane Ida (AL092021) fully functional

### What's Missing ❌
- Feature CSVs for remaining 13 storms
- No batch processing has been run
- Storm metadata validation

---

## Storm Inventory

**14 Gulf Coast Hurricanes (2005-2022):**

| Storm ID | Name | Year | Status |
|----------|------|------|--------|
| AL092021 | Ida | 2021 | ✅ Available |
| AL122005 | Katrina | 2005 | ❌ Missing |
| AL182005 | Rita | 2005 | ❌ Missing |
| AL042005 | Dennis | 2005 | ❌ Missing |
| AL072008 | Gustav | 2008 | ❌ Missing |
| AL092008 | Ike | 2008 | ❌ Missing |
| AL092017 | Harvey | 2017 | ❌ Missing |
| AL112017 | Irma | 2017 | ❌ Missing |
| AL142018 | Michael | 2018 | ❌ Missing |
| AL132020 | Laura | 2020 | ❌ Missing |
| AL262020 | Delta | 2020 | ❌ Missing |
| AL282020 | Zeta | 2020 | ❌ Missing |
| AL192020 | Sally | 2020 | ❌ Missing |
| AL092022 | Ian | 2022 | ❌ Missing |

---

## Implementation Steps

### Phase 1: Feature Extraction (Primary Task)

**Step 1.1: Verify Storm IDs**
- Confirm all 14 storm IDs exist in HURDAT2 dataset
- Validate storm names and years match
- Check for wind radii availability

```bash
# Quick verification script
python -c "
from pathlib import Path
import sys
sys.path.insert(0, '01_data_sources/hurdat2/src')
from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data

storms = parse_hurdat2_file('01_data_sources/hurdat2/input_data/hurdat2-atlantic.txt')
df = clean_hurdat2_data(storms)

storm_ids = ['AL092021', 'AL122005', 'AL182005', 'AL042005', 'AL072008',
             'AL092008', 'AL092017', 'AL112017', 'AL142018', 'AL132020',
             'AL262020', 'AL282020', 'AL192020', 'AL092022']

for sid in storm_ids:
    track = df[df['storm_id'] == sid]
    if not track.empty:
        name = track['storm_name'].iloc[0]
        year = track['date'].iloc[0].year
        print(f'✅ {sid}: {name} ({year})')
    else:
        print(f'❌ {sid}: NOT FOUND')
"
```

**Step 1.2: Run Batch Feature Extraction**
- Use existing `batch_extract_features.py` script
- Extract features for all 14 storms
- Output to `06_outputs/ml_ready/`

```bash
python 03_integration/scripts/batch_extract_features.py
```

**Expected Outputs:**
- `06_outputs/ml_ready/al122005_features.csv` (Katrina)
- `06_outputs/ml_ready/al182005_features.csv` (Rita)
- `06_outputs/ml_ready/al042005_features.csv` (Dennis)
- ... (11 more files)
- `06_outputs/ml_ready/storm_tract_features.csv` (unified)

**Step 1.3: Validate Outputs**
- Check each CSV has required columns
- Verify non-empty datasets
- Confirm storm metadata (name, year, ID)

```bash
# Validation script
for csv in 06_outputs/ml_ready/al*_features.csv; do
    echo "Checking $csv..."
    python -c "
import pandas as pd
df = pd.read_csv('$csv')
required = ['geoid', 'centroid_lat', 'centroid_lon', 'storm_id', 'storm_name', 'distance_to_track_km', 'max_wind_kt']
missing = [col for col in required if col not in df.columns]
if missing:
    print('  ❌ Missing columns:', missing)
else:
    print(f'  ✅ {len(df)} tracts, columns OK')
"
done
```

---

### Phase 2: Dashboard Enhancement (Optional Improvements)

**Step 2.1: Add Storm Summary Statistics**
- Create metadata file with storm characteristics
- Display in dashboard sidebar:
  - Max intensity (category)
  - Landfall location
  - Total affected tracts
  - Date range

**Step 2.2: Improve Storm Selector UX**
- Sort storms by year (most recent first)
- Add icons/badges for storm category
- Group by year in dropdown

**Step 2.3: Add Comparison Mode** (Future)
- Multi-select for 2+ storms
- Side-by-side map views
- Comparative statistics table

---

### Phase 3: Validation & Testing

**Step 3.1: Test Each Storm**
- Launch dashboard
- Select each storm from dropdown
- Verify map renders correctly
- Check statistics display properly

**Step 3.2: Performance Testing**
- Monitor load times for large storms (Katrina, Harvey)
- Ensure caching works across storm switches
- Validate memory usage

**Step 3.3: Edge Case Handling**
- Test storms with missing wind radii
- Verify storms with sparse census coverage
- Check extratropical transition handling

---

## File Organization

### Input Files Required
```
01_data_sources/
└── hurdat2/
    └── input_data/
        └── hurdat2-atlantic.txt  # Contains all storm data

01_data_sources/
└── census/
    └── data/
        └── tl_2019_*_tract.zip   # Census tract shapefiles
```

### Output Files Generated
```
06_outputs/
└── ml_ready/
    ├── al092021_features.csv     # Ida (exists)
    ├── al122005_features.csv     # Katrina (new)
    ├── al182005_features.csv     # Rita (new)
    ├── al042005_features.csv     # Dennis (new)
    ├── al072008_features.csv     # Gustav (new)
    ├── al092008_features.csv     # Ike (new)
    ├── al092017_features.csv     # Harvey (new)
    ├── al112017_features.csv     # Irma (new)
    ├── al142018_features.csv     # Michael (new)
    ├── al132020_features.csv     # Laura (new)
    ├── al262020_features.csv     # Delta (new)
    ├── al282020_features.csv     # Zeta (new)
    ├── al192020_features.csv     # Sally (new)
    ├── al092022_features.csv     # Ian (new)
    └── storm_tract_features.csv  # All storms combined
```

---

## Test-Driven Development (TDD)

### Test 1: Feature Extraction Completeness
```python
# 05_tests/test_multi_storm_extraction.py
def test_all_14_storms_have_features():
    """Verify all 14 Gulf Coast hurricanes have feature CSVs."""
    storm_ids = [
        'AL092021', 'AL122005', 'AL182005', 'AL042005',
        'AL072008', 'AL092008', 'AL092017', 'AL112017',
        'AL142018', 'AL132020', 'AL262020', 'AL282020',
        'AL192020', 'AL092022'
    ]

    for storm_id in storm_ids:
        csv_path = Path(f'06_outputs/ml_ready/{storm_id.lower()}_features.csv')
        assert csv_path.exists(), f"Missing features for {storm_id}"

        df = pd.read_csv(csv_path)
        assert len(df) > 0, f"Empty dataset for {storm_id}"
        assert 'storm_id' in df.columns
        assert df['storm_id'].iloc[0] == storm_id
```

### Test 2: Dashboard Storm Discovery
```python
# 05_tests/test_dashboard_storm_discovery.py
def test_dashboard_discovers_all_storms():
    """Verify dashboard can discover all available storms."""
    from streamlit_app import discover_storm_files

    options = discover_storm_files()
    storm_ids = [opt.storm_id for opt in options]

    assert len(storm_ids) >= 14, f"Only found {len(storm_ids)} storms"
    assert 'AL092021' in storm_ids  # Ida
    assert 'AL122005' in storm_ids  # Katrina
    # ... etc
```

### Test 3: Required Column Validation
```python
# 05_tests/test_feature_schema_validation.py
def test_all_csvs_have_required_columns():
    """Ensure all feature CSVs have required schema."""
    required_cols = [
        'geoid', 'centroid_lat', 'centroid_lon',
        'storm_id', 'storm_name', 'distance_to_track_km',
        'max_wind_kt', 'duration_64kt_hours'
    ]

    for csv_path in Path('06_outputs/ml_ready').glob('al*_features.csv'):
        df = pd.read_csv(csv_path)
        for col in required_cols:
            assert col in df.columns, f"{csv_path.name} missing {col}"
```

---

## Execution Workflow

### Quick Path (Simplest)
```bash
# 1. Run batch extraction
python 03_integration/scripts/batch_extract_features.py

# 2. Verify outputs
ls -lh 06_outputs/ml_ready/

# 3. Launch dashboard
streamlit run 03_integration/src/streamlit_app.py

# 4. Test all storms in dropdown
```

### Detailed Path (With Validation)
```bash
# 1. Verify storm IDs in HURDAT2
python -c "..." # (from Step 1.1)

# 2. Extract features one-by-one (for debugging)
for sid in AL122005 AL182005 AL042005 ...; do
    echo "Extracting $sid..."
    python 03_integration/src/feature_pipeline.py $sid
done

# 3. Run validation
bash validate_outputs.sh  # (from Step 1.3)

# 4. Run tests
pytest 05_tests/test_multi_storm_extraction.py -v

# 5. Launch dashboard
streamlit run 03_integration/src/streamlit_app.py
```

---

## Expected Outcomes

### Success Criteria
- ✅ All 14 storms appear in dashboard dropdown
- ✅ Each storm loads without errors
- ✅ Maps render correctly for all storms
- ✅ Statistics display accurate values
- ✅ CSV download works for each storm

### Deliverables
1. **Feature CSVs:** 14 individual storm files + 1 unified
2. **Test Suite:** 3 new tests validating multi-storm support
3. **Documentation:** Updated dashboard README with storm list
4. **Git Commit:** "feat: add multi-storm support to dashboard"

---

## Potential Issues & Solutions

### Issue 1: Large Storms (Katrina, Harvey)
**Problem:** May have 10,000+ tracts, slow loading
**Solution:**
- Implement pagination in data table
- Add distance filter in sidebar (default: <200km)
- Use deck.gl for more efficient rendering

### Issue 2: Missing Wind Radii (Pre-2004)
**Problem:** Some storms lack 64kt radii data
**Solution:**
- Skip envelope rendering if no radii
- Show track-only map
- Display warning message

### Issue 3: Inconsistent Column Names
**Problem:** Older CSVs may use different column names
**Solution:**
- Standardize schema in batch script
- Add column aliasing in dashboard
- Validate before saving

### Issue 4: Memory Usage
**Problem:** Loading all storms uses excessive RAM
**Solution:**
- Keep caching at per-storm level (already implemented)
- Clear cache when switching storms
- Use lazy loading for charts

---

## Dependencies

### Required Files
- ✅ `01_data_sources/hurdat2/input_data/hurdat2-atlantic.txt`
- ✅ `01_data_sources/census/data/tl_2019_*_tract.zip`
- ✅ `03_integration/scripts/batch_extract_features.py`
- ✅ `03_integration/src/feature_pipeline.py`

### Python Packages
- ✅ `streamlit >= 1.28.0`
- ✅ `pandas`
- ✅ `folium`
- ✅ `plotly`
- ✅ `shapely`
- ✅ `geopandas`

---

## Timeline Estimate

### Phase 1: Feature Extraction (2-3 hours)
- Storm ID verification: 30 min
- Batch extraction: 1-2 hours (compute time)
- Validation: 30 min

### Phase 2: Dashboard Enhancement (1-2 hours)
- Storm metadata: 30 min
- UX improvements: 30 min
- Testing: 30 min

### Phase 3: Validation & Testing (1 hour)
- Manual testing: 30 min
- Automated tests: 30 min

**Total Estimated Effort:** 4-6 hours

---

## Success Metrics

- **Coverage:** 14/14 storms available in dropdown (100%)
- **Performance:** <5 second load time per storm
- **Reliability:** All maps render without errors
- **Usability:** <3 clicks to switch between storms

---

## Related Documentation

- **Dashboard Status:** `03_integration/DASHBOARD_STATUS.md`
- **Feature Pipeline:** `03_integration/src/feature_pipeline.py`
- **Batch Script:** `03_integration/scripts/batch_extract_features.py`
- **Repository Structure:** `00_documentation/REPOSITORY_STRUCTURE.md`

---

## Next Steps

1. **Run:** `python 03_integration/scripts/batch_extract_features.py`
2. **Verify:** Check `06_outputs/ml_ready/` for 14 CSVs
3. **Test:** Launch dashboard and select each storm
4. **Commit:** Push all feature CSVs to GitHub
5. **Document:** Update dashboard README with storm list

---

**Ready to implement!** Start with Phase 1 batch extraction.
