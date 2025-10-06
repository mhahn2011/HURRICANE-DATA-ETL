# Multi-Storm Visualization Dashboard Implementation Plan

## 1. Objective

This document outlines the plan to refactor the existing Streamlit application into a centralized, multi-storm, feature-centric dashboard. The new dashboard will use pre-calculated data to ensure fast, interactive performance and will be architected to be easily extensible for new features.

## 2. High-Level Strategy

The implementation is divided into three main phases:
1.  **Project Scaffolding:** Create the new directory structure for the dashboard application and its data.
2.  **Data Pre-computation:** Implement a script to process and save all necessary visualization data in a dashboard-ready format.
3.  **Dashboard Refactoring:** Rework the Streamlit application to use the pre-computed data and introduce new UI elements for feature selection.

---

## 3. Phase 1: Project Scaffolding & Organization

**Goal:** Prepare the project structure for the new dashboard and the pre-computation script.

*   **Step 1.1: Create New Directory Structure**
    *   Create a new top-level directory: `07_dashboard_app/`
    *   Create a subdirectory for the pre-computed data: `07_dashboard_app/data/`
    *   Create a subdirectory for dashboard modules: `07_dashboard_app/modules/`

*   **Step 1.2: Create Pre-computation Script File**
    *   Create a new empty file: `03_integration/scripts/precompute_dashboard_data.py`

*   **Step 1.3: Copy Existing Dashboard as a Starting Point**
    *   Duplicate `/03_integration/src/streamlit_app.py` to `07_dashboard_app/app.py`. This gives us a working baseline to refactor.

---

## 4. Phase 2: Implement Data Pre-computation Script

**Goal:** Populate the `07_dashboard_app/data/` directory with one GeoJSON file per target storm.

*   **Step 2.1: Initial Script Setup (`precompute_dashboard_data.py`)**
    *   Add necessary imports (`pathlib`, `json`, `pandas`, `geopandas`, etc.).
    *   Define paths for inputs (`00_config/target_hurricanes.json`, `06_outputs/ml_ready/`) and the output directory (`07_dashboard_app/data/`).

*   **Step 2.2: Load Target Storms**
    *   Read the `target_hurricanes.json` file to get the list of storm IDs and names.

*   **Step 2.3: Main Processing Loop**
    *   Iterate through each storm defined in the JSON file.
    *   Inside the loop, perform the following for each `storm_id`:

*   **Step 2.4: Load and Compute Geometries**
    *   Load the full HURDAT2 dataset to find the track for the current storm.
    *   Use the existing logic (from `storm_tract_distance.py`) to compute the storm track `LineString` and the wind coverage envelope `Polygon`.

*   **Step 2.5: Load Tract Feature Data**
    *   Load the corresponding feature CSV from `06_outputs/ml_ready/{storm_id}_features_complete.csv` into a pandas DataFrame.
    *   Convert this pandas DataFrame into a GeoDataFrame, creating `Point` geometries from the `centroid_lat` and `centroid_lon` columns.

*   **Step 2.6: Assemble GeoJSON FeatureCollection**
    *   Create a GeoDataFrame for the envelope polygon.
    *   Create a GeoDataFrame for the track line.
    *   Combine the tract points, envelope, and track GeoDataFrames into a single final GeoDataFrame. Add a column to distinguish the geometry type (e.g., 'tract', 'envelope', 'track').

*   **Step 2.7: Save Output File**
    *   Save the final, combined GeoDataFrame to a GeoJSON file in the output directory: `07_dashboard_app/data/{storm_id}.geojson`.

---

## 5. Phase 3: Refactor the Streamlit Dashboard

**Goal:** Modify `07_dashboard_app/app.py` to create the new dashboard experience.

*   **Step 3.1: Update Data Loading Logic**
    *   Remove the `discover_storm_files` and `compute_track_and_envelope` functions.
    *   Create a new, cached function `load_storm_data(storm_id)` that reads a single `{storm_id}.geojson` file from the `07_dashboard_app/data/` directory.
    *   This function will parse the GeoJSON and return the envelope, track, and a DataFrame of tract features.

*   **Step 3.2: Rework the UI Sidebar**
    *   The "Select Hurricane" dropdown will now list storms based on the available `.geojson` files in the data directory.
    *   Add a new `st.selectbox` labeled "Select Feature to Visualize". The options should be populated dynamically from the columns of the loaded tract-feature DataFrame (e.g., 'distance_km', 'duration_in_envelope_hours', 'max_wind_experienced_kt').

*   **Step 3.3: Make the Map Feature-Aware**
    *   Modify the `build_map` function.
    *   The color scale for the tract centroids should now be based on the feature selected in the new dropdown.
    *   Update the colormap and tooltip to reflect the selected feature.

*   **Step 3.4: Rework the Charts**
    *   Replace the static `st.tabs` in the `render_charts` function.
    *   Instead, dynamically render one or two plots relevant to the selected feature. An `if/elif/else` structure mapping feature names to plotting functions would work well here.
    *   For example, if `max_wind_experienced_kt` is selected, show a histogram of wind speeds.

---

## 6. Phase 4: Verification and Cleanup

*   **Step 4.1: Execute and Verify**
    *   Run the `precompute_dashboard_data.py` script to generate the data.
    *   Run the new dashboard with `streamlit run 07_dashboard_app/app.py`.
    *   Verify that all UI elements work as expected and that performance is improved.

*   **Step 4.2: Deprecate Old Artifacts (Post-Verification)**
    *   Once the new dashboard is fully functional, the old `03_integration/src/streamlit_app.py` can be removed.
    *   The static HTML maps in `06_outputs/visuals/hurdat2_census/` will also be obsolete.
