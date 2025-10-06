"""
Shared Geometry Utilities

Common geospatial calculations used across transformations.
All functions use WGS84 (EPSG:4326) coordinates.
"""
import math
from typing import Tuple


def calculate_destination_point(lat: float, lon: float, bearing: float, distance_nm: float) -> Tuple[float, float]:
    """Great-circle forward calculation using nautical miles.

    Treats Earth as a sphere (radius = 3440.065 NM) and computes the
    destination point reached when travelling distance_nm along bearing.

    Args:
        lat: Starting latitude in decimal degrees
        lon: Starting longitude in decimal degrees
        bearing: True bearing in degrees (0° = north, 90° = east)
        distance_nm: Travel distance in nautical miles

    Returns:
        tuple: (dest_lon, dest_lat) in decimal degrees

    Example:
        >>> calculate_destination_point(29.0, -90.0, 45, 50)
        (-89.409..., 29.589...)
    """
    R_NM = 3440.065  # Earth radius in nautical miles

    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing)

    angular_distance = distance_nm / R_NM

    dest_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance) +
        math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
    )

    dest_lon_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(dest_lat_rad)
    )

    return (math.degrees(dest_lon_rad), math.degrees(dest_lat_rad))


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points.

    Args:
        lat1, lon1: First point coordinates in decimal degrees
        lat2, lon2: Second point coordinates in decimal degrees

    Returns:
        float: Distance in nautical miles
    """
    R_NM = 3440.065  # Earth radius in nautical miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R_NM * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate initial bearing from point 1 to point 2.

    Args:
        lat1, lon1: Starting point coordinates in decimal degrees
        lat2, lon2: Ending point coordinates in decimal degrees

    Returns:
        float: Initial bearing in degrees (0-360)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))

    bearing_rad = math.atan2(x, y)
    bearing_deg = math.degrees(bearing_rad)

    return (bearing_deg + 360) % 360
