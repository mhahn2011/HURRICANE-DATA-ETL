"""
Hurricane Envelope Algorithm - Perpendicular Distance Method

Creates storm envelopes using maximum perpendicular distances from track to wind extent points.
Uses 34kt wind radii (widest extent) for complete track containment.
"""
import math
import pandas as pd
import numpy as np
from shapely.geometry import Point, LineString, Polygon

# --- NEW: Accurate Geospatial Helper Function ---

def calculate_destination_point(lat, lon, bearing, distance_nm):
    """
    Calculates the destination point given a starting point, bearing, and distance
    using spherical trigonometry.

    Args:
        lat (float): Start latitude in degrees.
        lon (float): Start longitude in degrees.
        bearing (float): Bearing in degrees (0=North, 90=East).
        distance_nm (float): Distance in nautical miles.

    Returns:
        tuple: (destination_lon, destination_lat)
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


def calculate_slope(lat1, lon1, lat2, lon2):
    """Calculate slope (rise/run) between two lat/lon points"""
    if abs(lon2 - lon1) < 1e-10:  # Avoid division by zero
        return float('inf')  # Vertical line
    return (lat2 - lat1) / (lon2 - lon1)


def calculate_average_slope(i, storm_track):
    """Calculate average track slope through point i using adjacent points"""
    if len(storm_track) < 2:
        return 0  # Default horizontal slope

    if i == 0:
        p1 = storm_track.iloc[0]
        p2 = storm_track.iloc[1]
        return calculate_slope(p1['lat'], p1['lon'], p2['lat'], p2['lon'])

    elif i == len(storm_track) - 1:
        p1 = storm_track.iloc[i-1]
        p2 = storm_track.iloc[i]
        return calculate_slope(p1['lat'], p1['lon'], p2['lat'], p2['lon'])

    else:
        p_prev = storm_track.iloc[i-1]
        p_curr = storm_track.iloc[i]
        p_next = storm_track.iloc[i+1]
        slope1 = calculate_slope(p_prev['lat'], p_prev['lon'], p_curr['lat'], p_curr['lon'])
        slope2 = calculate_slope(p_curr['lat'], p_curr['lon'], p_next['lat'], p_next['lon'])
        if slope1 == float('inf') and slope2 == float('inf'):
            return float('inf')
        elif slope1 == float('inf'):
            return slope2
        elif slope2 == float('inf'):
            return slope1
        else:
            return (slope1 + slope2) / 2


def point_to_line_distance(point_lat, point_lon, line_lat, line_lon, track_direction):
    """Calculate perpendicular distance using a track direction vector."""

    dx, dy = track_direction
    px = point_lon - line_lon
    py = point_lat - line_lat

    # If direction is ill-defined, distance collapses to 0
    if dx == 0 and dy == 0:
        return 0.0

    # For unit vectors, |cross| equals perpendicular distance
    cross = dx * py - dy * px
    return abs(cross)


def which_side_of_line(point_lat, point_lon, line_lat, line_lon, track_direction):
    """
    Determine which side of line the point is on (LEFT/RIGHT) using cross product
    """
    to_point = (point_lon - line_lon, point_lat - line_lat)
    cross_product = track_direction[0] * to_point[1] - track_direction[1] * to_point[0]
    if cross_product > 0:
        return "LEFT"
    if cross_product < 0:
        return "RIGHT"
    return "ON"


def nm_to_degrees(nautical_miles, latitude):
    """Convert nautical miles to degrees (lat/lon)"""
    lat_degrees = nautical_miles / 60.0
    lon_degrees = nautical_miles / (60.0 * math.cos(math.radians(latitude)))
    return lat_degrees, lon_degrees

# --- REFACTORED: Use accurate destination calculation ---

def get_wind_extent_points(track_point, wind_threshold='34kt'):
    """
    Get all 4-directional wind extent points using accurate spherical trigonometry.
    """
    lat, lon = track_point['lat'], track_point['lon']
    max_wind = track_point.get('max_wind', 0)
    bearings = {'ne': 45, 'se': 135, 'sw': 225, 'nw': 315}
    extent_points = []

    for direction, bearing in bearings.items():
        radius_col = f'wind_radii_{wind_threshold.replace("kt", "")}_{direction}'
        radius = track_point.get(radius_col, 0)

        if not pd.notna(radius) or radius <= 0:
            continue

        dest_lon, dest_lat = calculate_destination_point(lat, lon, bearing, radius)
        
        extent_points.append({
            'lat': dest_lat,
            'lon': dest_lon,
            'direction': direction,
            'radius': radius,
            'wind_threshold': wind_threshold
        })

    return extent_points


def alpha_shape(points, alpha):
    """
    Computes the alpha shape (concave hull) of a set of points.

    Args:
        points (list of shapely.geometry.Point): The points to compute the hull for.
        alpha (float): The alpha parameter. A smaller value creates a tighter shape.

    Returns:
        shapely.geometry.Polygon or MultiPolygon: The resulting alpha shape.
    """
    from scipy.spatial import Delaunay
    from shapely.ops import unary_union

    if len(points) < 4:
        # Alpha shape requires at least 3 points to form a triangle.
        return MultiPoint(points).convex_hull

    coords = np.array([p.coords[0] for p in points])
    tri = Delaunay(coords)

    triangles = []
    for i in tri.simplices:
        pts = coords[i]
        # Check if the circumradius of the triangle is smaller than alpha
        # This is the core of the alpha shape algorithm.
        a = np.linalg.norm(pts[0] - pts[1])
        b = np.linalg.norm(pts[1] - pts[2])
        c = np.linalg.norm(pts[2] - pts[0])
        s = (a + b + c) / 2.0
        area = math.sqrt(s * (s - a) * (s - b) * (s - c))
        # Area can be zero for collinear points, handle this.
        if area > 1e-12:
            circum_r = (a * b * c) / (4.0 * area)
            if circum_r < 1.0 / alpha:
                triangles.append(Polygon(pts))

    return unary_union(triangles)

def create_storm_envelope(storm_track, wind_threshold='64kt', alpha=0.2, verbose=False):
    """
    Creates a precise storm envelope using a segmented alpha shape approach.
    """
    from shapely.geometry import MultiPoint
    from shapely.ops import unary_union

    if verbose:
        print(f"Creating Segmented Alpha Shape envelope for {len(storm_track)} points...")

    polygons = []
    lines = []
    all_hull_points = [] # To store points for visualization
    radii_cols = [f'wind_radii_{wind_threshold.replace("kt", "")}_{d}' for d in ['ne', 'se', 'sw', 'nw']]

    storm_track['has_radii'] = storm_track[radii_cols].gt(0).any(axis=1)
    storm_track['segment_id'] = (storm_track['has_radii'] != storm_track['has_radii'].shift()).cumsum()

    for seg_id, segment_df in storm_track.groupby('segment_id'):
        is_hull_segment = segment_df['has_radii'].all()
        track_points_in_segment = [Point(p.lon, p.lat) for p in segment_df.itertuples()]

        if is_hull_segment:
            if verbose: print(f"  Processing segment {seg_id} as Alpha Shape ({len(segment_df)} points)")
            all_points_for_hull = list(track_points_in_segment)
            
            for i, row in segment_df.iterrows():
                wind_points = get_wind_extent_points(row, wind_threshold=wind_threshold)
                for wp in wind_points:
                    all_points_for_hull.append(Point(wp['lon'], wp['lat']))
            
            all_hull_points.extend(all_points_for_hull) # Collect points

            if len(all_points_for_hull) >= 4:
                hull = alpha_shape(all_points_for_hull, alpha=alpha)
                polygons.append(hull)
            elif len(all_points_for_hull) >= 3:
                hull = MultiPoint(all_points_for_hull).convex_hull
                polygons.append(hull)
            else:
                lines.append(LineString(track_points_in_segment))
        else:
            if verbose: print(f"  Processing segment {seg_id} as LineString ({len(segment_df)} points)")
            if len(track_points_in_segment) > 1:
                # Buffer the line to create a thin polygon to bridge gaps
                line_bridge = LineString(track_points_in_segment).buffer(0.01)
                polygons.append(line_bridge)

    # Union geometries one by one for robustness
    final_geom = None
    all_geoms = polygons + lines
    for geom in all_geoms:
        if geom is None or geom.is_empty:
            continue
        if final_geom is None:
            final_geom = geom
        else:
            final_geom = final_geom.union(geom)

    if final_geom is None:
        return None, LineString(), [] # Return empty list

    full_track_line = LineString([Point(p.lon, p.lat) for p in storm_track.itertuples()])

    if verbose:
        print(f"✅ Alpha shape envelope created. Validity: {final_geom.is_valid}")

    if not final_geom.is_valid:
        final_geom = final_geom.buffer(0)

    return final_geom, full_track_line, all_hull_points


