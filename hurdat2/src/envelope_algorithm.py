"""
Hurricane Envelope Algorithm - Perpendicular Distance Method

Creates storm envelopes using maximum perpendicular distances from track to wind extent points.
Uses 34kt wind radii (widest extent) for complete track containment.
"""
import math
import pandas as pd
from shapely.geometry import Point, LineString, Polygon


def calculate_slope(lat1, lon1, lat2, lon2):
    """Calculate slope (rise/run) between two lat/lon points"""
    if abs(lon2 - lon1) < 1e-10:  # Avoid division by zero
        return float('inf')  # Vertical line
    return (lat2 - lat1) / (lon2 - lon1)


def calculate_average_slope(i, storm_track):
    """Calculate average track slope through point i using adjacent points"""
    if len(storm_track) < 2:
        return 0  # Default horizontal slope

    # For first point, use only available direction (to next point)
    if i == 0:
        p1 = storm_track.iloc[0]
        p2 = storm_track.iloc[1]
        return calculate_slope(p1['lat'], p1['lon'], p2['lat'], p2['lon'])

    # For last point, use only available direction (from previous point)
    elif i == len(storm_track) - 1:
        p1 = storm_track.iloc[i-1]
        p2 = storm_track.iloc[i]
        return calculate_slope(p1['lat'], p1['lon'], p2['lat'], p2['lon'])

    # For middle points, average the incoming and outgoing slopes
    else:
        p_prev = storm_track.iloc[i-1]
        p_curr = storm_track.iloc[i]
        p_next = storm_track.iloc[i+1]

        # Incoming slope
        slope1 = calculate_slope(p_prev['lat'], p_prev['lon'], p_curr['lat'], p_curr['lon'])
        # Outgoing slope
        slope2 = calculate_slope(p_curr['lat'], p_curr['lon'], p_next['lat'], p_next['lon'])

        # Handle vertical lines (infinite slope)
        if slope1 == float('inf') and slope2 == float('inf'):
            return float('inf')
        elif slope1 == float('inf'):
            return slope2
        elif slope2 == float('inf'):
            return slope1
        else:
            return (slope1 + slope2) / 2


def point_to_line_distance(point_lat, point_lon, line_lat, line_lon, line_slope):
    """Calculate perpendicular distance from point to line defined by point and slope"""
    if line_slope == float('inf'):  # Vertical line
        return abs(point_lon - line_lon)

    a = line_slope
    b = -1
    c = line_lat - line_slope * line_lon

    # Distance formula: |ax + by + c| / sqrt(a² + b²)
    distance = abs(a * point_lon + b * point_lat + c) / math.sqrt(a**2 + b**2)
    return distance


def which_side_of_line(point_lat, point_lon, line_lat, line_lon, track_direction):
    """
    Determine which side of line the point is on (LEFT/RIGHT) using cross product

    Args:
        point_lat, point_lon: Point to classify
        line_lat, line_lon: Point on the track line
        track_direction: Tuple (delta_lon, delta_lat) - the track direction vector

    Returns:
        "LEFT" or "RIGHT" based on cross product sign
    """
    # Vector from line point to the point being classified
    to_point = (point_lon - line_lon, point_lat - line_lat)

    # 2D cross product: direction × to_point
    # If positive, point is to the LEFT of the track direction
    # If negative, point is to the RIGHT of the track direction
    cross_product = track_direction[0] * to_point[1] - track_direction[1] * to_point[0]

    return "LEFT" if cross_product > 0 else "RIGHT"


def nm_to_degrees(nautical_miles, latitude):
    """Convert nautical miles to degrees (lat/lon)"""
    lat_degrees = nautical_miles / 60.0
    lon_degrees = nautical_miles / (60.0 * math.cos(math.radians(latitude)))
    return lat_degrees, lon_degrees


