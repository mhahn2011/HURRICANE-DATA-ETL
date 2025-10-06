# Complete Migration Plan: Legacy → Numbered Structure

**Date:** 2025-10-06
**Status:** Superseded by COMPLETE_REFACTORING_PLAN.md
**See:** [COMPLETE_REFACTORING_PLAN.md](./COMPLETE_REFACTORING_PLAN.md) for current execution plan
**Estimated Time:** 4-6 hours

> **Note:** This plan is kept for reference. Use COMPLETE_REFACTORING_PLAN.md for actual execution.

---

## Executive Summary

**Current State:** Repository has both old (`_legacy_data_sources/`) and new (`01_data_sources/`) structures coexisting, causing confusion.

**Target State:** Single numbered structure with all code migrated and legacy folders deleted.

**Key Finding:** New structure (01_, 02_, etc.) already has most files copied. Only need to:
1. Update imports to use new paths
2. Update output paths
3. Delete legacy folders
4. Verify tests pass

---

## Migration Map

### Phase 1: Import Path Updates

#### Files Needing Import Updates

**Count:** 2 main files (feature_pipeline.py has both old and new paths)

**File: `03_integration/src/feature_pipeline.py`**
```python
# CURRENT (lines 14-20):
sys.path.extend([
    str(REPO_ROOT / "hurdat2" / "src"),                           # DELETE
    str(REPO_ROOT / "census" / "src"),                            # DELETE
    str(REPO_ROOT / "hurdat2_census" / "src"),                    # DELETE
    str(REPO_ROOT / "_legacy_data_sources" / "hurdat2" / "src"),  # DELETE
    str(REPO_ROOT / "_legacy_data_sources" / "hurdat2_census" / "src"),  # DELETE
])

# NEW:
sys.path.extend([
    str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"),
    str(REPO_ROOT / "01_data_sources" / "census" / "src"),
    str(REPO_ROOT / "02_transformations" / "storm_tract_distance" / "src"),
    str(REPO_ROOT / "02_transformations" / "lead_time" / "src"),
])
```

**File: `02_transformations/duration/src/duration_calculator.py`**
```python
# CURRENT (line 17):
sys.path.append(str(REPO_ROOT / "hurdat2" / "src"))

# NEW:
sys.path.append(str(REPO_ROOT / "01_data_sources" / "hurdat2" / "src"))
```

**File: `02_transformations/storm_tract_distance/src/storm_tract_distance.py`**
```python
# Check and update sys.path.extend() to use new numbered paths
```

**File: `03_integration/src/streamlit_app.py`**
```python
# Check and update sys.path.extend() to use new numbered paths
```

---

### Phase 2: Output Path Updates

#### Default Output Paths

**Current scattered locations:**
```
integration/outputs/
hurdat2/outputs/
03_integration/outputs/
```

**New consolidated location:**
```
06_outputs/
├── ml_ready/          # Feature CSVs
├── visuals/           # HTML maps, plots
└── reports/           # Summary tables
```

#### Files to Update

**`03_integration/src/feature_pipeline.py` (line 143)**
```python
# CURRENT:
default_output = REPO_ROOT / "integration" / "outputs" / f"{storm_id}_features_complete.csv"

# NEW:
default_output = REPO_ROOT / "06_outputs" / "ml_ready" / f"{storm_id}_features_complete.csv"
```

**`03_integration/scripts/batch_extract_features.py`**
```python
# CURRENT (line 74):
output_path = REPO_ROOT / "integration" / "outputs" / "storm_tract_features.csv"

# NEW:
output_path = REPO_ROOT / "06_outputs" / "ml_ready" / "storm_tract_features.csv"

# CURRENT (line 57):
per_storm_path = REPO_ROOT / "integration" / "outputs" / f"{storm_id.lower()}_features_complete.csv"

# NEW:
per_storm_path = REPO_ROOT / "06_outputs" / "ml_ready" / f"{storm_id.lower()}_features_complete.csv"
```

**`01_data_sources/hurdat2/src/visualize_folium_qa.py`**
```python
# Update output paths from hurdat2/outputs/ to 06_outputs/visuals/
```

---

### Phase 3: Test Path Updates

