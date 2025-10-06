# Streamlit Quick Launch Script - Implementation Plan

## Context Summary

Create a double-clickable shell script in the reports folder that launches the Streamlit hurricane wind field viewer without requiring users to open Terminal and navigate to the correct directory. This improves accessibility for non-technical users and streamlines the workflow.

## Structured Workflow

### Step 1: Create Launch Script

1. **Create shell script file**
   - Location: `/Users/Michael/hurricane-data-etl/06_outputs/reports/launch_wind_field_viewer.command`
   - Extension: `.command` (allows double-click launch on macOS)
   - Include shebang: `#!/bin/bash`

2. **Script contents**
   - Change directory to repository root
   - Activate virtual environment (if exists)
   - Launch Streamlit app with correct path
   - Keep terminal window open to show status

3. **Add error handling**
   - Check if virtual environment exists
   - Verify Streamlit is installed
   - Display helpful error messages if dependencies missing

### Step 2: Make Script Executable

4. **Set executable permissions**
   - Run: `chmod +x launch_wind_field_viewer.command`
   - Verify script can be executed from Finder

5. **Test double-click launch**
   - Double-click from Finder
   - Verify Terminal opens and Streamlit starts
   - Check that browser opens automatically

### Step 3: Create Documentation

6. **Add README in reports folder**
   - File: `06_outputs/reports/README.md`
   - Explain what the launch script does
   - Provide troubleshooting steps
   - Include manual launch instructions as fallback

7. **Add visual indicator**
   - Consider adding icon to script (macOS custom icon)
   - Or: Include emoji/symbol in filename for visibility

## Folder and File Organization

```
06_outputs/reports/
├── launch_wind_field_viewer.command    # NEW: Double-click launcher
└── README.md                           # NEW: Usage instructions

00_plans/IMPLEMENTATION_PLANS/NEW/
└── streamlit_quick_launch_script.md    # THIS FILE
```

## Test-Driven Development (TDD)

### Testing Strategy

1. **Script functionality test**
   - Double-click launches Streamlit
   - Browser opens to correct URL
   - Terminal shows Streamlit status

2. **Error handling test**
   - Test with virtual env deactivated
   - Test with Streamlit uninstalled
   - Verify error messages are helpful

3. **Cross-machine test**
   - Test on different macOS versions if available
   - Verify paths work on other machines (relative paths)

## Simplicity and Value Delivery

### Minimum Viable Product (MVP)

**Core Value:**
- One-click launch from Finder (no Terminal knowledge required)
- Automatic browser opening
- Clear status messages

**Implementation Priority:**
1. Basic launch script (essential)
2. Executable permissions (essential)
3. Error handling (high priority)
4. Documentation (nice-to-have)

**Deferred:**
- Custom icon (cosmetic)
- Windows/Linux compatibility (not needed)
- Advanced configuration options

## Concise Intent and Outcomes

### Implementation Steps

**Step 1: Create Script**
- **Intent**: Build shell script that navigates to repo and launches Streamlit
- **Dependencies**: None
- **Expected Outcome**: `.command` file exists in reports folder

**Step 2: Set Permissions**
- **Intent**: Make script executable from Finder
- **Dependencies**: Script from Step 1
- **Expected Outcome**: Double-clicking opens Terminal and runs script

**Step 3: Test Launch**
- **Intent**: Verify script works as expected
- **Dependencies**: Executable script from Step 2
- **Expected Outcome**: Streamlit opens in browser, no errors

**Step 4: Document**
- **Intent**: Provide user instructions
- **Dependencies**: Working script from Step 3
- **Expected Outcome**: README explains usage and troubleshooting

## Script Template

