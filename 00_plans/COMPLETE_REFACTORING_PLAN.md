# Complete Refactoring Plan
**Created:** 2025-10-06
**Status:** Ready for Execution
**Priority:** Critical
**Estimated Time:** 6-8 hours

---

## Executive Summary

### Current State
The repository migration to numbered folders (01_, 02_, etc.) is **~70% complete**:
- ✅ Files copied to new numbered structure
- ✅ Some import paths updated (feature_pipeline.py, duration_calculator.py)
- ⚠️ Legacy folder still exists (`_legacy_data_sources/`)
- ⚠️ Many files still reference old paths (`integration/outputs`, `hurdat2/outputs`)
- ⚠️ Some sys.path statements not updated

### Target State
- ✅ All imports use numbered paths (01_data_sources, 02_transformations, etc.)
- ✅ All outputs go to `06_outputs/ml_ready/` or `06_outputs/visuals/`
- ✅ Legacy folders deleted
- ✅ Tests pass
- ✅ Documentation matches reality

---

## Phase 1: Import Path Updates (1.5 hours)

### Files Requiring sys.path Updates

#### 1.1 `03_integration/src/streamlit_app.py`
**Current (line 19):**
```python
sys.path.extend(
    [str(REPO_ROOT / folder) for folder in [
        "_legacy_data_sources/hurdat2/src",  # ❌ DELETE
        "_legacy_data_sources/census/src",   # ❌ DELETE
        # ... other paths
    ]]
)
```

**Target:**
```python
sys.path.extend([
    str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
    str(REPO_ROOT / "01_data_sources" / "census" / "src"),
    str(REPO_ROOT / "02_transformations" / "storm_tract_distance" / "src"),
    str(REPO_ROOT / "02_transformations" / "lead_time" / "src"),
    str(REPO_ROOT / "02_transformations" / "wind_interpolation" / "src"),
    str(REPO_ROOT / "02_transformations" / "duration" / "src"),
])
```

#### 1.2 `02_transformations/storm_tract_distance/src/storm_tract_distance.py`
**Current (line 27):**
```python
sys.path.extend(
    [str(REPO_ROOT / folder) for folder in [
        "_legacy_data_sources/hurdat2/src",  # ❌ CHECK/UPDATE
        # ...
    ]]
)
```

**Target:**
```python
sys.path.extend([
    str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
    str(REPO_ROOT / "01_data_sources" / "census" / "src"),
    str(REPO_ROOT / "02_transformations" / "wind_coverage_envelope" / "src"),
])
```

#### 1.3 `03_integration/src/prepare_ida_visualization_data.py`
**Current (line 8):**
Check and update sys.path.extend()

**Target:** Use numbered paths

#### 1.4 `03_integration/src/debug_distance_calculation.py`
**Current (line 10):**
Check and update sys.path.extend()

**Target:** Use numbered paths

#### 1.5 `03_integration/src/feature_pipeline_backup.py`
**Current (line 11):**
Check if this file is needed. If yes, update. If no, delete.

---

## Phase 2: Output Path Updates (2 hours)

### 2.1 Create Output Directory Structure

```bash
mkdir -p 06_outputs/ml_ready
mkdir -p 06_outputs/visuals/hurdat2
mkdir -p 06_outputs/visuals/transformations
mkdir -p 06_outputs/visuals/debug
mkdir -p 06_outputs/reports
```

### 2.2 Update Output Paths in Code

#### File: `03_integration/scripts/batch_extract_features.py`

**Search for:** `integration/outputs`

**Replace with:** `06_outputs/ml_ready`

**Specific changes:**
- Line ~57: `per_storm_path`
- Line ~74: `output_path` for master file

#### File: `03_integration/src/streamlit_app.py`

**Current (line 297):**
```python
st.error("No feature CSV files found under integration/outputs. Run the ETL pipeline first.")
```

**Target:**
```python
st.error("No feature CSV files found under 06_outputs/ml_ready/. Run the ETL pipeline first.")
```

**Also update:**
- Line ~43: Output directory path constant
- Any file loading logic that references old paths

#### File: `02_transformations/storm_tract_distance/src/storm_tract_distance.py`

**Current (line 11 in docstring):**
```python
--output integration/outputs/ida_tract_distances.csv
```

**Target:**
```python
--output 06_outputs/ml_ready/ida_tract_distances.csv
```

#### File: `01_data_sources/hurdat2/src/visualize_folium_qa.py`

**Search for:** References to `hurdat2/outputs/qa_maps/`

