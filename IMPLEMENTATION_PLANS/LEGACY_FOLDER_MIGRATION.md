# Legacy Folder Migration Implementation Plan

**Date Created:** 2025-10-05
**Status:** Ready for Implementation
**Priority:** High (Prerequisite for repository restructure)
**Estimated Time:** 15 minutes

---

## Objective

Move legacy data source folders into a `_legacy_data_sources/` folder to:
1. Preserve existing working code as backup
2. Clean up repository root
3. Enable validation that new structure works correctly
4. Allow safe deletion after verification

---

## Folders to Move

Based on current repository state, these are the legacy folders to archive:

### Legacy Data Source Folders
- `hurdat2/` - Original HURDAT2 processing (before restructure)
- `census/` - Original census processing (before restructure)
- `hurdat2_census/` - Original combined transformations (before restructure)
- `fema/` - FEMA data (if not actively used)

### Notes
- `integration/` - **KEEP** (still in active use, will be updated in place)
- `shared/` - **KEEP** (shared utilities)
- `tests/` - **KEEP** (will be updated in place)
- `docs/` - **KEEP** (project documentation)
- `IMPLEMENTATION_PLANS/` - **KEEP** (this folder)

---

## Implementation Steps

### Step 1: Create Legacy Archive Folder

```bash
cd /Users/Michael/hurricane-data-etl

# Create legacy archive directory
mkdir -p _legacy_data_sources

# Create README explaining the legacy folder
cat > _legacy_data_sources/README.md << 'EOF'
# Legacy Data Source Folders

**Date Archived:** 2025-10-05
**Reason:** Repository restructure to separate data_sources/ and transformations/

## Contents

These folders represent the original repository structure before the 2025-10-05 refactor.

### Archived Folders
- `hurdat2/` - Original HURDAT2 processing
- `census/` - Original census tract processing
- `hurdat2_census/` - Original combined storm-tract transformations
- `fema/` - FEMA disaster declaration data (not actively used)

## Migration Status

- **New Structure:** See `/data_sources/` and `/transformations/` folders
- **Implementation Plan:** See `/IMPLEMENTATION_PLANS/REPOSITORY_RESTRUCTURE_PLAN.md`

## Deletion Timeline

These folders will be deleted after:
1. ✅ New structure fully implemented
2. ✅ All scripts updated to use new paths
3. ✅ All tests passing with new structure
4. ✅ End-to-end pipeline verified

**Target deletion date:** 2025-10-12 (1 week buffer)

## Rollback

If issues arise with new structure:
```bash
# Restore legacy folders
mv _legacy_data_sources/hurdat2 ./
mv _legacy_data_sources/census ./
mv _legacy_data_sources/hurdat2_census ./
```

---

**Status:** Ready for deletion after validation ✅
EOF
```

**Validation:**
- [ ] `_legacy_data_sources/` directory created
- [ ] README.md explains archive purpose

---

### Step 2: Move Legacy Folders

```bash
cd /Users/Michael/hurricane-data-etl

# Move legacy data source folders
mv hurdat2 _legacy_data_sources/
mv census _legacy_data_sources/
mv hurdat2_census _legacy_data_sources/

# Move FEMA if it exists and is not actively used
if [ -d "fema" ]; then
    mv fema _legacy_data_sources/
fi

# Verify moves
echo "=== Legacy folders moved ==="
ls -la _legacy_data_sources/
```

**Expected result:**
```
_legacy_data_sources/
├── README.md
├── hurdat2/
├── census/
├── hurdat2_census/
└── fema/ (if exists)
```

**Validation:**
- [ ] Legacy folders moved successfully
- [ ] Repository root is cleaner
- [ ] No errors during move

---

### Step 3: Verify Repository Structure

```bash
cd /Users/Michael/hurricane-data-etl

# Check remaining directories in root
ls -la

# Should see:
# - data_sources/ (NEW)
# - transformations/ (NEW)
# - integration/ (KEPT, to be updated)
# - shared/ (KEPT)
# - tests/ (KEPT, to be updated)
# - docs/
# - IMPLEMENTATION_PLANS/
# - _legacy_data_sources/ (ARCHIVE)
# - .git/
# - various .md files
```