**`05_tests/test_wind_coverage_envelope.py` (line 8)**
```python
# CURRENT:
baseline_path = REPO_ROOT / "03_integration/outputs/ida_features_complete_v3.csv"

# NEW:
baseline_path = REPO_ROOT / "06_outputs/ml_ready/ida_features_complete_v3.csv"
```

**`05_tests/test_sensitivity_analysis.py`**
```python
# CURRENT:
summary = pd.read_csv("01_data_sources/hurdat2/outputs/batch_processing_summary.csv")

# NEW:
summary = pd.read_csv("01_data_sources/hurdat2/processed/batch_processing_summary.csv")
```

---

### Phase 4: Documentation Consolidation

#### Files to Merge/Update

**Target:** Single `REPOSITORY_GUIDE.md` replacing:
- `REPOSITORY_STRUCTURE.md`
- `REPOSITORY_ORGANIZATION_ANALYSIS.md`
- `DOCUMENTATION_REFACTORING_RECOMMENDATIONS.md`

**New structure:**
```markdown
# Repository Guide

## Quick Start
## Structure Overview
## Design Philosophy
## Common Tasks
## Contributing Guidelines
## Migration History
```

---

## File-by-File Migration Checklist

### ✅ Already Migrated (Files exist in new structure)

**Data Sources:**
- ✅ `01_data_sources/hurdat2/src/parse_raw.py`
- ✅ `01_data_sources/hurdat2/src/profile_clean.py`
- ✅ `01_data_sources/hurdat2/src/visualize_folium_qa.py`
- ✅ `01_data_sources/census/src/tract_centroids.py`

**Transformations:**
- ✅ `02_transformations/wind_coverage_envelope/src/envelope_algorithm.py`
- ✅ `02_transformations/wind_interpolation/src/wind_interpolation.py`
- ✅ `02_transformations/duration/src/duration_calculator.py`
- ✅ `02_transformations/lead_time/src/lead_time_calculator.py`
- ✅ `02_transformations/storm_tract_distance/src/storm_tract_distance.py`

**Integration:**
- ✅ `03_integration/src/feature_pipeline.py`
- ✅ `03_integration/src/intensification_features.py`
- ✅ `03_integration/src/streamlit_app.py`
- ✅ `03_integration/scripts/batch_extract_features.py`

### ⚠️ Need Import Updates Only (Files exist, imports wrong)

- ⚠️ `03_integration/src/feature_pipeline.py` - Update sys.path
- ⚠️ `02_transformations/duration/src/duration_calculator.py` - Update sys.path
- ⚠️ `02_transformations/storm_tract_distance/src/storm_tract_distance.py` - Check sys.path
- ⚠️ `03_integration/src/streamlit_app.py` - Update sys.path

### ❌ Ready to Delete (After import updates)

- ❌ `_legacy_data_sources/hurdat2/`
- ❌ `_legacy_data_sources/census/`
- ❌ `_legacy_data_sources/hurdat2_census/`
- ❌ `_legacy_data_sources/fema/` (not used)

---

## Step-by-Step Execution Plan

### Step 1: Update Import Paths (30 min)

```bash
# Edit 4 files with corrected sys.path statements
vim 03_integration/src/feature_pipeline.py
vim 02_transformations/duration/src/duration_calculator.py
vim 02_transformations/storm_tract_distance/src/storm_tract_distance.py
vim 03_integration/src/streamlit_app.py
```

**Changes:**
- Replace `"hurdat2/src"` → `"01_data_sources/hurdat2/src"`
- Replace `"census/src"` → `"01_data_sources/census/src"`
- Replace `"hurdat2_census/src"` → `"02_transformations/storm_tract_distance/src"`
- Remove all `_legacy_data_sources` references

### Step 2: Update Output Paths (20 min)

```bash
# Edit output path constants
vim 03_integration/src/feature_pipeline.py
vim 03_integration/scripts/batch_extract_features.py
vim 01_data_sources/hurdat2/src/visualize_folium_qa.py
```

**Changes:**
- `integration/outputs/` → `06_outputs/ml_ready/`
- `hurdat2/outputs/` → `06_outputs/visuals/hurdat2/`

### Step 3: Create Output Directory Structure (5 min)

```bash
mkdir -p 06_outputs/{ml_ready,visuals,reports}
mkdir -p 06_outputs/visuals/{hurdat2,transformations,debug}
```

