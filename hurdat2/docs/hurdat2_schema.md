# HURDAT2 Data Schema & Field Definitions

## File Structure Overview

**Format**: ASCII text, comma-delimited
**Line Types**: Header lines + Data lines
**Update Frequency**: Annual (April)
**Coverage**: Atlantic Basin 1851-2024

## Header Line Schema

```
AL092021, IDA, 40,
```

| Position | Field Name | Data Type | Description | Example |
|----------|-----------|-----------|-------------|---------|
| 1-2 | Basin | String(2) | Basin identifier | AL (Atlantic) |
| 3-4 | Cyclone Number | String(2) | ATCF cyclone number for year | 09 |
| 5-8 | Year | Integer | Storm year | 2021 |
| 9-18 | Name | String(10) | Storm name or "UNNAMED" | IDA |
| 19+ | Record Count | Integer | Number of data records following | 40 |

## Data Line Schema (21 Fields)

```
20210829, 1655, L, HU, 29.1N, 90.2W, 130, 931, 130, 110, 80, 110, 70, 60, 40, 60, 45, 35, 20, 30, 10
```

| Field | Name | Type | Units | Range | Missing Value | Description |
|-------|------|------|-------|-------|---------------|-------------|
| 1 | **date** | String(8) | YYYYMMDD | 1851-2024 | - | UTC date |
| 2 | **time** | String(4) | HHMM | 0000-2359 | - | UTC time (usually 00/06/12/18) |
| 3 | **record_id** | String(1) | - | C,G,I,L,P,R,S,T,W | (blank) | Record type identifier |
| 4 | **status** | String(2) | - | TD,TS,HU,EX,SD,SS,LO,WV,DB | - | Storm classification |
| 5 | **latitude** | Float | Degrees | -90 to 90 | - | Storm center latitude |
| 6 | **longitude** | Float | Degrees | -180 to 180 | - | Storm center longitude |
| 7 | **max_wind** | Integer | Knots | 15-200 | - | Maximum sustained wind (1-min avg at 10m) |
| 8 | **min_pressure** | Integer | Millibars | 870-1050 | -999 | Central pressure |
| 9 | **wind_radii_34_ne** | Integer | Nautical Miles | 0-500 | -999 | 34kt wind extent, NE quadrant |
| 10 | **wind_radii_34_se** | Integer | Nautical Miles | 0-500 | -999 | 34kt wind extent, SE quadrant |
| 11 | **wind_radii_34_sw** | Integer | Nautical Miles | 0-500 | -999 | 34kt wind extent, SW quadrant |
| 12 | **wind_radii_34_nw** | Integer | Nautical Miles | 0-500 | -999 | 34kt wind extent, NW quadrant |
| 13 | **wind_radii_50_ne** | Integer | Nautical Miles | 0-300 | -999 | 50kt wind extent, NE quadrant |
| 14 | **wind_radii_50_se** | Integer | Nautical Miles | 0-300 | -999 | 50kt wind extent, SE quadrant |
| 15 | **wind_radii_50_sw** | Integer | Nautical Miles | 0-300 | -999 | 50kt wind extent, SW quadrant |
| 16 | **wind_radii_50_nw** | Integer | Nautical Miles | 0-300 | -999 | 50kt wind extent, NW quadrant |
| 17 | **wind_radii_64_ne** | Integer | Nautical Miles | 0-200 | -999 | 64kt wind extent, NE quadrant |
| 18 | **wind_radii_64_se** | Integer | Nautical Miles | 0-200 | -999 | 64kt wind extent, SE quadrant |
| 19 | **wind_radii_64_sw** | Integer | Nautical Miles | 0-200 | -999 | 64kt wind extent, SW quadrant |
| 20 | **wind_radii_64_nw** | Integer | Nautical Miles | 0-200 | -999 | 64kt wind extent, NW quadrant |
| 21 | **radius_max_wind** | Integer | Nautical Miles | 3-100 | -999 | Radius of maximum wind |

