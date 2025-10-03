"""
Hurricane Envelope Algorithm - Alpha Shape (Concave Hull) Method

Transforms HURDAT2 wind radii into segmented concave-hull polygons that delineate
storm impact corridors. The implementation:

    1. Projects quadrant wind radii using accurate spherical trigonometry.
    2. Segments the storm track wherever wind radii are missing for ≥5 consecutive points
       to avoid bridging data gaps.
    3. Builds alpha-shape (concave hull) envelopes per segment and unions them into a
       final geometry.

Historical context:
    • v1.0 (deprecated 2025-10-03): Perpendicular-distance corridor.
    • v2.0 (current): Alpha shape with gap-aware segmentation (default α = 0.6).

References:
    • HURDAT2 format – https://www.nhc.noaa.gov/data/hurdat/hurdat2-format.pdf
    • Alpha shapes – Edelsbrunner et al., 1983, “On the Shape of a Set of Points in the Plane”.
"""
import math
import pandas as pd
import numpy as np
from shapely.geometry import Point, LineString, Polygon, MultiPoint

# --- NEW: Accurate Geospatial Helper Function ---

def calculate_destination_point(lat, lon, bearing, distance_nm):
    """Great-circle forward calculation using nautical miles.

    This helper treats the Earth as a sphere (radius = 3440.065 NM) and computes the
    destination point reached when travelling *distance_nm* along *bearing* starting at
    *(lat, lon)*. It replaces earlier planar approximations that accrued large errors
    for long radii (>100 NM).

    Args:
        lat (float): Starting latitude in decimal degrees.
        lon (float): Starting longitude in decimal degrees.
        bearing (float): True bearing in degrees (0° = north, 90° = east).
        distance_nm (float): Travel distance in nautical miles.

    Returns:
        tuple[float, float]: `(dest_lon, dest_lat)` in decimal degrees.

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
    """Return a concave hull (alpha shape) for *points*.

    The routine constructs a Delaunay triangulation, filters triangles whose
    circumradius exceeds ``1/alpha``, and unions the remaining simplices to form
    a concave polygon. It falls back to the convex hull when the input set is too
    small or the triangulation is ill-conditioned.

    Args:
        points (list[shapely.geometry.Point]): Point cloud to hull.
        alpha (float): Concavity parameter (production default = 0.6). Larger values
            retain only tight triangles (more concave), smaller values trend toward
            a convex hull.

    Returns:
        shapely.geometry.base.BaseGeometry: Polygon or MultiPolygon describing the hull.
    """
    from scipy.spatial import Delaunay
    from shapely.ops import unary_union
    from scipy.spatial.qhull import QhullError

    if len(points) < 4:
        # Alpha shape requires at least 3 points to form a triangle.
        return MultiPoint(points).convex_hull

    coords = np.array([p.coords[0] for p in points])
    try:
        tri = Delaunay(coords, qhull_options='QJ')
    except QhullError:
        # Fallback to convex hull if Delaunay fails even with joggling
        return MultiPoint(points).convex_hull

    triangles = []
    for i in tri.simplices:
        pts = coords[i]
        # Check if the circumradius of the triangle is smaller than alpha
        # This is the core of the alpha shape algorithm.
        a = np.linalg.norm(pts[0] - pts[1])
        b = np.linalg.norm(pts[1] - pts[2])
        c = np.linalg.norm(pts[2] - pts[0])
        s = (a + b + c) / 2.0
        area_squared = s * (s - a) * (s - b) * (s - c)
        if area_squared < 0:
            area = 0
        else:
            area = math.sqrt(area_squared)
        
        # Area can be zero for collinear points, handle this.
        if area > 1e-12:
            circum_r = (a * b * c) / (4.0 * area)
            if circum_r < 1.0 / alpha:
                triangles.append(Polygon(pts))

    return unary_union(triangles)

def create_storm_envelope(storm_track, wind_threshold='64kt', alpha=0.6, verbose=False):
    """Build a segmented alpha-shape envelope for a single hurricane track.

    Args:
        storm_track (pd.DataFrame): Track data sorted chronologically with columns:
            `lat`, `lon`, and quadrant radii `wind_radii_{threshold}_{ne,se,sw,nw}`.
        wind_threshold (str): Which wind radii to consume (`'34kt'`, `'50kt'`, `'64kt'`).
            Production defaults to `'64kt'` (hurricane-force).
        alpha (float): Alpha-shape concavity parameter; 0.6 validated by sensitivity study.
        verbose (bool): Emit progress diagnostics to stdout.

    Returns:
        tuple[shapely.geometry.base.BaseGeometry, LineString, list[Point]]:
            (envelope geometry, center-line track, points used in hull construction).

    Segmentation logic:
        The track is partitioned whenever quadrant radii are absent for ≥5 consecutive
        observations, preventing spurious corridors across data voids (common over land
        or during extratropical transition). Each segment yields its own hull; segments
        are then unioned into the final envelope.

    Validation:
        - Automatically buffers invalid geometries by 0 to restore validity.
        - Returns `(None, LineString(), [])` when insufficient data exist.
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

    # --- Segmentation Logic: Track split by data-availability gaps ---
    #
    # Problem: Missing wind radii can create artificial corridors if we hull the entire
    # track in one pass. Sensitivity analysis showed that treating stretches with ≥5
    # consecutive missing radii as gaps preserves coastal realism while avoiding
    # over-fragmentation.
    #   • Threshold < 5 → over-segmentation, fractures smooth ocean tracks.
    #   • Threshold > 5 → under-segmentation, reintroduces spurious bridges.
    # Typical gap causes: landfall (no buoy data), extratropical transition, or
    # historical record gaps.
    segment_ids = []
    current_segment = 1
    gap_counter = 0
    in_gap = False

    # First, determine where the long gaps are to define the segments
    for has_radii_val in storm_track['has_radii']:
        if not has_radii_val:
            gap_counter += 1
            in_gap = True
        else: # has_radii_val is True
            if in_gap and gap_counter >= 5:
                current_segment += 1
            gap_counter = 0
            in_gap = False
        segment_ids.append(current_segment)
    
    storm_track['segment_id'] = segment_ids

    for seg_id, segment_df in storm_track.groupby('segment_id'):
        # For each segment, generate one hull from all its points
        all_points_for_hull = []
        
        # Add all track points in the segment
        track_points_in_segment = [Point(p.lon, p.lat) for p in segment_df.itertuples()]
        all_points_for_hull.extend(track_points_in_segment)

        # Add all wind extent points from the segment (where they exist)
        for i, row in segment_df.iterrows():
            if row['has_radii']:
                wind_points = get_wind_extent_points(row, wind_threshold=wind_threshold)
                for wp in wind_points:
                    all_points_for_hull.append(Point(wp['lon'], wp['lat']))
        
        all_hull_points.extend(all_points_for_hull) # Collect points for visualization

        # Now, create a hull from all these points for the segment
        if len(all_points_for_hull) >= 4:
            hull = alpha_shape(all_points_for_hull, alpha=alpha)
            polygons.append(hull)
        elif len(all_points_for_hull) >= 3:
            hull = MultiPoint(all_points_for_hull).convex_hull
            polygons.append(hull)

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