**Expected root structure after move:**
```
hurricane-data-etl/
├── _legacy_data_sources/     # ARCHIVED (legacy folders)
├── data_sources/              # NEW STRUCTURE
├── transformations/           # NEW STRUCTURE
├── integration/               # ACTIVE (needs updates)
├── shared/                    # ACTIVE
├── tests/                     # ACTIVE (needs updates)
├── docs/                      # ACTIVE
├── IMPLEMENTATION_PLANS/      # ACTIVE
├── .git/
├── .gitignore
├── requirements.txt
└── [various .md files]
```

**Validation:**
- [ ] Root directory is organized
- [ ] Legacy folders are archived
- [ ] New structure folders exist
- [ ] Active folders remain in root

---

### Step 4: Update .gitignore

Add entry to prevent accidental commits of legacy folders:

```bash
cd /Users/Michael/hurricane-data-etl

# Add to .gitignore
cat >> .gitignore << 'EOF'

# Legacy folders (archived during 2025-10-05 restructure)
_legacy_data_sources/
EOF
```

**Alternative:** If you want to commit legacy folder structure (without large files):

```bash
# Add .gitignore inside legacy folder to ignore large files
cat > _legacy_data_sources/.gitignore << 'EOF'
# Ignore data files but keep structure
*/outputs/
*/raw/
*/processed/
*.csv
*.geojson
*.html
*.png
EOF
```

**Validation:**
- [ ] .gitignore updated appropriately
- [ ] Decision made: commit legacy structure or ignore completely

---

### Step 5: Git Commit (Optional)

If committing the move to version control:

```bash
cd /Users/Michael/hurricane-data-etl

# Stage changes
git add -A

# Check status
git status

# Commit the move
git commit -m "refactor: archive legacy data source folders

- Move hurdat2/, census/, hurdat2_census/, fema/ to _legacy_data_sources/
- Prepare for new data_sources/ and transformations/ structure
- Add README explaining legacy archive

See IMPLEMENTATION_PLANS/LEGACY_FOLDER_MIGRATION.md for details"
```

**Validation:**
- [ ] Git commit successful
- [ ] Changes tracked in version control

---

### Step 6: Verify Nothing Broke

Quick sanity checks to ensure nothing critical broke:

```bash
cd /Users/Michael/hurricane-data-etl

# Check if any scripts try to import from legacy folders
grep -r "from hurdat2\." . --include="*.py" 2>/dev/null | grep -v "_legacy_data_sources" || echo "No legacy imports found (good!)"
grep -r "from census\." . --include="*.py" 2>/dev/null | grep -v "_legacy_data_sources" || echo "No legacy imports found (good!)"
grep -r "from hurdat2_census\." . --include="*.py" 2>/dev/null | grep -v "_legacy_data_sources" || echo "No legacy imports found (good!)"

# Check if any scripts have hardcoded legacy paths
grep -r "hurdat2/outputs" . --include="*.py" 2>/dev/null | grep -v "_legacy_data_sources" | head -5
grep -r "census/outputs" . --include="*.py" 2>/dev/null | grep -v "_legacy_data_sources" | head -5
```

**Expected result:**
- Should find references in `integration/` and `tests/` (these will be updated next)
- Should NOT find references in `data_sources/` or `transformations/` (new code)

**Validation:**
- [ ] Legacy import references identified
- [ ] Plan to update them documented

---

## Validation Testing

### After Legacy Move

1. **Check new structure exists:**
   ```bash
   ls -la data_sources/
   ls -la transformations/
   ```
   - Should see new folder structure (even if empty)

2. **Check legacy archived:**
   ```bash
   ls -la _legacy_data_sources/
   ```
   - Should see hurdat2/, census/, hurdat2_census/, fema/

3. **Check active folders intact:**
   ```bash
   ls -la integration/
   ls -la tests/
   ls -la shared/
   ```
   - Should all still exist

4. **Attempt to run tests (expect failures due to import paths):**
   ```bash
   python -m pytest tests/ -v
   ```
   - Failures expected (imports still point to legacy folders)
   - Document which tests fail for fixing in next phase

---

## Post-Migration Cleanup Plan

After new structure is validated and working:

### Phase 1: Validate New Structure (Week 1)
- [ ] All scripts updated to use new paths
- [ ] All tests passing
- [ ] End-to-end pipeline runs successfully
- [ ] Outputs verified correct

### Phase 2: Archive Outputs (Week 1-2)
```bash
# Copy any critical outputs from legacy folders to new structure
cp _legacy_data_sources/hurdat2/outputs/cleaned_data/hurdat2_cleaned.csv \
   data_sources/hurdat2/processed/

cp _legacy_data_sources/census/outputs/tract_centroids.geojson \
   data_sources/census/processed/
```

