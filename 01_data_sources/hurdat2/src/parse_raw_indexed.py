"""
Optimized HURDAT2 parser with indexed access for fast individual storm extraction.

Key optimization: Build an index of storm locations on first load, then extract
only the needed lines for specific storms (40-200 lines vs 57,221 total lines).
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional
import json

# Cache file for the index
CACHE_DIR = Path(__file__).parent.parent / "processed"
INDEX_CACHE_FILE = CACHE_DIR / "hurdat2_index.json"


def build_storm_index(file_path: str) -> Dict[str, Tuple[int, int, str]]:
    """
    Build an index of storm locations in the HURDAT2 file.

    Returns:
        Dict mapping storm_id -> (start_line, num_records, storm_name)
    """
    index = {}
    current_line = 0

    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f):
            line = line.strip()
            if not line:
                continue

            # Check if this is a header line
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3 and len(parts) <= 4 and parts[0].startswith('AL') and parts[2].isdigit():
                storm_id = parts[0].strip()
                storm_name = parts[1].strip() if parts[1].strip() else 'UNNAMED'
                num_records = int(parts[2].strip())

                # Store: storm_id -> (header_line_number, num_records, name)
                index[storm_id] = (line_num, num_records, storm_name)

    return index


def save_index(index: Dict, cache_file: Path) -> None:
    """Save index to JSON cache."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(index, f, indent=2)


def load_index(cache_file: Path) -> Optional[Dict]:
    """Load index from JSON cache."""
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            return json.load(f)
    return None


def get_or_build_index(file_path: str, force_rebuild: bool = False) -> Dict[str, Tuple[int, int, str]]:
    """Get cached index or build it if needed."""
    if not force_rebuild:
        cached = load_index(INDEX_CACHE_FILE)
        if cached:
            return cached

    print(f"Building HURDAT2 index (one-time operation)...")
    index = build_storm_index(file_path)
    save_index(index, INDEX_CACHE_FILE)
    print(f"✅ Indexed {len(index)} storms")
    return index


def parse_coordinate(coord_str: str) -> float:
    """Convert HURDAT2 coordinate string to decimal degrees."""
    coord_str = coord_str.strip()
    if coord_str.endswith('N') or coord_str.endswith('E'):
        return float(coord_str[:-1])
    elif coord_str.endswith('S') or coord_str.endswith('W'):
        return -float(coord_str[:-1])
    else:
        return float(coord_str)


def get_storm_category(status: str, max_wind: Optional[int]) -> Optional[int]:
    """Determine Saffir-Simpson category from status and wind speed."""
    if status != 'HU' or max_wind is None:
        return None
    if max_wind >= 137:
        return 5
    elif max_wind >= 113:
        return 4
    elif max_wind >= 96:
        return 3
    elif max_wind >= 83:
        return 2
    elif max_wind >= 64:
        return 1
    return None


def parse_storm_by_id(file_path: str, storm_id: str, index: Optional[Dict] = None) -> pd.DataFrame:
    """
    Extract and parse a single storm by ID using indexed access.

    Args:
        file_path: Path to HURDAT2 file
        storm_id: Storm identifier (e.g., 'AL092021')
        index: Pre-built index (optional, will load/build if None)

    Returns:
        DataFrame with only this storm's track data
    """
    if index is None:
        index = get_or_build_index(file_path)

    if storm_id not in index:
        raise ValueError(f"Storm {storm_id} not found in HURDAT2 data")

    header_line, num_records, storm_name = index[storm_id]

    # Read only the lines we need
    records = []
    with open(file_path, 'r') as f:
        # Skip to the header line
        for _ in range(header_line + 1):
            next(f)

        # Read the storm's data lines
        for _ in range(num_records):
            line = f.readline().strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 7:
                continue

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

                # Parse wind radii
                wind_radii_34_ne = int(parts[8]) if len(parts) > 8 and parts[8] not in {'-999', '0', ''} else None
                wind_radii_34_se = int(parts[9]) if len(parts) > 9 and parts[9] not in {'-999', '0', ''} else None
                wind_radii_34_sw = int(parts[10]) if len(parts) > 10 and parts[10] not in {'-999', '0', ''} else None
                wind_radii_34_nw = int(parts[11]) if len(parts) > 11 and parts[11] not in {'-999', '0', ''} else None

                wind_radii_50_ne = int(parts[12]) if len(parts) > 12 and parts[12] not in {'-999', '0', ''} else None
                wind_radii_50_se = int(parts[13]) if len(parts) > 13 and parts[13] not in {'-999', '0', ''} else None
                wind_radii_50_sw = int(parts[14]) if len(parts) > 14 and parts[14] not in {'-999', '0', ''} else None
                wind_radii_50_nw = int(parts[15]) if len(parts) > 15 and parts[15] not in {'-999', '0', ''} else None

                wind_radii_64_ne = int(parts[16]) if len(parts) > 16 and parts[16] not in {'-999', '0', ''} else None
                wind_radii_64_se = int(parts[17]) if len(parts) > 17 and parts[17] not in {'-999', '0', ''} else None
                wind_radii_64_sw = int(parts[18]) if len(parts) > 18 and parts[18] not in {'-999', '0', ''} else None
                wind_radii_64_nw = int(parts[19]) if len(parts) > 19 and parts[19] not in {'-999', '0', ''} else None

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

                # Determine category
                category = get_storm_category(status, max_wind)

                record = {
                    'storm_id': storm_id,
                    'storm_name': storm_name,
                    'date': date_obj,
                    'record_id': record_id,
                    'status': status,
                    'lat': lat,
                    'lon': lon,
                    'max_wind': max_wind,
                    'min_pressure': min_pressure,
                    'category': category,
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
                # Skip malformed lines
                continue

    return pd.DataFrame(records)


def parse_multiple_storms(file_path: str, storm_ids: list[str]) -> pd.DataFrame:
    """
    Extract and parse multiple storms efficiently.

    Args:
        file_path: Path to HURDAT2 file
        storm_ids: List of storm identifiers

    Returns:
        DataFrame with all requested storms' track data
    """
    index = get_or_build_index(file_path)

    all_records = []
    for storm_id in storm_ids:
        df = parse_storm_by_id(file_path, storm_id, index=index)
        all_records.append(df)

    if not all_records:
        return pd.DataFrame()

    return pd.concat(all_records, ignore_index=True)


if __name__ == "__main__":
    # Test the indexed parser
    import sys
    import time

    hurdat_path = Path(__file__).parent.parent / "raw" / "hurdat2-atlantic.txt"

    print("Testing indexed HURDAT2 parser...")
    print("="*60)

    # Build index
    start = time.time()
    index = get_or_build_index(str(hurdat_path), force_rebuild=True)
    index_time = time.time() - start
    print(f"Index built in {index_time:.2f}s")

    # Test extracting IDA
    print("\nExtracting AL092021 (IDA)...")
    start = time.time()
    df = parse_storm_by_id(str(hurdat_path), "AL092021", index=index)
    extract_time = time.time() - start
    print(f"✅ Extracted {len(df)} records in {extract_time:.3f}s")
    print(f"\nFirst few records:")
    print(df.head())