**Replace with:** `06_outputs/visuals/hurdat2/`

### 2.3 Update Test File Paths

#### File: `05_tests/test_wind_coverage_envelope.py`

**Current (line 146):**
```python
baseline_path = REPO_ROOT / "03_integration/outputs/ida_features_complete_v3.csv"
```

**Target:**
```python
baseline_path = REPO_ROOT / "06_outputs/ml_ready/ida_features_complete_v3.csv"
```

#### File: `05_tests/test_sensitivity_analysis.py`

**Current (line 16):**
```python
summary = pd.read_csv("01_data_sources/hurdat2/outputs/batch_processing_summary.csv")
```

**Target:**
Check if this file exists. If not, update to correct location.
If it's a processed file, move to `01_data_sources/hurdat2/processed/`

---

## Phase 3: Documentation Updates (1.5 hours)

### 3.1 Files Requiring Path Updates in Documentation

**Update all references in:**

1. `00_documentation/README.md`
   - Line 133: `--output 03_integration/outputs/ida_features.csv`
   - Change to: `--output 06_outputs/ml_ready/ida_features.csv`

2. `00_documentation/VISUALIZATION_GUIDE.md`
   - Multiple references to `integration/outputs/` and `hurdat2/outputs/`
   - Update all to use `06_outputs/` structure

3. `00_documentation/simple_hurdat_setup.md`
   - Line 57: `mkdir -p integration/outputs/ml_ready_data`
   - Line 165-166: Path references
   - Line 246: CSV path

4. `.claude.md`
   - Line 264: `hurdat2/outputs/qa_maps/`
   - Line 266: `integration/outputs/results/`

### 3.2 Update Implementation Plans

**Files to update (documentation only, not executable):**
- `00_plans/IMPLEMENTATION_PLANS/COMPLETED/*.md` - Update path examples
- `00_plans/00_high_level_immediate_plans/IMMEDIATE_TODO.md` - Update paths
- `00_plans/AGENTS_GUIDE.md` - Update path examples

**Note:** These are completed plans - only update for accuracy of historical record

---

## Phase 4: Move Existing Output Files (30 min)

### 4.1 Move Feature CSVs

```bash
# Move ML-ready features
find . -name "*_features*.csv" -path "*/integration/outputs/*" -exec mv {} 06_outputs/ml_ready/ \; 2>/dev/null || true
find . -name "*_features*.csv" -path "*/03_integration/outputs/*" -exec mv {} 06_outputs/ml_ready/ \; 2>/dev/null || true

# Move existing files from 06_outputs/ml_ready to ensure no duplicates
# (files are already there from your git status)
```

### 4.2 Move Visualization Files

```bash
# Move HURDAT2 visualizations
find . -name "*.html" -path "*/hurdat2/outputs/qa_maps/*" -exec mv {} 06_outputs/visuals/hurdat2/ \; 2>/dev/null || true

# Move transformation visualizations
find . -name "qaqc_*.html" -exec mv {} 06_outputs/visuals/transformations/ \; 2>/dev/null || true
```

---

## Phase 5: Test & Verify (1.5 hours)

### 5.1 Run Unit Tests

```bash
# Run all tests
python -m pytest 05_tests/ -v

# Expected: Most tests pass (aim for 48+/51)
```

**If failures occur:**
- Check import errors first
- Verify file paths
- Check test data existence

### 5.2 Test Feature Pipeline

```bash
# Test single storm (Ida)
python 03_integration/src/feature_pipeline.py --storm-id AL092021

# Verify output
ls -lh 06_outputs/ml_ready/al092021_features_complete.csv
head -3 06_outputs/ml_ready/al092021_features_complete.csv
```

### 5.3 Test Batch Processing

```bash
# Process all 14 storms
python 03_integration/scripts/batch_extract_features.py

# Verify outputs
ls 06_outputs/ml_ready/*.csv | wc -l  # Should be 15 (14 storms + 1 master)
```

### 5.4 Test Dashboard

```bash
# Launch dashboard
streamlit run 03_integration/src/streamlit_app.py

# Manual checks:
# - All 14 storms appear in dropdown
# - Maps render correctly
# - Charts display data
```

---

## Phase 6: Delete Legacy Code (15 min)

### 6.1 Verify No References

```bash
# Check for legacy references in active code
grep -r "_legacy_data_sources" --include="*.py" \
  01_data_sources/ 02_transformations/ 03_integration/ 04_src_shared/ 05_tests/

# Should return 0 results

# Check for old paths in active code
grep -r "integration/outputs\|hurdat2/outputs" --include="*.py" \
  01_data_sources/ 02_transformations/ 03_integration/

# Should return only comments/docstrings (if any)
```