```bash
#!/bin/bash

# Hurricane Wind Field Viewer - Quick Launch Script
# Double-click this file to launch the Streamlit dashboard

echo "=============================================="
echo "  Hurricane Wind Field Viewer Launcher"
echo "=============================================="
echo ""

# Get the repository root (assumes script is in 06_outputs/reports/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$SCRIPT_DIR/../.."

echo "📂 Navigating to repository: $REPO_ROOT"
cd "$REPO_ROOT" || {
    echo "❌ ERROR: Could not find repository root"
    echo "   Expected path: $REPO_ROOT"
    exit 1
}

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate || {
        echo "⚠️  Warning: Could not activate virtual environment"
        echo "   Attempting to run without venv..."
    }
else
    echo "⚠️  No virtual environment found at .venv"
    echo "   Using system Python..."
fi

# Check if Streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ ERROR: Streamlit is not installed"
    echo ""
    echo "To install, run:"
    echo "  pip install streamlit streamlit-folium"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# Launch Streamlit app
echo ""
echo "🚀 Launching Hurricane Wind Field Viewer..."
echo "   The dashboard will open in your browser shortly..."
echo ""
echo "📍 Dashboard URL: http://localhost:8504"
echo ""
echo "To stop the dashboard, press Ctrl+C in this window"
echo "=============================================="
echo ""

streamlit run 01_data_sources/hurdat2/src/streamlit_wind_field_app.py

# Keep terminal open after Streamlit exits
echo ""
echo "Dashboard has been stopped."
read -p "Press Enter to close this window..."
```

## Key Technical Decisions

### File Extension Choice
- **`.command`** extension chosen (macOS standard for double-clickable scripts)
- Alternative: `.sh` (requires "Open With > Terminal")
- Chosen approach: Better UX for non-technical users

### Path Resolution
- Use **relative paths** from script location
- Calculate repo root dynamically
- Ensures portability across machines

### Virtual Environment Handling
- Attempt activation if `.venv` exists
- Gracefully fall back to system Python if not found
- Warn user but don't fail (allows flexibility)

### Browser Behavior
- Streamlit auto-opens browser by default
- No need to manually trigger browser launch
- User can disable auto-open via Streamlit config if desired

## Success Criteria

✅ **Script Complete When**:
1. Double-clicking opens Terminal and launches Streamlit
2. Browser automatically opens to dashboard
3. Error messages are clear and actionable
4. Script works from clean repository clone

✅ **Quality Gates**:
- Script executable without `bash` command
- Works with and without virtual environment
- Helpful error messages for missing dependencies
- README provides clear usage instructions

## Implementation Estimate

- **Script creation**: 20 minutes
- **Permission setup**: 5 minutes
- **Testing**: 15 minutes
- **Documentation**: 10 minutes

**Total**: ~50 minutes

## Platform Notes

### macOS Compatibility
- `.command` files are macOS-specific
- Terminal.app opens automatically on double-click
- Script uses bash (default shell on macOS)

### Future Cross-Platform Support
If Windows/Linux support needed:
- **Windows**: Create `.bat` or `.ps1` script
- **Linux**: Use `.desktop` file for GUI launcher
- Current implementation: macOS only (meets current need)

## README Template

```markdown
# Hurricane Wind Field Viewer - Quick Launch

## How to Use

1. **Double-click** `launch_wind_field_viewer.command`
2. Terminal will open and launch the dashboard
3. Your browser will automatically open to the dashboard
4. Select a hurricane and explore the wind fields!

## Stopping the Dashboard

Press `Ctrl+C` in the Terminal window, then press Enter to close.

## Troubleshooting

### "Permission Denied" Error
Run this command in Terminal:
```bash
chmod +x /Users/Michael/hurricane-data-etl/06_outputs/reports/launch_wind_field_viewer.command
```

### "Streamlit Not Found" Error
Install dependencies:
```bash
cd /Users/Michael/hurricane-data-etl
pip install streamlit streamlit-folium
```

### Manual Launch
If double-click doesn't work, open Terminal and run:
```bash
cd /Users/Michael/hurricane-data-etl
streamlit run 01_data_sources/hurdat2/src/streamlit_wind_field_app.py
```

## Technical Details

- **Repository Root**: `/Users/Michael/hurricane-data-etl`
- **Script Location**: `06_outputs/reports/launch_wind_field_viewer.command`
- **Dashboard URL**: http://localhost:8504
```

## Additional Enhancements (Optional)

### Custom Icon
- Create icon for `.command` file using macOS "Get Info"
- Use hurricane/weather-related icon for visual recognition

### Startup Options
- Add command-line flags to script (e.g., `--port 8505`)
- Allow configuration of browser auto-open behavior
- Support multiple dashboard variants (wind fields vs tract features)

### Logging
- Redirect Streamlit output to log file in `06_outputs/reports/logs/`
- Useful for debugging without keeping Terminal open
- Include timestamp in log filename
