# Hurricane Data Explorer Dashboard - Status

**Last Updated:** 2025-10-06
**Status:** ✅ Working (Updated for new folder structure)

---

## Quick Start

### 1. Install Dependencies (if not already installed)

```bash
pip install streamlit streamlit-folium plotly
# Or install all requirements
pip install -r requirements.txt
```

### 2. Generate Feature Data (if needed)

```bash
# Extract features for Hurricane Ida
python 03_integration/src/feature_pipeline.py AL092021
# Output: 06_outputs/ml_ready/al092021_features.csv
```

### 3. Launch Dashboard

```bash
streamlit run 03_integration/src/streamlit_app.py
```

The dashboard will open at **http://localhost:8501**

---

## ✅ Current Status

### What's Working

- ✅ **Storm selector** - Auto-detects CSVs in `06_outputs/ml_ready/`
- ✅ **Summary statistics** - Total tracts, duration ranges, distance metrics
- ✅ **Interactive Folium map** - Storm track, wind envelope, tract centroids
- ✅ **Data table viewer** - Sortable/filterable feature table
- ✅ **Analytical charts** - Duration, distance, wind distributions
- ✅ **CSV download** - Export filtered data

### Available Data

Currently loaded storms in `06_outputs/ml_ready/`:
- **Hurricane Ida (2021)** - `al092021_features.csv` (229 KB)

### Dependencies Status

All required packages installed:
- ✅ `streamlit >= 1.28.0`
- ✅ `streamlit-folium >= 0.15.0`
- ✅ `plotly`
- ✅ `pandas`
- ✅ `folium`
- ✅ `shapely`

---

## 🎯 Dashboard Features

### 1. **Storm Selector**
- Dropdown menu with all available storms
- Auto-detects any `*_features*.csv` in `06_outputs/ml_ready/`
- Format: "Hurricane Name (STORM_ID) - Year"

### 2. **Summary Metrics Panel**
- Total affected census tracts
- Duration range (min/max/mean hours in envelope)
- Distance range from track
- Maximum wind speed experienced
- States affected

### 3. **Interactive Map**
- **Base layer:** Folium map with CartoDB Positron tiles
- **Storm track:** Red line showing hurricane path
- **Wind envelope:** Blue polygon (64kt coverage area, 20% opacity)
- **Tract centroids:** Color-coded by distance to track
- **Tooltips:** Hover for quick info
- **Popups:** Click for detailed tract features

### 4. **Data Table**
- Full feature table with all columns
- Sortable by any column
- Filterable by:
  - Minimum duration threshold
  - Maximum distance from track
  - State FIPS code
- Download as CSV button

### 5. **Analytical Visualizations**
Using Plotly for interactive charts:
- **Duration Distribution** - Histogram of exposure hours
- **Distance vs Duration** - Scatter plot showing relationship
- **Wind Speed Distribution** - Histogram of max winds
- **Exposure Timeline** - Entry/exit times (when available)

---

## 📂 File Locations

### Dashboard Files
- **Main app:** `03_integration/src/streamlit_app.py`
- **Documentation:** `03_integration/README_streamlit.md`
- **This file:** `03_integration/DASHBOARD_STATUS.md`

### Data Sources
- **Feature CSVs:** `06_outputs/ml_ready/`
- **HURDAT2 data:** `01_data_sources/hurdat2/input_data/hurdat2-atlantic.txt`
- **Census tracts:** `01_data_sources/census/data/`

### Output Location
- Dashboard reads from: `06_outputs/ml_ready/`
- File pattern: `*_features*.csv`

---

## 🚀 Usage Examples

### Launch Dashboard

```bash
cd /path/to/hurricane-data-etl
streamlit run 03_integration/src/streamlit_app.py
```

### Add More Storms

```bash
# Extract features for any storm
python 03_integration/src/feature_pipeline.py <STORM_ID>

# Example: Hurricane Katrina (2005)
python 03_integration/src/feature_pipeline.py AL122005

# Dashboard will auto-detect the new CSV
```

### Process All 14 Gulf Coast Storms

```bash
python 03_integration/scripts/batch_extract_features.py

# This creates individual CSVs for each storm in 06_outputs/ml_ready/
# Plus a unified dataset: storm_tract_features.csv
```

---

## 🔧 Technical Details

### Data Flow

