# Filter Streamlit Dashboard to Target Hurricanes Only - Implementation Plan

## Context Summary

Currently the Streamlit wind field viewer loads all ~2000 hurricanes from HURDAT2, which creates unnecessary overhead and makes it harder to find the specific storms we're analyzing. Filter the dashboard to only show the 14 target hurricanes used in the hurricane-data-etl pipeline, improving performance and usability.

## Structured Workflow

### Step 1: Identify Target Hurricane List

1. **Locate existing hurricane list configuration**
   - Check for existing configuration file with target storm IDs
   - Look in common locations: config files, batch processing scripts, documentation
   - Expected storms: Katrina, Rita, Wilma, Gustav, Ike, Irene, Isaac, Sandy, Harvey, Irma, Maria, Michael, Laura, Ida (14 total)

2. **Create centralized configuration**
   - If no config exists, create: `00_config/target_hurricanes.json`
   - Format: List of storm IDs with metadata (name, year, region)
   - Example structure:
     ```json
     {
       "target_hurricanes": [
         {"storm_id": "AL122005", "name": "KATRINA", "year": 2005},
         {"storm_id": "AL182005", "name": "RITA", "year": 2005},
         ...
       ]
     }
     ```

### Step 2: Update Streamlit App to Use Filter

3. **Modify data loading function**
   - Update cached HURDAT2 loading function
   - After parsing all storms, filter to only target storm IDs
   - Maintain alphabetical or chronological sorting

4. **Update sidebar controls**
   - Remove year range slider (no longer needed with 14 storms)
   - Keep storm selector dropdown (now showing only 14 options)
   - Add count indicator: "Showing 14 target hurricanes"

5. **Simplify dropdown formatting**
   - Current format: "IDA (AL092021) - 2021"
   - Consider grouping by year or region if helpful
   - Ensure sorted chronologically (oldest to newest or vice versa)

### Step 3: Add Visual Indicator

6. **Add header/info box**
   - Display message: "Viewing 14 Major Gulf Coast Hurricanes (2005-2021)"
   - Optional: Show list of all included storms in expandable section
   - Link to documentation explaining selection criteria

### Step 4: Testing

7. **Verify filtering works**
   - Confirm dropdown shows exactly 14 storms
   - Test that all 14 storms load and render correctly
   - Verify performance improvement (faster initial load)

## Folder and File Organization

```
00_config/
└── target_hurricanes.json              # NEW: Central hurricane list

01_data_sources/hurdat2/src/
└── streamlit_wind_field_app.py         # MODIFY: Filter to target storms

00_plans/IMPLEMENTATION_PLANS/NEW/
└── streamlit_filter_to_target_hurricanes.md  # THIS FILE
```

## Test-Driven Development (TDD)

### Tests to Create

1. **Configuration loading test**
   - Verify JSON loads correctly
   - Test malformed JSON handling
   - Validate all storm IDs exist in HURDAT2

2. **Filtering test**
   - Assert dropdown contains exactly 14 storms
   - Verify all 14 are from target list
   - Ensure no extra storms included

3. **Manual QA**
   - Load dashboard, confirm 14 storms visible
   - Test each storm renders without error
   - Verify initial load is faster than before

## Simplicity and Value Delivery

### Minimum Viable Product (MVP)

**Core Value:**
- Focus on relevant storms only (14 vs 2000)
- Faster loading and selection
- Clearer purpose for end users

**Implementation Priority:**
1. Identify/create target storm list (highest priority)
2. Filter HURDAT2 data in Streamlit app (core feature)
3. Update UI to reflect filtering (nice-to-have)

**Deferred:**
- Advanced grouping/categorization
- Storm comparison features
- Historical context notes

## Concise Intent and Outcomes

### Implementation Steps

**Step 1: Create Configuration**
- **Intent**: Centralize target hurricane list for reuse
- **Dependencies**: None
- **Expected Outcome**: JSON file with 14 storm IDs

**Step 2: Update Streamlit App**
- **Intent**: Filter loaded storms to target list only
- **Dependencies**: Configuration file from Step 1
- **Expected Outcome**: Dropdown shows 14 storms instead of 2000

**Step 3: Simplify UI**
- **Intent**: Remove unnecessary controls (year slider)
- **Dependencies**: Filtered data from Step 2
- **Expected Outcome**: Cleaner sidebar focused on storm selection

**Step 4: Test & Validate**
- **Intent**: Ensure all 14 storms work correctly
- **Dependencies**: Updated app from Step 2-3
- **Expected Outcome**: All storms render, no errors

## Target Hurricane List

Based on typical Gulf Coast analysis (2005-2021), likely targets:

1. **AL122005** - Katrina (2005)
2. **AL182005** - Rita (2005)
3. **AL252005** - Wilma (2005)
4. **AL072008** - Gustav (2008)
5. **AL092008** - Ike (2008)
6. **AL092011** - Irene (2011)
7. **AL092012** - Isaac (2012)
8. **AL182012** - Sandy (2012)
9. **AL092017** - Harvey (2017)
10. **AL112017** - Irma (2017)
11. **AL152017** - Maria (2017)
12. **AL142018** - Michael (2018)
13. **AL132020** - Laura (2020)
14. **AL092021** - Ida (2021)

**Action Required**: Verify this list matches actual pipeline configuration

## Key Technical Decisions

### Configuration Format Choice
- **JSON** chosen for simplicity and readability
- Alternative: Python list in config.py (more flexible but less portable)
- Alternative: CSV (harder to maintain metadata)

### Filtering Location
- Filter **after parsing** HURDAT2 (reuses existing parsing logic)
- Alternative: Filter during parsing (more efficient but couples code)
- Chosen approach: Simpler, maintains separation of concerns

### UI Simplification
- Remove year slider (not needed with 14 storms)
- Keep layer toggles (still valuable)
- Add context about selection criteria

## Success Criteria

✅ **Feature Complete When**:
1. Dropdown shows exactly 14 target hurricanes
2. All other storms excluded from dropdown
3. Initial load time improves (target: <2 seconds)
4. UI clearly indicates filtering to target storms

✅ **Quality Gates**:
- Configuration file validates correctly
- All 14 storms render maps without errors
- No performance regression
- Code documentation explains filtering logic

## Implementation Estimate

- **Configuration creation**: 15 minutes
- **Streamlit app filtering**: 30 minutes
- **UI updates**: 15 minutes
- **Testing**: 30 minutes

**Total**: ~1.5 hours

## Migration Notes

### Backward Compatibility
- Original functionality (all storms) can be restored by removing filter
- Consider adding toggle: "Show all hurricanes" checkbox
- Current approach: Hard-coded filter (simpler, meets immediate need)

### Future Extensions
- Allow users to add/remove storms from target list via UI
- Group storms by decade or intensity
- Add comparison mode for multiple storms