### 6.2 Delete Legacy Folders

```bash
# ONLY after all tests pass
rm -rf _legacy_data_sources/

# Verify removal
ls -la | grep legacy  # Should be empty
```

### 6.3 Clean Old Output Directories

```bash
# Remove old output directories (after files moved)
rm -rf integration/outputs/ 2>/dev/null || true
rm -rf hurdat2/outputs/ 2>/dev/null || true
rm -rf 03_integration/outputs/ 2>/dev/null || true

# Keep only: 06_outputs/
```

---

## Phase 7: Final Verification (30 min)

### 7.1 Verify Complete Structure

```bash
# Check structure
tree -L 2 -d

# Should show:
# 00_plans/
# 00_documentation/
# 01_data_sources/
# 02_transformations/
# 03_integration/
# 04_src_shared/
# 05_tests/
# 06_outputs/
#   ├── ml_ready/
#   ├── visuals/
#   └── reports/
```

### 7.2 Run Full Test Suite

```bash
# All tests
python -m pytest 05_tests/ -v --tb=short

# Check coverage
python -m pytest 05_tests/ --cov=01_data_sources --cov=02_transformations --cov=03_integration
```

### 7.3 Verify Outputs Exist

```bash
# Check ML outputs
ls -lh 06_outputs/ml_ready/

# Check visualizations
ls 06_outputs/visuals/hurdat2/*.html
ls 06_outputs/visuals/transformations/*.html
```

---

## Execution Checklist

### Phase 1: Import Paths ⏱️ 1.5 hours
- [ ] Update `03_integration/src/streamlit_app.py` sys.path
- [ ] Update `02_transformations/storm_tract_distance/src/storm_tract_distance.py` sys.path
- [ ] Update `03_integration/src/prepare_ida_visualization_data.py` sys.path
- [ ] Update `03_integration/src/debug_distance_calculation.py` sys.path
- [ ] Delete or update `03_integration/src/feature_pipeline_backup.py`
- [ ] Verify no more `_legacy_data_sources` in sys.path statements

### Phase 2: Output Paths ⏱️ 2 hours
- [ ] Create `06_outputs/` directory structure
- [ ] Update `03_integration/scripts/batch_extract_features.py` output paths
- [ ] Update `03_integration/src/streamlit_app.py` output paths
- [ ] Update `02_transformations/storm_tract_distance/src/storm_tract_distance.py` docstring
- [ ] Update `01_data_sources/hurdat2/src/visualize_folium_qa.py` output paths
- [ ] Update `05_tests/test_wind_coverage_envelope.py` baseline path
- [ ] Update `05_tests/test_sensitivity_analysis.py` input path

### Phase 3: Documentation ⏱️ 1.5 hours
- [ ] Update `00_documentation/README.md`
- [ ] Update `00_documentation/VISUALIZATION_GUIDE.md`
- [ ] Update `00_documentation/simple_hurdat_setup.md`
- [ ] Update `.claude.md`
- [ ] Update `00_documentation/ML_TOOLS_OVERVIEW.md` path examples
- [ ] Update completed implementation plans (for historical accuracy)

### Phase 4: Move Files ⏱️ 30 min
- [ ] Move feature CSVs to `06_outputs/ml_ready/`
- [ ] Move HTML visualizations to `06_outputs/visuals/`
- [ ] Verify no files left in old locations

### Phase 5: Test & Verify ⏱️ 1.5 hours
- [ ] Run pytest suite - aim for 48+/51 passing
- [ ] Test feature_pipeline.py with AL092021
- [ ] Test batch_extract_features.py (all 14 storms)
- [ ] Test streamlit dashboard
- [ ] Fix any import/path errors found

### Phase 6: Delete Legacy ⏱️ 15 min
- [ ] Verify no `_legacy_data_sources` references in code
- [ ] Verify no `integration/outputs` or `hurdat2/outputs` in active code
- [ ] Delete `_legacy_data_sources/` folder
- [ ] Delete old output directories (`integration/outputs/`, etc.)

### Phase 7: Final Verification ⏱️ 30 min
- [ ] Verify directory structure correct
- [ ] Run full test suite
- [ ] Verify all outputs exist in `06_outputs/`
- [ ] Check git status - commit changes
- [ ] Update REPOSITORY_STRUCTURE.md if needed

