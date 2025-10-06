# Streamlit Hurricane Wind Field Viewer - Implementation Plan

## Context Summary

Create an interactive Streamlit dashboard that allows users to select any hurricane from the HURDAT2 database via dropdown and dynamically generate/display the arc-based wind field visualization. This replaces the need to manually regenerate static HTML files for each storm.

## Structured Workflow

### Phase 1: Basic Dashboard with Single Storm Selector

1. **Create Streamlit app structure**
   - New file: `01_data_sources/hurdat2/src/streamlit_wind_field_app.py`
   - Import necessary modules (streamlit, streamlit-folium, existing visualization functions)
   - Set page config with wide layout for map viewing

2. **Build storm selection interface**
   - Load HURDAT2 data on app startup (cache with `@st.cache_data`)
   - Extract unique storm list with format: "STORM_NAME (STORM_ID) - YEAR"
   - Create dropdown selector in sidebar
   - Display storm metadata (dates, max intensity, affected region)

3. **Integrate wind field generation**
   - Reuse `generate_qa_map()` function from `visualize_folium_qa.py`
   - Generate map dynamically based on selected storm
   - Display map using `streamlit_folium.folium_static()`
   - Add loading spinner while generating

4. **Add basic filtering controls**
   - Sidebar checkboxes to toggle wind field layers (34kt, 50kt, 64kt, RMW)
   - Checkbox to show/hide track points
   - Year range slider to filter available storms

### Phase 2: Enhanced Features

5. **Add storm statistics panel**
   - Display in sidebar or expandable section
   - Show: max wind, min pressure, duration, landfall location(s)
   - Track length, dates of formation/dissipation
   - Category at peak intensity

6. **Export functionality**
   - Button to download current map as standalone HTML
   - Save to `06_outputs/visuals/hurdat2/` with timestamp
   - Success message with file path

7. **Performance optimization**
   - Cache storm track data per storm_id
   - Cache generated maps (keyed by storm_id + layer selections)
   - Add progress bars for slow operations

### Phase 3: Multi-Storm Comparison (Optional Future)

8. **Side-by-side comparison mode**
   - Multi-select dropdown for 2-3 storms
   - Display maps in columns
   - Synchronized zoom/pan (if feasible with streamlit-folium)

## Folder and File Organization

```
01_data_sources/hurdat2/src/
├── streamlit_wind_field_app.py          # Main Streamlit app
├── visualize_folium_qa.py               # Existing (reuse functions)
└── ... (other existing files)

06_outputs/visuals/hurdat2/
└── streamlit_exports/                   # User-downloaded maps
    └── {STORM_NAME}_{TIMESTAMP}.html

requirements.txt                         # Add streamlit + streamlit-folium
```

## Test-Driven Development (TDD)

### Testing Strategy

1. **Unit tests for data loading**
   - Test storm list extraction from HURDAT2
   - Validate storm name formatting
   - Test caching behavior

2. **Integration tests**
   - Test map generation for sample storms (Ida, Katrina, Rita)
   - Verify all layer toggles work correctly
   - Test export functionality creates valid HTML

3. **Manual QA checklist**
   - Dropdown loads all storms
   - Map renders correctly for various storms
   - Layer toggles update map immediately
   - Export button downloads valid HTML
   - Performance acceptable (<3 seconds per storm)

## Simplicity and Value Delivery

### Minimum Viable Product (MVP) - Phase 1

**Goal**: Dynamic storm selection with wind field visualization

**Core Value**:
- Eliminate need to manually regenerate 2000+ static HTML files
- Enable instant exploration of any historical hurricane
- Provide interactive layer controls

**Implementation Priority**:
1. Storm selector dropdown (essential)
2. Map generation and display (essential)
3. Layer toggles (high value, low complexity)
4. Caching for performance (essential for UX)
5. Statistics panel (nice-to-have, can defer)

### Deferred to Future Iterations
- Multi-storm comparison
- Advanced filtering (by region, intensity, season)
- Track animation/time slider
- Integration with census tract features (already handled by separate dashboard plan)

## Concise Intent and Outcomes

### Step-by-Step Intent

**Step 1: App Structure**
- **Intent**: Create Streamlit entry point with proper imports
- **Dependencies**: streamlit, streamlit-folium packages installed
- **Expected Outcome**: Running `streamlit run streamlit_wind_field_app.py` opens blank dashboard

**Step 2: Storm Selector**
- **Intent**: Load all storms and present dropdown
- **Dependencies**: HURDAT2 parsing functions from existing codebase
- **Expected Outcome**: Dropdown lists ~2000 storms in readable format

**Step 3: Map Generation**
- **Intent**: Generate wind field map when storm selected
- **Dependencies**: `generate_qa_map()` from `visualize_folium_qa.py`
- **Expected Outcome**: Selecting storm displays arc-based wind field visualization

**Step 4: Layer Toggles**
- **Intent**: Allow users to show/hide specific wind thresholds
- **Dependencies**: Conditional rendering based on sidebar checkboxes
- **Expected Outcome**: Checking/unchecking layers updates map display

**Step 5: Export Function**
- **Intent**: Save current map as standalone HTML
- **Dependencies**: Folium's `.save()` method
- **Expected Outcome**: Downloaded file opens in browser showing same map

## Key Technical Decisions

### Caching Strategy
- Use `@st.cache_data` for HURDAT2 parsing (runs once)
- Use `@st.cache_resource` for map generation (keyed by storm_id)
- Clear cache button in sidebar for development/debugging

### Map Rendering Approach
- Use `streamlit_folium.folium_static()` (simple, works out of box)
- Accept limitation: map is static image in Streamlit (fully interactive when exported)
- Alternative considered: `st_folium()` for bidirectional communication (more complex, defer)

### Storm List Formatting
```
Format: "IDA (AL092021) - 2021"
Sort by: Year descending (most recent first)
Filter options: Year range, minimum intensity
```

## Dependencies to Install

```bash
pip install streamlit streamlit-folium
```

Or add to `requirements.txt`:
```
streamlit>=1.28.0
streamlit-folium>=0.15.0
```

## Running the Dashboard

```bash
# From repo root
streamlit run 01_data_sources/hurdat2/src/streamlit_wind_field_app.py

# Opens in browser at http://localhost:8501
```

## Success Criteria

✅ **MVP Complete When**:
1. User can select any hurricane from dropdown
2. Map renders with arc-based wind fields
3. Layer toggles work (34kt, 50kt, 64kt, RMW)
4. Loading time <3 seconds after selection
5. Export button downloads functional HTML

✅ **Quality Gates**:
- Dropdown lists all ~2000 storms correctly
- Maps render identically to static HTML version
- No errors when switching between storms rapidly
- Exported HTML files open and display correctly

## Implementation Estimate

- **Phase 1 (MVP)**: 2-3 hours
  - App structure: 30 min
  - Storm selector: 1 hour
  - Map integration: 1 hour
  - Layer toggles: 30 min

- **Phase 2 (Enhanced)**: 1-2 hours
  - Statistics panel: 30 min
  - Export function: 30 min
  - Optimization: 1 hour

- **Total MVP**: Half day of focused work
