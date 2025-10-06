# Lead Time Features - Implementation Plan

## Feature Definition
Calculate warning time for each tract by measuring the time between when the storm reached various category thresholds and when it made closest approach to the tract.

**Categories**: Cat 1 (64kt), Cat 2 (83kt), Cat 3 (96kt), Cat 4 (113kt), Cat 5 (137kt)

---

## Algorithm

For each tract centroid:

1. Get `nearest_approach_time` from existing distance features
2. For each category threshold:
   - Find first time storm reached that threshold in the track
   - Calculate: `lead_time = nearest_approach_time - threshold_time`
   - Result in hours (positive = had warning, negative = intensified after passing)

**Output**: 5 lead time features per tract

---

## Implementation

### File to Create: `integration/src/lead_time_calculator.py`

**Inputs**:
- Storm track DataFrame (from `parse_raw.py` + `profile_clean.py`)
  - Columns needed: `date`, `max_wind`
- Nearest approach time (from `compute_min_distance_features()`)
  - Column: `storm_time`

**Functions to implement**:

```python
CATEGORY_THRESHOLDS = {
    'cat1': 64,   # Tropical Storm -> Hurricane
    'cat2': 83,   # Category 1 -> Category 2
    'cat3': 96,   # Category 2 -> Category 3
    'cat4': 113,  # Category 3 -> Category 4
    'cat5': 137   # Category 4 -> Category 5
}

def find_category_threshold_time(
    track_df: pd.DataFrame,
    threshold_kt: int
) -> datetime or None:
    """
    Find first time storm reached given wind speed threshold.

    Args:
        track_df: Storm track with 'date' and 'max_wind' columns
        threshold_kt: Wind speed threshold in knots

    Returns:
        datetime: First time max_wind >= threshold_kt
        None: If storm never reached threshold

    Example:
        >>> find_category_threshold_time(ida_track, 113)  # Cat 4
        Timestamp('2021-08-29 12:00:00')
    """
```

```python
def calculate_lead_times(
    track_df: pd.DataFrame,
    nearest_approach_time: datetime
) -> dict:
    """
    Calculate lead times for all category thresholds.

    Args:
        track_df: Storm track DataFrame
        nearest_approach_time: Time of closest approach to tract

    Returns:
        {
            'lead_time_cat1_hours': float or None,
            'lead_time_cat2_hours': float or None,
            'lead_time_cat3_hours': float or None,
            'lead_time_cat4_hours': float or None,
            'lead_time_cat5_hours': float or None
        }

    Notes:
        - Positive value: Tract had warning time after threshold
        - Negative value: Storm intensified after passing tract
        - None: Storm never reached that threshold

    Example for Hurricane Ida at New Orleans:
        {
            'lead_time_cat1_hours': 48.5,   # Had ~2 days warning
            'lead_time_cat2_hours': 42.0,
            'lead_time_cat3_hours': 36.5,
            'lead_time_cat4_hours': 12.0,   # Only 12 hours after Cat 4
            'lead_time_cat5_hours': None    # Never reached Cat 5
        }
    """
```

---

## Integration

### Update: `integration/src/storm_tract_distance.py`

Add lead time calculation in the existing feature loop:

```python
from lead_time_calculator import calculate_lead_times

# In run_pipeline(), within the existing loop over centroids_in_envelope:

wind_rows = []
duration_rows = []
lead_time_rows = []  # NEW

for idx, centroid_row in centroids_in_envelope.iterrows():
    centroid_geom = centroid_row.geometry

    # Existing: Wind features
    wind_data = calculate_max_wind_experienced(...)
    wind_rows.append(wind_data)

    # Existing: Duration features
    duration_data = calculate_duration_for_tract(...)
    duration_rows.append(duration_data)

    # NEW: Lead time features
    # Get nearest approach time from base_features
    nearest_approach_time = base_features.loc[idx, 'storm_time']

    lead_time_data = calculate_lead_times(
        track_df=track,
        nearest_approach_time=nearest_approach_time
    )
    lead_time_rows.append(lead_time_data)

# Combine all features
wind_df = pd.DataFrame(wind_rows)
duration_df = pd.DataFrame(duration_rows)
lead_time_df = pd.DataFrame(lead_time_rows)  # NEW

combined = pd.concat([base_features, wind_df, duration_df, lead_time_df], axis=1)
```