### Phase 3: Delete Legacy Folders (Week 2)
```bash
# Only after 100% confident new structure works
rm -rf _legacy_data_sources/

# Update .gitignore to remove legacy folder entry
```

---

## Rollback Plan

If issues arise:

### Quick Rollback (restore legacy structure)
```bash
cd /Users/Michael/hurricane-data-etl

# Move folders back
mv _legacy_data_sources/hurdat2 ./
mv _legacy_data_sources/census ./
mv _legacy_data_sources/hurdat2_census ./
mv _legacy_data_sources/fema ./ 2>/dev/null

# Remove legacy archive folder
rmdir _legacy_data_sources/

# Everything back to original state
```

### Partial Rollback (keep both structures)
```bash
# Keep legacy as backup
# Just update scripts to point to legacy temporarily
# Then fix new structure issues
```

---

## Files Affected by Legacy Move

These files currently reference legacy paths and will need updates:

### Integration Scripts
- `integration/src/feature_pipeline.py` - References hurdat2_census outputs
- `integration/src/streamlit_app.py` - May reference old paths

### Test Files
- `tests/test_duration_calculator.py` - Imports from old structure
- `tests/test_arc_polygons.py` - May import from old structure
- Various test files in `tests/`

### Documentation
- `REPOSITORY_STRUCTURE.md` - References old structure (needs update)
- `.claude.md` - References old paths (needs update)
- Various docs in `docs/`

**Next steps:** These will be addressed in REPOSITORY_RESTRUCTURE_PLAN.md Phase 5 (Update Import Paths)

---

## Success Criteria

✅ **Migration successful when:**
- [ ] Legacy folders moved to `_legacy_data_sources/`
- [ ] Repository root is clean and organized
- [ ] README in legacy folder explains archive
- [ ] Git commit captures the move
- [ ] No critical functionality immediately broken
- [ ] Plan documented for next steps

✅ **Safe to delete legacy when:**
- [ ] New structure fully implemented
- [ ] All tests passing with new structure
- [ ] End-to-end pipeline verified
- [ ] Critical outputs copied to new structure
- [ ] 1 week buffer period passed

---

## Timeline

| Step | Task | Time |
|------|------|------|
| 1 | Create legacy archive folder | 2 min |
| 2 | Move legacy folders | 3 min |
| 3 | Verify repository structure | 2 min |
| 4 | Update .gitignore | 2 min |
| 5 | Git commit | 3 min |
| 6 | Verify nothing broke | 3 min |
| **Total** | | **15 min** |

---

## Status

**Current Phase:** Ready for implementation
**Next Phase:** After migration, begin REPOSITORY_RESTRUCTURE_PLAN.md Phase 2-3 (Move data source files and transformation files)

**Dependencies:**
- None (can start immediately)

**Blocks:**
- REPOSITORY_RESTRUCTURE_PLAN.md (should do this first)

---

## Notes

### Why _legacy_data_sources instead of legacy_data_sources?
- Leading underscore signals "internal/temporary/archive"
- Sorts to top/bottom of directory listings
- Convention for "don't touch unless you know what you're doing"

### Why keep legacy folder temporarily?
- **Safety:** Easy rollback if new structure has issues
- **Reference:** Can compare outputs between old and new
- **Gradual migration:** Can cherry-pick files as needed
- **Confidence:** Don't delete until 100% sure

### Why archive instead of git branch?
- Files already committed in git history
- Easier to reference during development
- Can run old scripts if needed for comparison
- Local backup without git complexity

---

## Questions for Review

Before implementing:

1. **Folder name:** OK with `_legacy_data_sources/` or prefer different name?
2. **Git strategy:** Commit legacy folder structure or add to .gitignore?
3. **Deletion timeline:** 1 week buffer OK or need longer?
4. **FEMA folder:** Archive it too, or keep in root?

---

## Ready to Execute

**Command to start:**
```bash
cd /Users/Michael/hurricane-data-etl
bash IMPLEMENTATION_PLANS/LEGACY_FOLDER_MIGRATION.md  # Extract commands from this file
# OR manually run Step 1-6 commands above
```

**Next after completion:**
- Update `.claude.md` with new structure
- Begin REPOSITORY_RESTRUCTURE_PLAN.md Phase 2
- Document any issues encountered
