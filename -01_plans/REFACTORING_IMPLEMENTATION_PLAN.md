# Refactoring Implementation Plan - Fix Broken Imports

**Date Created:** 2025-10-05
**Status:** In Progress
**Priority:** Critical
**Estimated Time:** 2-3 hours

---

## Current State Analysis

### What Changed

The repository was reorganized with numbered prefixes:

| Old Path | New Path |
|----------|----------|
| `hurdat2/` | `01_data_sources/hurdat2/` |
| `census/` | `01_data_sources/census/` |
| `hurdat2_census/` | `_legacy_data_sources/hurdat2_census/` |
| `integration/` | `03_integration/` |
| `shared/` | `04_src_shared/` |
| `tests/` | `05_tests/` |
| `transformations/` | `02_transformations/` |
| `IMPLEMENTATION_PLANS/` | `-01_plans/` |
| `docs/` | `00_documentation/` |

### What Broke

**Test failures:** 11 errors out of 13 test files
**Root cause:** Import paths pointing to old folder structure

---

## Import Path Mapping

### Old → New Module Paths

#### Data Sources
```python
# OLD
from hurdat2.src.parse_raw import parse_hurdat2_file
from hurdat2.src.profile_clean import clean_hurdat2_data
from census.src.tract_centroids import load_tract_centroids

# NEW
from 01_data_sources.hurdat2.src.parse_raw import parse_hurdat2_file
from 01_data_sources.hurdat2.src.profile_clean import clean_hurdat2_data
from 01_data_sources.census.src.tract_centroids import load_tract_centroids
```

#### Transformations
```python
# OLD (various legacy paths)
from envelope_algorithm import create_storm_envelope
from duration_calculator import create_instantaneous_wind_polygon
from lead_time_calculator import calculate_lead_times
from integration.src.storm_tract_distance import calculate_storm_tract_features
from integration.src.wind_interpolation import calculate_max_wind_experienced

# NEW
from 02_transformations.wind_coverage_envelope.src.envelope_algorithm import create_storm_envelope
from 02_transformations.duration.src.duration_calculator import create_instantaneous_wind_polygon
from 02_transformations.lead_time.src.lead_time_calculator import calculate_lead_times
from 02_transformations.storm_tract_distance.src.storm_tract_distance import calculate_storm_tract_features
from 02_transformations.wind_interpolation.src.wind_interpolation import calculate_max_wind_experienced
```

#### Integration
```python
# OLD
from integration.src.feature_pipeline import run_pipeline
from integration.src.intensification_features import calculate_intensification_features

# NEW
from 03_integration.src.feature_pipeline import run_pipeline
from 03_integration.src.intensification_features import calculate_intensification_features
```

#### Shared Utilities
```python
# OLD
from shared.geometry_utils import haversine_distance

# NEW
from 04_src_shared.geometry_utils import haversine_distance
```

---

## Broken Files Inventory

### Test Files (05_tests/)
1. ✅ `test_arc_polygons.py` - Imports: duration_calculator, envelope_algorithm
2. ✅ `test_duration_calculator.py` - Imports: integration.src.duration_calculator
3. ✅ `test_envelope_validity.py` - Imports: envelope_algorithm, parse_raw, profile_clean
4. ✅ `test_intensification_features.py` - Imports: integration.src.intensification_features
5. ✅ `test_lead_time_calculator.py` - Imports: lead_time_calculator
6. ✅ `test_storm_tract_distance.py` - Imports: integration.src.storm_tract_distance, integration.src.wind_interpolation
7. ✅ `test_visualize_folium_qa.py` - Imports: hurdat2.src.visualize_folium_qa
8. ✅ `test_wind_coverage_envelope.py` - Imports: TBD (need to check)
9. ✅ `test_wind_interpolation.py` - Imports: integration.src.wind_interpolation
10. ✅ `test_sensitivity_analysis.py` - Imports: TBD (need to check)

### Source Files (to be checked)
- All files in `02_transformations/*/src/` - Check for internal cross-imports
- All files in `03_integration/src/` - Check for imports from transformations
- All files in `03_integration/scripts/` - Check for imports

---

## Implementation Strategy

### Phase 1: Fix Test Files (Work Backwards from Tests)

**Rationale:** Tests tell us what's broken. Fix tests first, then fix source files as needed.

#### Step 1.1: Update test_arc_polygons.py

**File:** `05_tests/test_arc_polygons.py`

```python
# BEFORE (lines 9-14)
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.extend([
    str(REPO_ROOT / "hurdat2" / "src"),
    str(REPO_ROOT / "hurdat2_census" / "src"),
])

from duration_calculator import create_instantaneous_wind_polygon
from envelope_algorithm import calculate_destination_point

# AFTER
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from 02_transformations.duration.src.duration_calculator import create_instantaneous_wind_polygon
from 02_transformations.wind_coverage_envelope.src.envelope_algorithm import calculate_destination_point
```