---

## Testing

### Unit Tests: `tests/test_lead_time_calculator.py`

```python
def test_find_category_threshold_time_basic():
    """Test finding Cat 4 threshold in track"""
    track = pd.DataFrame({
        'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 06:00', '2021-08-28 12:00']),
        'max_wind': [80, 100, 115]
    })

    cat4_time = find_category_threshold_time(track, threshold_kt=113)

    assert cat4_time == pd.Timestamp('2021-08-28 12:00')

def test_find_category_threshold_never_reached():
    """Test when storm never reaches threshold"""
    track = pd.DataFrame({
        'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 06:00']),
        'max_wind': [60, 75]
    })

    cat4_time = find_category_threshold_time(track, threshold_kt=113)

    assert cat4_time is None

def test_calculate_lead_times_positive():
    """Test positive lead time (warning time)"""
    track = pd.DataFrame({
        'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-28 12:00']),
        'max_wind': [80, 115]
    })
    nearest_approach = pd.Timestamp('2021-08-29 00:00')

    lead_times = calculate_lead_times(track, nearest_approach)

    # 12 hours from Cat 4 to closest approach
    assert lead_times['lead_time_cat4_hours'] == 12.0
    assert lead_times['lead_time_cat5_hours'] is None

def test_calculate_lead_times_negative():
    """Test negative lead time (intensified after passing)"""
    track = pd.DataFrame({
        'date': pd.to_datetime(['2021-08-28 00:00', '2021-08-29 12:00']),
        'max_wind': [80, 115]
    })
    nearest_approach = pd.Timestamp('2021-08-29 00:00')

    lead_times = calculate_lead_times(track, nearest_approach)

    # Storm reached Cat 4 12 hours AFTER closest approach
    assert lead_times['lead_time_cat4_hours'] == -12.0
```

### Integration Test: `integration/scripts/test_lead_time_ida.py`

```python
# Load Ida track
ida_track = load_ida_track()

# Test tract: New Orleans (close to landfall)
test_approach_time = pd.Timestamp('2021-08-29 18:00')  # Approximate landfall time

# Calculate lead times
lead_times = calculate_lead_times(ida_track, test_approach_time)

print("Lead times for New Orleans tract:")
for cat, hours in lead_times.items():
    if hours is not None:
        print(f"  {cat}: {hours:.1f} hours")
    else:
        print(f"  {cat}: Never reached")

# Expected for Ida (reached Cat 4, not Cat 5):
# - lead_time_cat1_hours: ~48+ hours (positive, good warning)
# - lead_time_cat2_hours: ~36+ hours
# - lead_time_cat3_hours: ~24+ hours
# - lead_time_cat4_hours: ~12+ hours
# - lead_time_cat5_hours: None
```

---

## Expected Output

### New Columns in `storm_tract_features.csv`:

```
...,lead_time_cat1_hours,lead_time_cat2_hours,lead_time_cat3_hours,lead_time_cat4_hours,lead_time_cat5_hours
...,48.5,42.0,36.5,12.0,
```

**For Hurricane Ida (~456 tracts)**:
- All tracts will have Cat 1-4 lead times (Ida reached Cat 4)
- All tracts will have `None` for Cat 5 (Ida peaked at 130kt, below 137kt threshold)
- Coastal tracts near landfall: Shorter lead times (6-24 hours for Cat 4)
- Inland/distant tracts: Longer lead times or negative (storm weakened after passing)

**For weaker storms** (e.g., Sally, Zeta):
- May only have Cat 1-2 lead times
- Cat 3-5 will be `None`

