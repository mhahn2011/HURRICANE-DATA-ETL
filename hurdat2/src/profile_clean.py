"""
Data cleaning and profiling functions for HURDAT2 hurricane data
"""

import pandas as pd
import numpy as np

def clean_hurdat2_data(df):
    """
    Clean and validate HURDAT2 hurricane data

    Args:
        df: Raw HURDAT2 DataFrame from parse_raw.py

    Returns:
        pandas.DataFrame: Cleaned hurricane data
    """
    print("Starting data cleaning...")

    # Make a copy to avoid modifying original
    df_clean = df.copy()

    # Remove records with missing critical data
    initial_count = len(df_clean)

    # Remove records with no coordinates
    df_clean = df_clean.dropna(subset=['lat', 'lon'])
    print(f"Removed {initial_count - len(df_clean)} records with missing coordinates")

    # Remove records with invalid coordinates
    coord_count = len(df_clean)
    df_clean = df_clean[
        (df_clean['lat'] >= -90) & (df_clean['lat'] <= 90) &
        (df_clean['lon'] >= -180) & (df_clean['lon'] <= 180)
    ]
    print(f"Removed {coord_count - len(df_clean)} records with invalid coordinates")

    # Remove records with unrealistic wind speeds
    wind_count = len(df_clean)
    df_clean = df_clean[
        (df_clean['max_wind'].isna()) |
        ((df_clean['max_wind'] >= 10) & (df_clean['max_wind'] <= 200))
    ]
    print(f"Removed {wind_count - len(df_clean)} records with unrealistic wind speeds")

    # Sort by storm and date for consistency
    df_clean = df_clean.sort_values(['storm_id', 'date'])

    # Add derived fields
    df_clean = add_derived_fields(df_clean)

    print(f"Cleaning complete. {len(df_clean)} records remaining ({len(df_clean)/initial_count*100:.1f}%)")

    return df_clean

def add_derived_fields(df):
    """Add useful derived fields to the dataset"""

    # Add year
    df['year'] = df['date'].dt.year

    # Add month
    df['month'] = df['date'].dt.month

    # Add season categorization
    df['season'] = df['month'].apply(lambda x:
        'Peak' if x in [8, 9, 10] else
        'Early' if x in [6, 7] else
        'Late' if x in [11, 12] else
        'Off-season'
    )

    # Add movement speed (for consecutive points of same storm)
    df['speed_kts'] = np.nan
    df['direction_deg'] = np.nan

    for storm_id in df['storm_id'].unique():
        storm_mask = df['storm_id'] == storm_id
        storm_data = df[storm_mask].sort_values('date')

        if len(storm_data) > 1:
            # Calculate movement between consecutive points
            lats = storm_data['lat'].values
            lons = storm_data['lon'].values
            times = storm_data['date'].values

            speeds = []
            directions = []

            for i in range(len(lats) - 1):
                # Calculate distance and time difference
                dist_nm = haversine_distance(lats[i], lons[i], lats[i+1], lons[i+1])
                time_diff_hours = (pd.Timestamp(times[i+1]) - pd.Timestamp(times[i])).total_seconds() / 3600

                if time_diff_hours > 0:
                    speed = dist_nm / time_diff_hours  # knots
                    direction = calculate_bearing(lats[i], lons[i], lats[i+1], lons[i+1])
                else:
                    speed = 0
                    direction = 0

                speeds.append(speed)
                directions.append(direction)

            # Assign speeds (first point gets NaN, rest get calculated values)
            speeds.insert(0, np.nan)
            directions.insert(0, np.nan)

            df.loc[storm_mask, 'speed_kts'] = speeds
            df.loc[storm_mask, 'direction_deg'] = directions

    return df

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on Earth in nautical miles"""
    from math import radians, cos, sin, asin, sqrt

    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    # Earth's radius in nautical miles
    r_nm = 3440.065

    return c * r_nm

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing from point 1 to point 2 in degrees"""
    from math import radians, degrees, cos, sin, atan2

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1

    y = sin(dlon) * cos(lat2)
    x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)

    bearing = atan2(y, x)
    bearing = degrees(bearing)
    bearing = (bearing + 360) % 360  # Normalize to 0-360

    return bearing

def profile_data_quality(df):
    """Generate data quality report"""

    report = {
        'total_records': len(df),
        'unique_storms': df['storm_id'].nunique(),
        'date_range': (df['date'].min(), df['date'].max()),
        'null_counts': df.isnull().sum().to_dict(),
        'wind_speed_stats': df['max_wind'].describe().to_dict(),
        'coordinate_ranges': {
            'lat_min': df['lat'].min(),
            'lat_max': df['lat'].max(),
            'lon_min': df['lon'].min(),
            'lon_max': df['lon'].max()
        }
    }

    return report