def get_wind_extent_points(track_point, wind_threshold='34kt'):
    """
    Get all 4-directional wind extent points (NE, SE, SW, NW) for a specific wind threshold

    Args:
        track_point: DataFrame row with wind radii data
        wind_threshold: '34kt', '50kt', or '64kt' - which wind threshold to use

    Returns:
        List of extent points with lat/lon/direction/radius/threshold
    """
    lat, lon = track_point['lat'], track_point['lon']
    max_wind = track_point.get('max_wind', 0)

    directions = ['ne', 'se', 'sw', 'nw']
    extent_points = []

    for direction in directions:
        # Get the requested wind threshold radius
        radius = None
        wind_speed_threshold = wind_threshold  # Initialize with requested threshold

        if wind_threshold == '34kt':
            radius = track_point.get(f'wind_radii_34_{direction}', None)
        elif wind_threshold == '50kt':
            radius = track_point.get(f'wind_radii_50_{direction}', None)
        elif wind_threshold == '64kt':
            radius = track_point.get(f'wind_radii_64_{direction}', None)

        # ⭐ FALLBACK: If requested threshold not available, try lower thresholds or estimate
        if radius is None or radius <= 0:
            # Try fallback order: 34kt → 50kt → 64kt → estimated
            for r, thresh in [
                (track_point.get(f'wind_radii_34_{direction}'), '34kt'),
                (track_point.get(f'wind_radii_50_{direction}'), '50kt'),
                (track_point.get(f'wind_radii_64_{direction}'), '64kt')
            ]:
                if r is not None and r > 0:
                    radius = r
                    wind_speed_threshold = f'{thresh}_fallback'
                    break

        # Final fallback: Estimate from wind speed
        if radius is None or radius <= 0:
            if max_wind > 0:
                radius = max_wind * 2.5
                wind_speed_threshold = 'estimated'
            else:
                continue  # Skip this direction if no data at all

        # Convert nautical miles to degrees
        lat_deg, lon_deg = nm_to_degrees(radius, lat)

        # Calculate point based on direction (45° intervals)
        if direction == 'ne':  # Northeast (45°)
            point_lat = lat + (lat_deg * 0.707)
            point_lon = lon + (lon_deg * 0.707)
        elif direction == 'se':  # Southeast (135°)
            point_lat = lat - (lat_deg * 0.707)
            point_lon = lon + (lon_deg * 0.707)
        elif direction == 'sw':  # Southwest (225°)
            point_lat = lat - (lat_deg * 0.707)
            point_lon = lon - (lon_deg * 0.707)
        elif direction == 'nw':  # Northwest (315°)
            point_lat = lat + (lat_deg * 0.707)
            point_lon = lon - (lon_deg * 0.707)

        extent_points.append({
            'lat': point_lat,
            'lon': point_lon,
            'direction': direction,
            'radius': radius,
            'wind_threshold': wind_speed_threshold
        })

    return extent_points