#### Step 1.2: Update test_duration_calculator.py

**File:** `05_tests/test_duration_calculator.py`

```python
# BEFORE
from integration.src.duration_calculator import (
    create_instantaneous_wind_polygon,
    calculate_tract_duration,
)

# AFTER
from 02_transformations.duration.src.duration_calculator import (
    create_instantaneous_wind_polygon,
    calculate_tract_duration,
)
```

#### Step 1.3: Update test_envelope_validity.py

**File:** `05_tests/test_envelope_validity.py`

```python
# BEFORE
sys.path.extend([
    str(REPO_ROOT / "hurdat2" / "src"),
])

from envelope_algorithm import create_storm_envelope, get_wind_extent_points
from parse_raw import parse_hurdat2_file
from profile_clean import clean_hurdat2_data

# AFTER
sys.path.insert(0, str(REPO_ROOT))

from 02_transformations.wind_coverage_envelope.src.envelope_algorithm import create_storm_envelope, get_wind_extent_points
from 01_data_sources.hurdat2.src.parse_raw import parse_hurdat2_file
from 01_data_sources.hurdat2.src.profile_clean import clean_hurdat2_data
```

#### Step 1.4: Update test_intensification_features.py

**File:** `05_tests/test_intensification_features.py`

```python
# BEFORE
from integration.src.intensification_features import calculate_intensification_features

# AFTER
from 03_integration.src.intensification_features import calculate_intensification_features
```

#### Step 1.5: Update test_lead_time_calculator.py

**File:** `05_tests/test_lead_time_calculator.py`

```python
# BEFORE
sys.path.extend([
    str(REPO_ROOT / "hurdat2_census" / "src"),
])

from lead_time_calculator import (
    calculate_lead_times,
    detect_category_threshold_crossing,
)

# AFTER
sys.path.insert(0, str(REPO_ROOT))

from 02_transformations.lead_time.src.lead_time_calculator import (
    calculate_lead_times,
    detect_category_threshold_crossing,
)
```

#### Step 1.6: Update test_storm_tract_distance.py

**File:** `05_tests/test_storm_tract_distance.py`

```python
# BEFORE
from integration.src.storm_tract_distance import (
    create_storm_envelope,
    calculate_distance_to_track,
    classify_wind_exposure,
)
from integration.src.wind_interpolation import calculate_max_wind_experienced

# AFTER
from 02_transformations.storm_tract_distance.src.storm_tract_distance import (
    create_storm_envelope,
    calculate_distance_to_track,
    classify_wind_exposure,
)
from 02_transformations.wind_interpolation.src.wind_interpolation import calculate_max_wind_experienced
```

#### Step 1.7: Update test_visualize_folium_qa.py

**File:** `05_tests/test_visualize_folium_qa.py`

```python
# BEFORE
from hurdat2.src.visualize_folium_qa import (
    create_wind_radii_map,
    add_storm_track,
)

# AFTER
from 01_data_sources.hurdat2.src.visualize_folium_qa import (
    create_wind_radii_map,
    add_storm_track,
)
```

#### Step 1.8: Update test_wind_interpolation.py

**File:** `05_tests/test_wind_interpolation.py`

```python
# BEFORE
from integration.src.wind_interpolation import calculate_max_wind_experienced

# AFTER
from 02_transformations.wind_interpolation.src.wind_interpolation import calculate_max_wind_experienced
```

#### Step 1.9: Check remaining test files

**Files to check:**
- `test_wind_coverage_envelope.py`
- `test_sensitivity_analysis.py`

**Action:** Read these files and update imports similarly

---

### Phase 2: Fix Source File Imports

After fixing test imports, run tests again. Any remaining failures indicate source files have broken internal imports.

#### Step 2.1: Check transformation cross-imports

**Files to check:**
```bash
grep -r "^from " 02_transformations/*/src/*.py | grep -v "from shapely\|from numpy\|from pandas"
```

**Common patterns to fix:**
```python
# If duration_calculator.py imports envelope_algorithm
# BEFORE
from envelope_algorithm import calculate_destination_point

# AFTER
from 02_transformations.wind_coverage_envelope.src.envelope_algorithm import calculate_destination_point
```

#### Step 2.2: Check integration imports

**Files to check:**
```bash
grep -r "^from " 03_integration/src/*.py | grep -v "from shapely\|from numpy\|from pandas"
```

**Expected imports to fix:**
- Imports from transformations
- Imports from data sources
- Imports from shared utilities

#### Step 2.3: Check hardcoded file paths

**Files to check:**
```bash
grep -r "hurdat2/outputs\|census/outputs\|integration/outputs" 02_transformations 03_integration
```

**Update patterns:**
```python
# BEFORE
INPUT_PATH = "hurdat2/outputs/cleaned_data/hurdat2_cleaned.csv"

# AFTER
INPUT_PATH = "01_data_sources/hurdat2/processed/hurdat2_cleaned.csv"
```

---

