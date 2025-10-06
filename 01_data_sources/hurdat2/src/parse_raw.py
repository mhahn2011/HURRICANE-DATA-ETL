"""
HURDAT2 parser for Atlantic hurricane database

HURDAT2 format has two types of lines:
1. Header lines: Storm ID, Name, Number of records
2. Data lines: Date/time, status, lat/lon, wind speed, pressure, etc.
"""

import pandas as pd
from datetime import datetime
import re

def parse_hurdat2_file(file_path):
    """
    Parse HURDAT2 Atlantic hurricane database file into a pandas DataFrame

    Args:
        file_path: Path to HURDAT2 text file

    Returns:
        pandas.DataFrame with hurricane track data
    """
    records = []
    current_storm_id = None
    current_storm_name = None

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Check if this is a header line (storm info)
            # Format: AL092021,                IDA,     40,
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3 and len(parts) <= 4 and parts[0].startswith('AL') and parts[2].isdigit():
                current_storm_id = parts[0].strip()
                current_storm_name = parts[1].strip() if parts[1].strip() else 'UNNAMED'
                print(f"Found storm: {current_storm_id} - {current_storm_name}")
                continue

            # This is a data line (track point)
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 7:
                continue  # Skip malformed lines

            try:
                # Parse basic fields
                date_str = parts[0]
                time_str = parts[1]
                record_id = parts[2] if parts[2] else ''
                status = parts[3]
                lat_str = parts[4]
                lon_str = parts[5]
                max_wind = int(parts[6]) if parts[6] != '-999' else None
                min_pressure = int(parts[7]) if len(parts) > 7 and parts[7] != '-999' else None

                # Parse wind radii (nautical miles) - modern HURDAT2 format
                wind_radii_34_ne = int(parts[8]) if len(parts) > 8 and parts[8] != '-999' and parts[8] != '0' else None
                wind_radii_34_se = int(parts[9]) if len(parts) > 9 and parts[9] != '-999' and parts[9] != '0' else None
                wind_radii_34_sw = int(parts[10]) if len(parts) > 10 and parts[10] != '-999' and parts[10] != '0' else None
                wind_radii_34_nw = int(parts[11]) if len(parts) > 11 and parts[11] != '-999' and parts[11] != '0' else None

                wind_radii_50_ne = int(parts[12]) if len(parts) > 12 and parts[12] != '-999' and parts[12] != '0' else None
                wind_radii_50_se = int(parts[13]) if len(parts) > 13 and parts[13] != '-999' and parts[13] != '0' else None
                wind_radii_50_sw = int(parts[14]) if len(parts) > 14 and parts[14] != '-999' and parts[14] != '0' else None
                wind_radii_50_nw = int(parts[15]) if len(parts) > 15 and parts[15] != '-999' and parts[15] != '0' else None

                wind_radii_64_ne = int(parts[16]) if len(parts) > 16 and parts[16] != '-999' and parts[16] != '0' else None
                wind_radii_64_se = int(parts[17]) if len(parts) > 17 and parts[17] != '-999' and parts[17] != '0' else None
                wind_radii_64_sw = int(parts[18]) if len(parts) > 18 and parts[18] != '-999' and parts[18] != '0' else None
                wind_radii_64_nw = int(parts[19]) if len(parts) > 19 and parts[19] != '-999' and parts[19] != '0' else None

                radius_max_wind = (
                    int(parts[20])
                    if len(parts) > 20 and parts[20] not in {'-999', '0', ''}
                    else None
                )

                # Parse coordinates
                lat = parse_coordinate(lat_str)
                lon = parse_coordinate(lon_str)

                # Parse date/time
                date_obj = datetime.strptime(date_str + time_str.zfill(4), '%Y%m%d%H%M')

                # Determine storm category
                category = get_storm_category(status, max_wind)

                record = {
                    'storm_id': current_storm_id,
                    'storm_name': current_storm_name,
                    'date': date_obj,
                    'record_id': record_id,
                    'status': status,
                    'lat': lat,
                    'lon': lon,
                    'max_wind': max_wind,
                    'min_pressure': min_pressure,
                    'category': category,
                    # Wind radii in nautical miles
                    'wind_radii_34_ne': wind_radii_34_ne,
                    'wind_radii_34_se': wind_radii_34_se,
                    'wind_radii_34_sw': wind_radii_34_sw,
                    'wind_radii_34_nw': wind_radii_34_nw,
                    'wind_radii_50_ne': wind_radii_50_ne,
                    'wind_radii_50_se': wind_radii_50_se,
                    'wind_radii_50_sw': wind_radii_50_sw,
                    'wind_radii_50_nw': wind_radii_50_nw,
                    'wind_radii_64_ne': wind_radii_64_ne,
                    'wind_radii_64_se': wind_radii_64_se,
                    'wind_radii_64_sw': wind_radii_64_sw,
                    'wind_radii_64_nw': wind_radii_64_nw,
                    'radius_max_wind': radius_max_wind,
                }

                records.append(record)

            except (ValueError, IndexError) as e:
                print(f"Warning: Could not parse line: {line[:50]}... ({e})")
                continue

    df = pd.DataFrame(records)

    # Convert date to proper datetime
    df['date'] = pd.to_datetime(df['date'])

    return df

def parse_coordinate(coord_str):
    """Parse coordinate string like '28.0N' or '94.8W' to decimal degrees"""
    if not coord_str or coord_str == '-999':
        return None

    # Extract number and direction
    match = re.match(r'([0-9.]+)([NSEW])', coord_str)
    if not match:
        return None

    value = float(match.group(1))
    direction = match.group(2)

    # Convert to signed decimal degrees
    if direction in ['S', 'W']:
        value = -value

    return value

def get_storm_category(status, max_wind):
    """Determine storm category based on status and wind speed"""
    if status == 'HU' and max_wind:
        if max_wind >= 137:
            return 'Cat5'
        elif max_wind >= 113:
            return 'Cat4'
        elif max_wind >= 96:
            return 'Cat3'
        elif max_wind >= 83:
            return 'Cat2'
        elif max_wind >= 64:
            return 'Cat1'
    elif status == 'TS':
        return 'TS'
    elif status == 'TD':
        return 'TD'
    else:
        return status

if __name__ == "__main__":
    # Test the parser
    import sys
    if len(sys.argv) > 1:
        df = parse_hurdat2_file(sys.argv[1])
        print(f"Parsed {len(df)} records from {df['storm_id'].nunique()} storms")
        print(df.head())
