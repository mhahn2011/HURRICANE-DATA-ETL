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
from typing import Iterable, List, Tuple

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


# Bearings defining each quadrant arc (degrees). NW wraps beyond 360 to maintain
# monotonically increasing bearings around the storm centre.
QUADRANT_BEARING_RANGES: dict = {
    "ne": (45.0, 135.0),
    "se": (135.0, 225.0),
    "sw": (225.0, 315.0),
    "nw": (315.0, 405.0),
}


def generate_quadrant_arc_points(
    lat: float,
    lon: float,
    quadrant: str,
    radius_nm: float,
    *,
    num_points: int = 30,
    include_endpoint: bool = True,
) -> List[Tuple[float, float]]:
    """Sample evenly spaced arc points for a quadrant wind radius.

    Args:
        lat: Storm centre latitude (degrees).
        lon: Storm centre longitude (degrees).
        quadrant: Quadrant label (``'ne'``, ``'se'``, ``'sw'``, ``'nw'``).
        radius_nm: Radius length in nautical miles.
        num_points: Number of samples along the arc (defaults to 30).
        include_endpoint: Whether to include the final bearing in the sampling.

    Returns:
        List of ``(lon, lat)`` coordinate tuples tracing the quadrant arc. Returns an
        empty list when the radius is missing or non-positive.
    """

    if not quadrant or quadrant not in QUADRANT_BEARING_RANGES:
        raise ValueError(f"Unsupported quadrant '{quadrant}'")

    if not pd.notna(radius_nm) or radius_nm <= 0:
        return []

    # Ensure at least two samples so downstream code can form a LineString when
    # only one quadrant is available.
    sample_count = max(2, int(num_points))

    start_bearing, end_bearing = QUADRANT_BEARING_RANGES[quadrant]
    bearings = np.linspace(start_bearing, end_bearing, sample_count, endpoint=include_endpoint)

    points: List[Tuple[float, float]] = []
    for bearing in bearings:
        dest_lon, dest_lat = calculate_destination_point(lat, lon, bearing % 360.0, radius_nm)
        points.append((dest_lon, dest_lat))

    return points


def identify_imputable_segments(storm_track: pd.DataFrame, wind_threshold: str = "64kt") -> pd.Series:
    """Return boolean mask marking rows eligible for proportional radii imputation."""

    quadrants = ["ne", "se", "sw", "nw"]
    prefix = wind_threshold.replace("kt", "")
    radii_cols = [f"wind_radii_{prefix}_{quad}" for quad in quadrants]

    mask = pd.Series(False, index=storm_track.index)
    for position, idx in enumerate(storm_track.index):
        current_vals = storm_track.loc[idx, radii_cols]
        current_defined = current_vals.notna() & (current_vals > 0)
        defined_count = int(current_defined.sum())

        if defined_count == len(quadrants):
            continue  # fully observed, no imputation required

        prev_defined_count = 0
        if position > 0:
            prev_idx = storm_track.index[position - 1]
            prev_vals = storm_track.loc[prev_idx, radii_cols]
            prev_defined = prev_vals.notna() & (prev_vals > 0)
            prev_defined_count = int(prev_defined.sum())

        imputable = False
        if defined_count >= 2:
            imputable = True
        elif prev_defined_count >= 2:
            imputable = True

        mask.iloc[position] = imputable

    return mask


def impute_missing_wind_radii(storm_track: pd.DataFrame, wind_threshold: str = "64kt") -> pd.DataFrame:
    """Return copy of ``storm_track`` with proportional imputation for missing quadrants."""

    if storm_track.empty:
        return storm_track.copy()

    track = storm_track.copy().reset_index(drop=True)

    quadrants = ["ne", "se", "sw", "nw"]
    prefix = wind_threshold.replace("kt", "")
    base_cols = [f"wind_radii_{prefix}_{quad}" for quad in quadrants]
    imputed_cols = [f"{col}_imputed" for col in base_cols]
    flag_cols = [f"{col}_was_imputed" for col in base_cols]
    ratio_col = f"wind_radii_{prefix}_shrinkage_ratio"

    for base_col, imputed_col, flag_col in zip(base_cols, imputed_cols, flag_cols):
        track[imputed_col] = track[base_col]
        track[flag_col] = False

    track[ratio_col] = np.nan
    track[f"wind_radii_{prefix}_any_imputed"] = False

    imputable_mask = identify_imputable_segments(track, wind_threshold=wind_threshold).reset_index(drop=True)

    last_known_ratio: float | None = 1.0
    index_list = track.index.tolist()

    for position, idx in enumerate(index_list):
        prev_idx = index_list[position - 1] if position > 0 else None

        current_vals = track.loc[idx, base_cols]
        defined_mask = current_vals.notna() & (current_vals > 0)
        defined_count = int(defined_mask.sum())

        applied_ratio: float | None = None

        # Update shrinkage ratio whenever overlapping quadrants exist with previous step
        if prev_idx is not None:
            ratios: List[float] = []
            for base_col, imputed_col in zip(base_cols, imputed_cols):
                current_val = track.at[idx, base_col]
                prev_val = track.at[prev_idx, imputed_col]
                if (
                    pd.notna(current_val)
                    and pd.notna(prev_val)
                    and float(prev_val) > 0
                ):
                    ratios.append(float(current_val) / float(prev_val))

            if ratios:
                applied_ratio = float(np.mean(ratios))
                applied_ratio = max(applied_ratio, 0.0)
                last_known_ratio = applied_ratio

        # Store ratio (either newly computed or carry forward last known)
        if applied_ratio is not None:
            track.at[idx, ratio_col] = applied_ratio
        elif last_known_ratio is not None:
            track.at[idx, ratio_col] = last_known_ratio

        # Determine whether we should attempt imputation at this row
        if not imputable_mask.iloc[position]:
            continue

        if defined_count >= 2 and applied_ratio is None and last_known_ratio is not None:
            applied_ratio = last_known_ratio

        if defined_count < 2:
            applied_ratio = applied_ratio if applied_ratio is not None else last_known_ratio

        if applied_ratio is None or prev_idx is None:
            continue  # insufficient information to impute

        row_imputed = False
        for base_col, imputed_col, flag_col in zip(base_cols, imputed_cols, flag_cols):
            current_val = track.at[idx, base_col]
            if pd.notna(current_val) and current_val > 0:
                continue  # observed value already present

            prev_val = track.at[prev_idx, imputed_col]
            if pd.isna(prev_val):
                continue

            if float(prev_val) <= 0:
                imputed_value = 0.0
            else:
                imputed_value = float(prev_val) * float(applied_ratio)
                if imputed_value < 0:
                    imputed_value = 0.0

            track.at[idx, imputed_col] = imputed_value
            track.at[idx, flag_col] = True
            row_imputed = True

        if row_imputed:
            track.at[idx, f"wind_radii_{prefix}_any_imputed"] = True
            if applied_ratio is not None:
                last_known_ratio = applied_ratio

    return track


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

