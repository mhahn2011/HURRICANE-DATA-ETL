#!/bin/bash

# Streamlit Dashboard Quick Launcher
# Double-click this script to choose a dashboard to run.

set -e

# Find the repository root directory regardless of where the script is run from
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$SCRIPT_DIR" # Assuming the script is in the repo root

cd "$REPO_ROOT" || {
  echo "❌ ERROR: Repository root not found at $REPO_ROOT"
  read -p "Press Enter to exit..."
  exit 1
}

# Activate virtual environment if present
if [ -d ".venv" ]; then
  echo "🐍 Activating virtual environment (.venv)"
  source .venv/bin/activate || echo "⚠️ Warning: could not activate .venv"
fi

# Check streamlit availability
if ! command -v streamlit >/dev/null 2>&1; then
  echo "❌ Streamlit is not installed."
  echo "   Install via: pip install streamlit streamlit-folium plotly geopandas"
  read -p "Press Enter to exit..."
  exit 1
fi

# Prompt user for dashboard selection
cat <<CHOICES
==============================================
 Streamlit Dashboard Launcher
==============================================
1) Hurricane Feature Dashboard (Recommended)
2) Hurricane Wind Field Viewer (Simple)
q) Quit
==============================================
CHOICES

read -p "Select an option: " choice

case "$choice" in
  1)
    DASHBOARD_PATH="07_dashboard_app/app.py"
    PORT=8501
    TITLE="Hurricane Feature Dashboard"
    ;;
  2)
    DASHBOARD_PATH="01_data_sources/hurdat2/src/streamlit_wind_field_app.py"
    PORT=8504
    TITLE="Hurricane Wind Field Viewer"
    ;;
  q|Q)
    echo "Goodbye!"
    exit 0
    ;;
  *)
    echo "Invalid selection."
    read -p "Press Enter to exit..."
    exit 1
    ;;
 esac

if [ ! -f "$DASHBOARD_PATH" ]; then
  echo "❌ Dashboard script not found: $DASHBOARD_PATH"
  read -p "Press Enter to exit..."
  exit 1
fi

echo ""
echo "🚀 Launching $TITLE"
echo "   URL: http://localhost:$PORT"
echo "Press Ctrl+C in this window to stop the dashboard."
echo ""

streamlit run "$DASHBOARD_PATH" --server.port=$PORT

echo ""
echo "Dashboard stopped."
read -p "Press Enter to close this window..."