def create_storm_envelope(storm_track, wind_threshold='34kt', verbose=False):
    """
    Create envelope using perpendicular distance method with averaged track slopes

    Args:
        storm_track: DataFrame with columns: lat, lon, wind_radii_34_*, wind_radii_50_*, wind_radii_64_*
        wind_threshold: '34kt', '50kt', or '64kt' - which wind speed threshold to use
        verbose: Print progress messages

    Returns:
        tuple: (envelope_polygon, track_line, diagnostics_df)
    """

    if verbose:
        print(f"Creating perpendicular distance envelope for {len(storm_track)} points...")

    # Create output table for diagnostics
    envelope_data = []
    left_vertices = []
    right_vertices = []
    track_points = []

    for i in range(len(storm_track)):
        point = storm_track.iloc[i]
        lat, lon = point['lat'], point['lon']
        track_center = (lon, lat)
        track_points.append(track_center)

        # Step 1: Calculate track direction vector at this point
        # Use actual track direction (current→next, or previous→current at tail)
        if i < len(storm_track) - 1:
            # Use direction to next point
            next_point = storm_track.iloc[i + 1]
            track_direction = (next_point['lon'] - lon, next_point['lat'] - lat)
        else:
            # At tail, use direction from previous point
            prev_point = storm_track.iloc[i - 1]
            track_direction = (lon - prev_point['lon'], lat - prev_point['lat'])

        # Also calculate slope for perpendicular distance calculation
        track_slope = calculate_average_slope(i, storm_track)

        # Step 2: Get all 4 wind extent points for this track location at specified threshold
        wind_points = get_wind_extent_points(point, wind_threshold=wind_threshold)

        # Step 3: Find maximum perpendicular distance on each side
        max_left_distance = 0
        max_right_distance = 0
        left_detail = None
        right_detail = None

        for wind_point in wind_points:
            # Calculate perpendicular distance from wind point to track line
            perp_dist = point_to_line_distance(
                wind_point['lat'], wind_point['lon'],
                lat, lon, track_slope
            )

            # Determine which side of track line using CROSS PRODUCT with track direction
            side = which_side_of_line(
                wind_point['lat'], wind_point['lon'],
                lat, lon, track_direction
            )

            # Track maximum distance on each side
            if side == "LEFT" and perp_dist > max_left_distance:
                max_left_distance = perp_dist
                left_detail = wind_point
            elif side == "RIGHT" and perp_dist > max_right_distance:
                max_right_distance = perp_dist
                right_detail = wind_point

        # Step 4: Create envelope vertices using max perpendicular distances
        # Calculate perpendicular direction to track slope
        if track_slope == float('inf'):  # Vertical track
            perp_direction_lat = 0
            perp_direction_lon = 1
        else:
            # Perpendicular slope is negative reciprocal
            perp_slope = -1 / track_slope if track_slope != 0 else float('inf')
            # Normalize perpendicular direction vector
            if perp_slope == float('inf'):
                perp_direction_lat = 1
                perp_direction_lon = 0
            else:
                magnitude = math.sqrt(1 + perp_slope**2)
                perp_direction_lat = perp_slope / magnitude
                perp_direction_lon = 1 / magnitude

        # Create vertices at maximum perpendicular distances
        left_vertex_lat = lat + perp_direction_lat * max_left_distance
        left_vertex_lon = lon + perp_direction_lon * max_left_distance

        right_vertex_lat = lat - perp_direction_lat * max_right_distance
        right_vertex_lon = lon - perp_direction_lon * max_right_distance

        left_vertices.append((left_vertex_lon, left_vertex_lat))
        right_vertices.append((right_vertex_lon, right_vertex_lat))

        # Step 5: Store diagnostic information
        envelope_data.append({
            'point_index': i + 1,
            'track_lat': lat,
            'track_lon': lon,
            'track_slope': track_slope if track_slope != float('inf') else 'vertical',
            'wind_points_count': len(wind_points),
            'max_left_distance': max_left_distance,
            'max_right_distance': max_right_distance,
            'left_vertex_lat': left_vertex_lat,
            'left_vertex_lon': left_vertex_lon,
            'right_vertex_lat': right_vertex_lat,
            'right_vertex_lon': right_vertex_lon,
            'left_wind_direction': left_detail['direction'] if left_detail else None,
            'left_wind_radius': left_detail['radius'] if left_detail else None,
            'right_wind_direction': right_detail['direction'] if right_detail else None,
            'right_wind_radius': right_detail['radius'] if right_detail else None,
            'wind_speed': point.get('max_wind', 0)
        })

        # Print progress for key points
        if verbose and (i < 5 or i % 10 == 0):
            wind_speed = point.get('max_wind', 0)
            slope_display = f"{track_slope:.3f}" if track_slope != float('inf') else 'vertical'
            print(f"Point {i+1}: {lat:.1f}°N {lon:.1f}°W, {wind_speed}kt, slope: {slope_display}")
            print(f"  Wind points: {len(wind_points)}, Max L/R distances: {max_left_distance:.3f}, {max_right_distance:.3f}")

    # Step 6: Create envelope polygon - FIXED: Proper vertex ordering to avoid self-intersection
    if len(left_vertices) >= 2 and len(right_vertices) >= 2:
        # Connect vertices to form corridor polygon
        # Strategy: left boundary forward + right boundary backward = closed loop
        envelope_coords = (
            left_vertices +                     # Left boundary (start to end)
            list(reversed(right_vertices))      # Right boundary (end to start)
        )

        envelope_polygon = Polygon(envelope_coords)
        track_line = LineString(track_points)

        if verbose:
            print(f"✅ Perpendicular distance envelope created with {len(envelope_coords)} vertices")
            print(f"   Envelope validity check: {envelope_polygon.is_valid}")

        # If invalid, try to fix with buffer(0) trick
        if not envelope_polygon.is_valid:
            if verbose:
                print("   ⚠️ Invalid geometry detected - attempting auto-fix with buffer(0)...")
            envelope_polygon = envelope_polygon.buffer(0)
            if verbose:
                print(f"   Fixed envelope validity: {envelope_polygon.is_valid}")

        # Create diagnostic DataFrame
        envelope_df = pd.DataFrame(envelope_data)

        return envelope_polygon, track_line, envelope_df
    else:
        if verbose:
            print("❌ Insufficient points for envelope creation")
        return None, LineString(track_points), pd.DataFrame(envelope_data)