---

## Category Threshold Reference

| Category | Wind Speed (kt) | Description |
|----------|----------------|-------------|
| Cat 1 | 64-82 | Minimal hurricane |
| Cat 2 | 83-95 | Moderate hurricane |
| Cat 3 | 96-112 | Major hurricane |
| Cat 4 | 113-136 | Extreme hurricane |
| Cat 5 | 137+ | Catastrophic hurricane |

**Our 14 storms peak intensities**:
- Cat 5: Katrina (150kt), Rita (155kt), Irma (155kt)
- Cat 4: Dennis (130kt), Gustav (135kt), Ike (125kt), Michael (140kt), Ida (130kt), Ian (140kt), Laura (130kt)
- Cat 2-3: Harvey (115kt), Delta (120kt), Zeta (100kt), Sally (95kt)

**Result**: Most storms will have Cat 1-3 values, ~10/14 will have Cat 4, ~3/14 will have Cat 5

---

## Performance

**Complexity**: O(1) per tract - just table lookup and subtraction

**For 456 Ida tracts**:
- 456 × 5 category checks = 2,280 operations
- Expected time: < 0.1 seconds (trivial)

**No optimization needed** - this is extremely fast

---

## Implementation Steps

1. **Create `integration/src/lead_time_calculator.py`** (30 min)
   - `find_category_threshold_time()` function
   - `calculate_lead_times()` function
   - `CATEGORY_THRESHOLDS` constant

2. **Create unit tests** `tests/test_lead_time_calculator.py` (30 min)
   - Test threshold detection
   - Test positive/negative lead times
   - Test storms that never reach threshold

3. **Integrate into pipeline** (15 min)
   - Update `integration/src/storm_tract_distance.py`
   - Add lead_time_rows collection
   - Concatenate lead_time_df to output

4. **Run integration test** (15 min)
   - Test with Ida (should have Cat 1-4 values)
   - Test with Sally (should have Cat 1-2 values, Cat 3+ None)
   - Validate ranges

**Total estimated time**: 1.5 hours

---

## File Locations Summary

**Create**:
- `integration/src/lead_time_calculator.py`
- `tests/test_lead_time_calculator.py`
- `integration/scripts/test_lead_time_ida.py`

**Modify**:
- `integration/src/storm_tract_distance.py` (add lead time to feature loop)

**Read from**:
- `hurdat2/input_data/hurdat2-atlantic.txt` (storm tracks with max_wind)
- Existing `base_features` DataFrame (storm_time column)

**Write to**:
- `integration/outputs/ida_complete_features.csv` (with all features)

**No new dependencies**: Uses only pandas datetime operations

---

## Success Criteria

✅ **Threshold detection working**: Correctly finds first time each category is reached

✅ **Lead times calculated**: All 456 Ida tracts have 5 lead time columns

✅ **Null handling**: Tracts have `None` for Cat 5 (Ida never reached it)

✅ **Sign correctness**:
- Positive values for tracts impacted after intensification
- Negative values for tracts impacted before peak intensity

✅ **Reasonable ranges**:
- Cat 1 lead times: -48 to +96 hours (wide range)
- Cat 4 lead times: -24 to +48 hours (narrower, closer to landfall)

✅ **Performance**: < 1 second to process all lead times for one storm

---

## Open Questions

1. **Threshold on the boundary**: If max_wind = 113 exactly, is that Cat 4 or still Cat 3?
   - **Recommendation**: Use `>=` (113kt is Cat 4)

2. **Storm weakening**: Should we track "last time" at threshold or "first time"?
   - **Recommendation**: First time (measures initial intensification)

3. **Multiple intensification cycles**: If storm weakens then re-intensifies?
   - **Recommendation**: Use first occurrence (conservative estimate of warning time)

4. **Output for very weak storms**: Tropical storms that never reach Cat 1?
   - **Recommendation**: All lead times = None (handled automatically)
