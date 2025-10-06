# Hurricane Data Explorer Dashboard

Interactive Streamlit dashboard for visualising tract-level hurricane impacts
produced by the integration pipeline.

## Prerequisites

1. Install dependencies (ideally within the project virtualenv):

   ```bash
   pip install -r requirements.txt
   ```

   > **Note:** If running in an offline or firewalled environment, manually
   > install `streamlit`, `streamlit-folium`, and `plotly` from a trusted wheel
   > source before launching the dashboard.

2. Generate storm feature CSVs under `03_integration/outputs/`. The dashboard
   auto-detects any file matching `*_features*.csv` and reads metadata from the
   first record.

   ```bash
   # Single storm (e.g., Hurricane Ida)
   python 03_integration/src/feature_pipeline.py AL092021 \
       --output 03_integration/outputs/al092021_features_complete.csv

   # Batch process the curated 14-storm set
   python 03_integration/scripts/batch_extract_features.py
   ```

   Both commands expect the raw HURDAT2 feed at
   `01_data_sources/hurdat2/raw/hurdat2-atlantic.txt` and census tracts under
   `01_data_sources/census/`.

## Launching the App

```bash
streamlit run 03_integration/src/streamlit_app.py
```

The app opens at <http://localhost:8501>. Use the sidebar to select a storm and
filter results by duration, distance, or state.

## Feature CSV Schema

Each `_features_complete.csv` must include at minimum:

- `tract_geoid`
- `centroid_lat`, `centroid_lon`
- `storm_id`, `storm_name`, `storm_time`
- `distance_km`
- `duration_in_envelope_hours`
- `max_wind_experienced_kt`

Optional columns (automatically added by the extraction pipeline) enable extra
widgets: `first_entry_time`, `last_exit_time`, `duration_source`, and the
`lead_time_cat*_hours` metrics.

## Features

- Dynamic storm selector driven by output CSV inventory
- Summary metrics (affected tracts, duration range, distance range, max wind)
- Folium map embedded via `streamlit-folium` with optional layers:
  - 64kt wind coverage envelope from the union-of-arcs algorithm
  - Storm centreline track
  - Census tract centroids colour-coded by distance to track
- Downloadable feature table view with on-the-fly filtering
- Plotly charts: duration distribution, distance vs. duration, wind histogram,
  and exposure timeline

## Notes

- Computationally heavy steps (HURDAT2 parsing, envelope creation, CSV reads)
  are memoised with `@st.cache_data`.
- Exposure timeline plot is shown when `first_entry_time`/`last_exit_time`
  columns are available.
- For best performance, run the dashboard on a machine with local copies of
  the feature CSVs and HURDAT2 dataset.

## Troubleshooting

- **Dashboard shows no storms:** Ensure `_features_complete.csv` files exist in
  `03_integration/outputs/` and contain the required columns above.
- **`ModuleNotFoundError` for Streamlit/Plotly:** Install the new dashboard
  dependencies (see prerequisites) or update your virtualenv.
- **Feature extraction errors:** Make sure the HURDAT2 feed lives at
  `01_data_sources/hurdat2/raw/hurdat2-atlantic.txt` and that the census TIGER/Line
  ZIPs are present under `01_data_sources/census/`.