def get_wind_extent_points(track_point, wind_threshold='34kt', samples_per_quadrant: int = 30):
    """Return sampled wind-extent points along each quadrant arc.

    The legacy implementation returned a single point per quadrant which formed a
    diamond-like polygon. Sampling along the true circular arcs produces a point
    cloud that more faithfully represents the HURDAT2 specification and dramatically
    reduces envelope underestimation.
    """
    lat, lon = track_point['lat'], track_point['lon']
    extent_points = []

    prefix = wind_threshold.replace("kt", "")

    for direction in ('ne', 'se', 'sw', 'nw'):
        radius_col = f"wind_radii_{prefix}_{direction}"
        imputed_col = f"{radius_col}_imputed"
        flag_col = f"{radius_col}_was_imputed"

        radius = track_point.get(imputed_col, np.nan)
        was_imputed = bool(track_point.get(flag_col, False))

        if not pd.notna(radius) or radius <= 0:
            radius = track_point.get(radius_col, np.nan)
            was_imputed = False

        if not pd.notna(radius) or radius <= 0:
            continue

        arc_points = generate_quadrant_arc_points(
            lat,
            lon,
            direction,
            radius,
            num_points=samples_per_quadrant,
            include_endpoint=True,
        )

        for idx, (dest_lon, dest_lat) in enumerate(arc_points):
            extent_points.append(
                {
                    'lat': dest_lat,
                    'lon': dest_lon,
                    'direction': direction,
                    'radius': radius,
                    'wind_threshold': wind_threshold,
                    'was_imputed': was_imputed,
                    'bearing_index': idx,
                    'samples_per_quadrant': samples_per_quadrant,
                    'point_type': 'arc_sample',
                }
            )

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

    polygons: List[Polygon] = []
    lines: List[LineString] = []
    all_hull_points = []  # To store points for visualization

    prefix = wind_threshold.replace("kt", "")
    radii_cols = [f"wind_radii_{prefix}_{d}" for d in ['ne', 'se', 'sw', 'nw']]
    imputed_cols = [f"{col}_imputed" for col in radii_cols]

    working_track = impute_missing_wind_radii(storm_track, wind_threshold=wind_threshold)

    working_track['has_radii_observed'] = working_track[radii_cols].gt(0).any(axis=1)
    working_track['has_radii'] = working_track[imputed_cols].fillna(0).gt(0).any(axis=1)
    working_track['imputation_begins'] = working_track[f"wind_radii_{prefix}_any_imputed"].fillna(False)

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
    for has_radii_val in working_track['has_radii']:
        if not has_radii_val:
            gap_counter += 1
            in_gap = True
        else: # has_radii_val is True
            if in_gap and gap_counter >= 5:
                current_segment += 1
            gap_counter = 0
            in_gap = False
        segment_ids.append(current_segment)
    
    working_track['segment_id'] = segment_ids

    for seg_id, segment_df in working_track.groupby('segment_id'):
        # For each segment, generate one hull from all its points
        all_points_for_hull = []
        
        # Add all track points in the segment
        track_points_in_segment = [Point(p.lon, p.lat) for p in segment_df.itertuples()]
        all_points_for_hull.extend(track_points_in_segment)

        # Add all wind extent points from the segment (where they exist)
        for _, row in segment_df.iterrows():
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

    full_track_line = LineString([Point(p.lon, p.lat) for p in working_track.itertuples()])

    if verbose:
        print(f"✅ Alpha shape envelope created. Validity: {final_geom.is_valid}")

    if not final_geom.is_valid:
        final_geom = final_geom.buffer(0)

    return final_geom, full_track_line, all_hull_points