---

## Quick Command Reference

### Search for Legacy References
```bash
# Find old sys.path patterns
grep -r "sys\.path\." --include="*.py" 02_transformations/ 03_integration/ | grep -v "01_data_sources"

# Find old output paths
grep -r "integration/outputs\|hurdat2/outputs\|census/outputs" --include="*.py" . | grep -v "00_plans\|00_documentation"

# Find legacy folder references
grep -r "_legacy_data_sources" --include="*.py" 01_data_sources/ 02_transformations/ 03_integration/ 04_src_shared/ 05_tests/
```

### Verify Import Paths
```bash
# Check all sys.path statements are correct
grep -A5 "sys.path" --include="*.py" 02_transformations/ 03_integration/
```

### Test Commands
```bash
# Quick test
python -m pytest 05_tests/test_arc_polygons.py -v

# Full test
python -m pytest 05_tests/ -v

# Run pipeline
python 03_integration/src/feature_pipeline.py --storm-id AL092021

# Run batch
python 03_integration/scripts/batch_extract_features.py
```

---

## Rollback Plan

If critical failures occur:

```bash
# 1. Restore from git
git checkout .
git clean -fd

# 2. Restore legacy folder if deleted
# (Restore from backup or previous commit)

# 3. Verify old system works
pytest 05_tests/
```

**Prevention:** Commit after each phase completes successfully.

---

## Success Criteria

✅ **Refactoring Complete When:**

1. **Code Quality**
   - All imports use numbered paths (01_, 02_, 03_)
   - No `_legacy_data_sources` references in any .py file
   - All sys.path statements use numbered structure

2. **Output Organization**
   - All ML features in `06_outputs/ml_ready/`
   - All visualizations in `06_outputs/visuals/`
   - Old output folders deleted

3. **Tests**
   - 48+ tests passing (out of 51)
   - Feature pipeline runs successfully
   - Dashboard loads all storms

4. **Documentation**
   - All docs reference correct paths
   - REPOSITORY_STRUCTURE.md matches reality
   - No misleading path examples

5. **Clean Structure**
   - Only numbered folders exist (00-06)
   - Legacy folders deleted
   - Git status clean or only expected changes

---

## Post-Refactoring Tasks

### Immediate (same session)
- [ ] Commit all changes
- [ ] Create git tag: `v2.0-refactoring-complete`
- [ ] Update CHANGELOG.md

### Near-term (within 1 week)
- [ ] Consider replacing sys.path with proper package structure
- [ ] Add __init__.py files for cleaner imports
- [ ] Create setup.py for installable package

### Long-term (within 1 month)
- [ ] Evaluate moving to src/ layout
- [ ] Consider poetry/conda for dependency management
- [ ] Set up CI/CD to prevent path regressions

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Import errors | Medium | High | Test incrementally, fix immediately |
| Missing test data | Low | Medium | Verify file existence before deletion |
| Dashboard breaks | Medium | Medium | Test with single storm first |
| Lost output files | Low | High | Move, don't delete; verify before cleanup |
| Test failures | High | Medium | Expected; fix one by one |

**Overall Risk:** MEDIUM (migration halfway done, need to complete carefully)

---

## Estimated Timeline

| Phase | Duration | Can Start After |
|-------|----------|----------------|
| 1. Import paths | 1.5 hr | - |
| 2. Output paths | 2.0 hr | Phase 1 |
| 3. Documentation | 1.5 hr | Phase 2 (can parallelize) |
| 4. Move files | 0.5 hr | Phase 2 |
| 5. Test & verify | 1.5 hr | Phase 4 |
| 6. Delete legacy | 0.25 hr | Phase 5 |
| 7. Final verify | 0.5 hr | Phase 6 |

**Total Sequential:** ~8 hours
**With Parallelization:** ~6.5 hours
**Buffer for issues:** +1.5 hours
**Realistic Total:** 6-8 hours

---

## Notes

- This plan completes the migration started in REFACTORING_IMPLEMENTATION_PLAN.md
- The numbered structure (01_, 02_, etc.) is already in place - just need to update references
- Most files already exist in correct locations - this is primarily path updates
- Test early and often - commit after each phase
- Keep git history clean with meaningful commit messages per phase

---

## Contact

**Questions?** See:
- Original plan: `00_plans/REFACTORING_IMPLEMENTATION_PLAN.md`
- Migration plan: `00_plans/MIGRATION_PLAN.md`
- This plan: `00_plans/COMPLETE_REFACTORING_PLAN.md`