1. **Discovery:** Dashboard scans `06_outputs/ml_ready/` for CSVs
2. **Loading:** Reads selected storm CSV with pandas
3. **Caching:** Uses `@st.cache_data` for HURDAT2 and envelope generation
4. **Rendering:** Creates map layers and charts dynamically

### Performance Optimizations

- **Cached operations:**
  - HURDAT2 parsing (loaded once, reused)
  - Wind coverage envelope generation
  - Feature CSV loading
- **Lazy loading:** Charts only render when selected
- **Efficient filtering:** Client-side DataFrame operations

### Map Generation

Wind coverage envelope created using:
- Alpha shape algorithm (α = 0.6)
- Arc-based wind field geometry (30 points per quadrant)
- 64kt threshold for envelope boundary

---

## 📊 Required CSV Schema

For dashboard to work, feature CSVs must include:

### Essential Columns
- `tract_geoid` or `geoid`
- `centroid_lat`, `centroid_lon`
- `storm_id`, `storm_name`
- `distance_km` or `distance_to_track_km`
- `duration_in_envelope_hours` or `duration_64kt_hours`
- `max_wind_experienced_kt` or `max_wind_kt`

### Optional Columns (enable extra features)
- `first_entry_time`, `last_exit_time` - For exposure timeline
- `duration_source` - For data quality tracking
- `lead_time_cat*_hours` - For warning time analysis
- `state_fips` - For state filtering

---

## 🐛 Troubleshooting

### Dashboard shows "No storms available"

**Cause:** No CSV files in `06_outputs/ml_ready/`

**Solution:**
```bash
# Generate features for at least one storm
python 03_integration/src/feature_pipeline.py AL092021
```

### Map doesn't render

**Cause:** Missing columns in CSV

**Solution:** Verify CSV has required columns (see schema above)

### Module import errors

**Cause:** Missing dependencies or wrong paths

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify streamlit installed
streamlit --version
```

### Wind envelope doesn't appear

**Cause:** HURDAT2 file not found or missing wind radii

**Solution:**
- Check HURDAT2 file exists at `01_data_sources/hurdat2/input_data/hurdat2-atlantic.txt`
- Verify storm has 64kt wind radii data

---

## 🔄 Recent Updates (2025-10-06)

### Fixed for New Folder Structure
- ✅ Updated all paths from old structure → numbered folders
- ✅ OUTPUT_DIR: `integration/outputs` → `06_outputs/ml_ready`
- ✅ HURDAT_PATH: `hurdat2/input_data` → `01_data_sources/hurdat2/input_data`
- ✅ Import paths: `hurdat2/src` → `01_data_sources/hurdat2/src`
- ✅ Documentation updated in README_streamlit.md

### Added
- ✅ Hurricane Ida features in new output location
- ✅ This status document

---

## 📈 Future Enhancements

### Planned Features (Not Yet Implemented)

1. **Multi-Storm Comparison**
   - Side-by-side map views
   - Comparative statistics table
   - Overlay multiple storm tracks

2. **Advanced Filtering**
   - Wind speed range slider
   - Lead time threshold filters
   - County-level aggregation

3. **Export Options**
   - PDF report generation
   - PNG map export
   - Filtered dataset download

4. **Real-Time Updates**
   - Auto-refresh when new CSVs added
   - File watcher for output directory

---

## 📞 Support

**Documentation:**
- Main README: [`00_documentation/README.md`](../00_documentation/README.md)
- Dashboard README: [`README_streamlit.md`](README_streamlit.md)
- Feature Methodology: [`00_documentation/FEATURE_METHODOLOGY.md`](../00_documentation/FEATURE_METHODOLOGY.md)

**Implementation Plans:**
- Original plan: [`-01_plans/IMPLEMENTATION_PLANS/COMPLETED/streamlit_dashboard_plan.md`](../-01_plans/IMPLEMENTATION_PLANS/COMPLETED/streamlit_dashboard_plan.md)

---

## ✅ Quick Checklist

Before launching dashboard:

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] At least one CSV in `06_outputs/ml_ready/`
- [ ] HURDAT2 file exists at `01_data_sources/hurdat2/input_data/hurdat2-atlantic.txt`
- [ ] Port 8501 available (or use `--server.port` flag)

Launch command:
```bash
streamlit run 03_integration/src/streamlit_app.py
```

---

**Dashboard is ready to use! 🎉**
