# Hurricane Data ETL - Streamlit Dashboard Plan

## Overview
Interactive dashboard for exploring hurricane track features with dynamic storm selection and Folium map visualization.

## Key Features

### 1. Hurricane Selector
- **Widget**: `st.selectbox()` dropdown
- **Data Source**: Scan `integration/outputs/` for feature CSV files
- **Format**: Display as "Hurricane Name (STORM_ID) - Year"
- **Auto-detect**: Parse available storms from output directory

### 2. Summary Statistics Panel
Display key metrics for selected hurricane:
- Total affected tracts
- Duration range (min/max/mean)
- Distance range from track
- Max wind speed experienced
- States affected
- Landfall date/location

### 3. Interactive Map Display
- **Library**: `streamlit-folium`
- **Base**: Folium map with:
  - Hurricane track (red line)
  - Wind coverage envelope (blue polygon, 20% opacity)
  - Census tract centroids (color-coded by distance)
  - Interactive tooltips (hover) showing tract ID, distance, wind, duration
  - Detailed popups (click) with full feature set

### 4. Data Table
- **Widget**: `st.dataframe()` with sorting/filtering
- Display complete feature table for selected storm
- Allow CSV download via `st.download_button()`

### 5. Analytical Charts
Using Plotly for interactivity:
- **Duration Distribution**: Histogram of exposure durations
- **Distance vs Duration**: Scatter plot showing relationship
- **Wind Speed Distribution**: Histogram of max winds experienced
- **Temporal Analysis**: Timeline showing entry/exit times

## File Structure

```
integration/
├── src/
│   └── streamlit_app.py          # Main dashboard application
├── outputs/
│   ├── ida_features_final.csv    # Hurricane Ida features
│   ├── katrina_features.csv      # (future storms)
│   └── ...
└── README_streamlit.md            # Dashboard usage instructions
```

## Implementation Steps

### Phase 1: Basic Dashboard (MVP)
1. Create `streamlit_app.py` with:
   - Storm selector dropdown
   - Load feature CSV for selected storm
   - Display summary statistics
   - Show data table

### Phase 2: Map Integration
2. Add Folium map visualization:
   - Recreate map generation logic from `plot_ida_folium.py`
   - Make it dynamic based on selected storm
   - Embed using `streamlit-folium`

### Phase 3: Analytics
3. Add analytical visualizations:
   - Plotly charts for distributions
   - Interactive filtering/selection

### Phase 4: Multi-Storm Comparison (Future)
4. Enable comparing multiple storms:
   - Side-by-side maps
   - Comparative statistics
   - Overlay multiple tracks

## Dependencies

```python
# requirements.txt additions
streamlit>=1.28.0
streamlit-folium>=0.15.0
plotly>=5.17.0
```

## Running the Dashboard

```bash
# From repo root
streamlit run integration/src/streamlit_app.py

# Dashboard will open in browser at http://localhost:8501
```

## Configuration Options

### Sidebar Controls
- **Storm Selector**: Choose hurricane from dropdown
- **Map Settings**:
  - Toggle envelope visibility
  - Toggle track visibility
  - Toggle tract centroids
  - Adjust distance color bins
- **Filter Controls**:
  - Duration threshold slider
  - Distance threshold slider
  - State selector (multi-select)

### Layout
- **Header**: Title + selected storm name
- **Left Column** (30% width):
  - Summary statistics
  - Filter controls
  - Data download button
- **Right Column** (70% width):
  - Folium map (top)
  - Analytical charts (bottom tabs)

## Data Flow

```
User selects storm
    ↓
Load {storm}_features.csv
    ↓
Parse metadata (storm name, dates, affected states)
    ↓
Generate summary statistics
    ↓
Create Folium map with:
    - Load HURDAT2 track data
    - Generate envelope
    - Plot centroids from features
    ↓
Render Plotly charts from features
    ↓
Display in Streamlit layout
```

## Future Enhancements

1. **Real-time Data**: Fetch latest HURDAT2 updates
2. **Batch Processing**: Process new storms via UI
3. **Export Options**: Download filtered subsets
4. **3D Visualization**: Time-animated track with wind field evolution
5. **Comparison Mode**: Select 2+ storms to compare metrics
6. **Advanced Filtering**: Query builder for complex conditions
7. **Caching**: Use `@st.cache_data` for expensive operations

## Performance Considerations

- Cache HURDAT2 parsing with `@st.cache_data`
- Cache envelope generation per storm
- Limit map rendering to visible/filtered tracts
- Use pagination for large data tables
- Lazy-load analytical charts (only when tab is selected)

## Example Code Skeleton

```python
import streamlit as st
import pandas as pd
from pathlib import Path
from streamlit_folium import folium_static
import folium

st.set_page_config(page_title="Hurricane Data Explorer", layout="wide")

# Sidebar
st.sidebar.title("Hurricane Data Explorer")

# Auto-detect available storms
output_dir = Path("integration/outputs")
storm_files = list(output_dir.glob("*_features*.csv"))
storm_names = [f.stem.replace("_features_final", "").replace("_features", "").upper()
               for f in storm_files]

selected_storm = st.sidebar.selectbox("Select Hurricane", storm_names)

# Load data
storm_file = output_dir / f"{selected_storm.lower()}_features_final.csv"
df = pd.read_csv(storm_file)

# Main content
col1, col2 = st.columns([3, 7])

with col1:
    st.subheader("Summary Statistics")
    st.metric("Affected Tracts", len(df))
    st.metric("Mean Duration", f"{df['duration_in_envelope_hours'].mean():.1f} hrs")
    st.metric("Max Wind", f"{df['max_wind_experienced_kt'].max():.0f} kt")

with col2:
    st.subheader("Interactive Map")
    # Generate Folium map
    m = create_hurricane_map(df, selected_storm)
    folium_static(m)

# Data table
st.subheader("Feature Data")
st.dataframe(df)
```

## Testing Checklist

- [ ] Dropdown loads all available storms
- [ ] Switching storms updates all components
- [ ] Map renders correctly with all layers
- [ ] Tooltips/popups display correct data
- [ ] Data table allows sorting/filtering
- [ ] Charts update when filters change
- [ ] Download button exports correct CSV
- [ ] Performance acceptable (<2s load time)
- [ ] Mobile responsive layout

## Deployment Options

1. **Local**: Run on localhost for development
2. **Streamlit Cloud**: Free hosting, auto-deploy from GitHub
3. **Docker**: Containerize for consistent deployment
4. **Cloud VM**: AWS/GCP/Azure with custom domain

## Documentation

Create `integration/README_streamlit.md` with:
- Installation instructions
- Running the dashboard
- Feature descriptions
- Troubleshooting common issues
- Adding new storms to the dashboard
