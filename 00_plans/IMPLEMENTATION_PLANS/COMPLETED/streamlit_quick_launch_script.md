# Streamlit Quick Launch Script - Implementation Summary

## What Changed
- Added `00_config/target_hurricanes.json` to centralize the curated storm list used across dashboards.
- Introduced a double-clickable launcher at `06_outputs/reports/launch_streamlit_dashboards.command`.
  The script activates the project virtualenv (when present), checks for Streamlit,
  and lets users choose between the wind-field viewer (`01_data_sources/hurdat2/src/streamlit_wind_field_app.py`)
  and the tract feature explorer (`03_integration/src/streamlit_app.py`).
- Documented usage in `06_outputs/reports/README.md` (instructions, requirements,
  and manual launch hints).
- Updated the HURDAT2 Streamlit viewer to rely on the new target-storm list and
  reflect the curated scope in its UI copy (`01_data_sources/hurdat2/src/streamlit_wind_field_app.py`,
  `01_data_sources/hurdat2/README.md`).

## Testing
- Double-click launcher script (simulated via `bash 06_outputs/reports/launch_streamlit_dashboards.command`)
  to verify menu selection, dependency checks, and Streamlit invocation logic.
- Manually ran the HURDAT2 Streamlit app using the script’s command to ensure the
  filtered storm list renders correctly.

## Follow-up
- Extend the launcher script if additional dashboards are added.
- Consider notarizing or marking the `.command` file as trusted to avoid macOS gatekeeper prompts.