### Phase 3: Add __init__.py Files

Ensure all directories are proper Python packages:

```bash
# Create __init__.py in all src directories
touch 01_data_sources/hurdat2/src/__init__.py
touch 01_data_sources/census/src/__init__.py
touch 02_transformations/wind_coverage_envelope/src/__init__.py
touch 02_transformations/duration/src/__init__.py
touch 02_transformations/lead_time/src/__init__.py
touch 02_transformations/storm_tract_distance/src/__init__.py
touch 02_transformations/wind_interpolation/src/__init__.py
touch 03_integration/src/__init__.py
```

---

### Phase 4: Update pytest Configuration

**File:** `pytest.ini`

```ini
# BEFORE
[pytest]
testpaths = tests
python_paths = . hurdat2/src census/src integration/src shared

# AFTER
[pytest]
testpaths = 05_tests
python_paths = .
```

**Note:** With absolute imports from repo root, we don't need to add individual paths.

---

### Phase 5: Verify All Tests Pass

```bash
# Run all tests
python -m pytest 05_tests/ -v

# Run specific test to debug
python -m pytest 05_tests/test_arc_polygons.py -v

# Run with more detail if needed
python -m pytest 05_tests/test_arc_polygons.py -vv -s
```

**Success criteria:**
- All 13 test files import successfully
- All tests pass (or fail for legitimate reasons, not import errors)

---

## Execution Checklist

### Test File Updates
- [ ] Fix test_arc_polygons.py
- [ ] Fix test_duration_calculator.py
- [ ] Fix test_envelope_validity.py
- [ ] Fix test_intensification_features.py
- [ ] Fix test_lead_time_calculator.py
- [ ] Fix test_storm_tract_distance.py
- [ ] Fix test_visualize_folium_qa.py
- [ ] Fix test_wind_interpolation.py
- [ ] Fix test_wind_coverage_envelope.py
- [ ] Fix test_sensitivity_analysis.py

### Source File Updates
- [ ] Check and fix 02_transformations/*/src/*.py imports
- [ ] Check and fix 03_integration/src/*.py imports
- [ ] Check and fix 03_integration/scripts/*.py imports
- [ ] Check and fix hardcoded file paths

### Package Structure
- [ ] Add __init__.py to all src directories
- [ ] Update pytest.ini
- [ ] Verify Python path resolution

### Validation
- [ ] Run pytest 05_tests/ -v
- [ ] Verify all imports work
- [ ] Verify no hardcoded path errors
- [ ] Document any remaining issues

---

## Common Patterns Reference

### Import Pattern Template

```python
# At top of test files
import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Then use absolute imports from repo root
from 01_data_sources.hurdat2.src.parse_raw import parse_hurdat2_file
from 02_transformations.duration.src.duration_calculator import calculate_duration
from 03_integration.src.feature_pipeline import run_pipeline
from 04_src_shared.geometry_utils import haversine_distance
```

### Sys.path.extend vs sys.path.insert(0)

```python
# AVOID: sys.path.extend() adds to end, lower priority
sys.path.extend([str(REPO_ROOT / "hurdat2" / "src")])

# PREFER: sys.path.insert(0) adds to beginning, higher priority
sys.path.insert(0, str(REPO_ROOT))
```

### Relative vs Absolute Imports

```python
# Within same package: relative imports OK
# File: 02_transformations/duration/src/duration_calculator.py
from .helpers import some_helper  # OK if helpers.py in same dir

# Across packages: always use absolute from repo root
from 02_transformations.wind_coverage_envelope.src.envelope_algorithm import create_envelope
```

---

## Rollback Plan

If refactoring causes issues:

```bash
# Revert all changes
git checkout .

# Or revert specific files
git checkout 05_tests/test_*.py
```

---

## Timeline Estimate

| Phase | Task | Time |
|-------|------|------|
| 1 | Fix 10 test files | 45 min |
| 2 | Fix source file imports | 30 min |
| 3 | Add __init__.py files | 5 min |
| 4 | Update pytest.ini | 5 min |
| 5 | Run tests and debug | 30 min |
| **Total** | | **~2 hours** |

Add buffer for unexpected issues: **2-3 hours total**

---

## Success Metrics

✅ **Refactoring successful when:**
- [ ] `python -m pytest 05_tests/ -v` shows 0 import errors
- [ ] All test files can be imported
- [ ] Tests pass or fail for legitimate reasons (not imports)
- [ ] No hardcoded path errors in source files
- [ ] Code can be run from repo root

---

## Next Steps After Refactoring

1. Update documentation to reflect new structure
2. Update .claude.md with correct paths
3. Update REPOSITORY_STRUCTURE.md
4. Run end-to-end pipeline to verify functionality
5. Consider creating helper imports in __init__.py files

---

## Status: READY TO EXECUTE

**Start with:** Phase 1, Step 1.1 (Fix test_arc_polygons.py)
**Work backwards from tests:** Fix imports until all tests can run