### Step 4: Update Test Paths (15 min)

```bash
vim 05_tests/test_wind_coverage_envelope.py
vim 05_tests/test_sensitivity_analysis.py
```

**Changes:**
- Update hardcoded paths to use 06_outputs/
- Update data source paths to 01_data_sources/

### Step 5: Run Tests (30 min)

```bash
# Verify all tests pass with new paths
pytest 05_tests/ -v

# If failures, check:
# - Import paths correct?
# - Output directories exist?
# - Test data in right location?
```

### Step 6: Test Feature Pipeline (30 min)

```bash
# Test single storm
python 03_integration/src/feature_pipeline.py AL092021

# Expected output:
# 06_outputs/ml_ready/al092021_features_complete.csv

# Verify file created and valid
ls -lh 06_outputs/ml_ready/
head -2 06_outputs/ml_ready/al092021_features_complete.csv
```

### Step 7: Test Batch Processing (1 hour)

```bash
# Run batch for all storms
python 03_integration/scripts/batch_extract_features.py

# Expected outputs:
# - 06_outputs/ml_ready/{storm_id}_features_complete.csv (14 files)
# - 06_outputs/ml_ready/storm_tract_features.csv (master)
```

### Step 8: Test Dashboard (15 min)

```bash
streamlit run 03_integration/src/streamlit_app.py

# Verify:
# - Storms load from 06_outputs/ml_ready/
# - All 14 storms appear
# - Maps and charts work
```

### Step 9: Move Existing Outputs (10 min)

```bash
# Move existing CSVs to new location
mv integration/outputs/*_features_complete.csv 06_outputs/ml_ready/ 2>/dev/null
mv integration/outputs/storm_tract_features.csv 06_outputs/ml_ready/ 2>/dev/null
mv hurdat2/outputs/qa_maps/*.html 06_outputs/visuals/hurdat2/ 2>/dev/null
```

### Step 10: Delete Legacy Folders (5 min)

```bash
# ONLY after all tests pass and outputs verified
rm -rf _legacy_data_sources/

# Verify no broken imports
grep -r "_legacy_data_sources" . --include="*.py" --include="*.md"
# Should return 0 results
```

### Step 11: Clean Up Old Structure (5 min)

```bash
# Remove old non-numbered folders if they exist
rm -rf hurdat2/ census/ integration/ hurdat2_census/ 2>/dev/null
```

---

## Validation Checklist

### ✅ Code Works
- [ ] All tests pass (pytest 05_tests/)
- [ ] Feature pipeline runs (single storm)
- [ ] Batch processing completes (all 14 storms)
- [ ] Dashboard launches and loads data
- [ ] No import errors in any module

### ✅ Outputs Correct
- [ ] Files appear in 06_outputs/ml_ready/
- [ ] HTML visuals in 06_outputs/visuals/
- [ ] CSV schemas match expected format
- [ ] File counts correct (14 storm CSVs + 1 master)

### ✅ No Legacy References
- [ ] No `_legacy_data_sources` in code
- [ ] No `hurdat2/src` imports (should be 01_data_sources/hurdat2/src)
- [ ] No `integration/outputs` paths (should be 06_outputs/)
- [ ] No old folder names in documentation

---

## Documentation Updates

### Consolidate into Single Guide

**Create: `00_documentation/REPOSITORY_GUIDE.md`**

Consolidates:
- REPOSITORY_STRUCTURE.md (keep structure section)
- REPOSITORY_ORGANIZATION_ANALYSIS.md (keep design philosophy)
- DOCUMENTATION_REFACTORING_RECOMMENDATIONS.md (archive)

**Structure:**
```markdown
# Repository Guide

## Overview
- Project purpose
- Quick start commands

## Structure
- Folder organization (numbered system)
- Design philosophy
- Data flow diagram

## Common Tasks
- Extract features for one storm
- Run batch processing
- Generate visualizations
- Launch dashboard

## Contributing
- Where to add new features
- Testing guidelines
- Code style

## Architecture
- Design principles explained
- Why numbered folders
- Comparison to ML standards

## Migration History
- Pre-2025-10-05: Flat structure
- 2025-10-05: Numbered structure introduced
- 2025-10-06: Migration completed
```