## Code Definitions

### Record Identifiers (Field 3)
| Code | Meaning | Description |
|------|---------|-------------|
| **L** | **Landfall** | Storm center crossing coastline |
| C | Closest Approach | Nearest point to coast without landfall |
| G | Genesis | Storm formation |
| I | Intensity Peak | Peak in both pressure and wind |
| P | Pressure Minimum | Minimum central pressure |
| W | Wind Maximum | Maximum sustained wind |
| R | Rapid Change | Additional detail during rapid intensification |
| S | Status Change | Change in storm classification |
| T | Track Detail | Additional position detail |

### Storm Status Codes (Field 4)
| Code | Meaning | Wind Speed | Description |
|------|---------|------------|-------------|
| **TD** | **Tropical Depression** | <34 knots | Organized circulation, low winds |
| **TS** | **Tropical Storm** | 34-63 knots | Named storm |
| **HU** | **Hurricane** | ≥64 knots | Major tropical cyclone |
| EX | Extratropical | Any | Transitioned to winter storm |
| SD | Subtropical Depression | <34 knots | Hybrid characteristics |
| SS | Subtropical Storm | ≥34 knots | Hybrid characteristics |
| LO | Low | Any | Non-tropical/subtropical low |
| WV | Tropical Wave | Any | Degenerated, no surface center |
| DB | Disturbance | Any | Weak system |

## Data Quality Eras

### Wind Radii Availability
- **2004-Present**: All wind radii fields available
- **Pre-2004**: Wind radii marked as -999 (missing)

### Pressure Data Quality  
- **1979-Present**: Complete central pressure analysis
- **Pre-1979**: Many missing values (-999)

### Radius of Maximum Wind
- **2021-Present**: RMW available
- **Pre-2021**: RMW marked as -999 (missing)

### Historical Accuracy
- **1979-Present**: High quality (satellite era)
- **1944-1978**: Good quality (aircraft reconnaissance)
- **Pre-1944**: Lower quality (ship observations only)

## Wind Field Interpretation

### Quadrant System
- **NE**: 0° to 90° from storm center
- **SE**: 90° to 180° from storm center  
- **SW**: 180° to 270° from storm center
- **NW**: 270° to 360° from storm center

### Wind Speed Zones (Nested)
- **34kt radius**: Area with ≥34 knot winds (tropical storm force)
- **50kt radius**: Area with ≥50 knot winds (strong tropical storm)
- **64kt radius**: Area with ≥64 knot winds (hurricane force)

**Key Insight**: 64kt ⊆ 50kt ⊆ 34kt (nested circles in each quadrant)

## Common Data Issues

### Missing Data Patterns
- **Pressure**: -999 for older storms
- **Wind Radii**: -999 for pre-2004 storms
- **RMW**: -999 for pre-2021 storms

### Data Quality Flags
- **Pre-1944**: Underestimated intensities (no aircraft)
- **1944-1966**: Aircraft data, but limited satellite
- **1967-1978**: Early satellite era
- **1979+**: Modern satellite analysis

### Coordinate System
- **Latitude**: Positive = North, Negative = South
- **Longitude**: Positive = East, Negative = West
- **Precision**: 0.1 degrees (≈6 nautical miles)

## Implementation Notes

### For ML Feature Engineering
1. **Storm Tracking**: Use lat/lon fields for distance calculations
2. **Intensity**: Use max_wind and min_pressure
3. **Wind Field**: Use quadrant-specific radii for tract-level wind assignment
4. **Landfall Detection**: Filter for record_id = 'L'
5. **Storm Selection**: Filter for status in ['TS', 'HU'] for significant impacts

### For New Orleans Analysis
- **Gulf Coast Filter**: Latitude 25-32°N, Longitude 80-98°W
- **Distance Calculation**: Haversine distance to 29.95°N, 90.07°W
- **Quadrant Assignment**: Calculate bearing from New Orleans to storm center