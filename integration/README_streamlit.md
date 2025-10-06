# Hurricane Data Explorer Dashboard

Interactive Streamlit dashboard for visualising tract-level hurricane impacts
produced by the integration pipeline.

## Prerequisites

1. Install dependencies (ideally within the project virtualenv):

   ```bash
   pip install -r requirements.txt
   ```

2. Generate storm feature CSVs under `integration/outputs/` using the existing
   ETL workflows (e.g. `python integration/src/storm_tract_distance.py`). The
   dashboard automatically discovers files that match `*_features*.csv` and reads
   their metadata from the first row.

## Launching the App

```bash
streamlit run integration/src/streamlit_app.py
```

The app opens at <http://localhost:8501>. Use the sidebar to select a storm and
filter results by duration, distance, or state.

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