**Archive old docs:**
```bash
mkdir -p 00_documentation/archive/pre-migration-2025-10-06/
mv 00_documentation/REPOSITORY_ORGANIZATION_ANALYSIS.md 00_documentation/archive/pre-migration-2025-10-06/
mv 00_documentation/DOCUMENTATION_REFACTORING_RECOMMENDATIONS.md 00_documentation/archive/pre-migration-2025-10-06/
mv 00_documentation/DESIGN_PHILOSOPHY_ASSESSMENT.md 00_documentation/archive/pre-migration-2025-10-06/
```

---

## Rollback Plan

If critical issues arise after migration:

```bash
# 1. Restore legacy folders
cd /path/to/backup
cp -r _legacy_data_sources/ /path/to/repo/

# 2. Revert code changes
git checkout HEAD~1 03_integration/src/feature_pipeline.py
git checkout HEAD~1 02_transformations/duration/src/duration_calculator.py

# 3. Verify old system works
pytest 05_tests/
python integration/src/feature_pipeline.py AL092021
```

**Prevention:** Commit changes incrementally, test after each phase.

---

## Timeline

| Phase | Task | Time | Can Parallelize? |
|-------|------|------|------------------|
| 1 | Update imports | 30 min | No |
| 2 | Update output paths | 20 min | No |
| 3 | Create directories | 5 min | Yes |
| 4 | Update test paths | 15 min | Yes |
| 5 | Run tests | 30 min | No |
| 6 | Test pipeline | 30 min | No |
| 7 | Batch processing | 60 min | No |
| 8 | Test dashboard | 15 min | No |
| 9 | Move outputs | 10 min | Yes |
| 10 | Delete legacy | 5 min | No |
| 11 | Clean up | 5 min | No |
| 12 | Update docs | 60 min | Yes (during batch) |

**Total Sequential Time:** ~4 hours
**With Parallelization:** ~3 hours

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Import errors | Medium | High | Test imports incrementally |
| Missing files | Low | High | Verify files exist before deleting legacy |
| Tests fail | Medium | Medium | Fix issues before proceeding |
| Output path errors | Low | Medium | Create directories first |
| Dashboard breaks | Low | Medium | Test with Ida before batch processing |

**Overall Risk:** LOW (files already copied, just need path updates)

---

## Success Criteria

✅ **Migration Complete When:**

1. All code uses numbered folder paths (01_, 02_, 03_, 06_)
2. All tests pass (48/51 or better)
3. Feature pipeline generates correct CSVs in 06_outputs/ml_ready/
4. Dashboard loads all 14 storms from new location
5. No references to `_legacy_data_sources/` in any file
6. Documentation accurately describes new structure
7. Old folders deleted with no impact

---

## Post-Migration Tasks

### Immediate (Same Day)
- [ ] Commit migration changes
- [ ] Update README.md with new structure
- [ ] Tag release: `v2.0-numbered-structure`

### Near-term (Within Week)
- [ ] Update all documentation references
- [ ] Create migration announcement
- [ ] Add to CHANGELOG.md

### Long-term (Within Month)
- [ ] Create `setup.py` for installable package
- [ ] Replace sys.path manipulation with proper imports
- [ ] Add environment-based path configuration

---

## Quick Reference

**Key File Changes:**
```
03_integration/src/feature_pipeline.py          → Update sys.path, output paths
02_transformations/duration/src/duration_calculator.py → Update sys.path
03_integration/scripts/batch_extract_features.py → Update output paths
05_tests/test_*.py                              → Update test data paths
```

**Key Directory Changes:**
```
integration/outputs/ → 06_outputs/ml_ready/
hurdat2/outputs/     → 06_outputs/visuals/hurdat2/
```

**Verification Commands:**
```bash
pytest 05_tests/ -v
python 03_integration/src/feature_pipeline.py AL092021
streamlit run 03_integration/src/streamlit_app.py
grep -r "_legacy_data_sources\|hurdat2/src" . --include="*.py"
```

---

## Contact

**Questions about migration?** See:
- This plan: `00_plans/MIGRATION_PLAN.md`
- Design rationale: `00_documentation/REPOSITORY_GUIDE.md`
- Original structure: `00_documentation/archive/pre-migration-2025-10-06/`
