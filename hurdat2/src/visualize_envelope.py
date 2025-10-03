"""
Hurricane Envelope Visualization with Geographic Context

Creates map-based visualizations of storm envelopes with coastal cities for orientation.
"""
import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd
from shapely.geometry import MultiPolygon, LineString
from pathlib import Path


# Gulf Coast Cities for Reference
GULF_COAST_CITIES = {
    'New Orleans, LA': (-90.0715, 29.9511),
    'Baton Rouge, LA': (-91.1871, 30.4515),
    'Mobile, AL': (-88.0399, 30.6954),
    'Gulfport, MS': (-89.0928, 30.3674),
    'Pensacola, FL': (-87.2169, 30.4213),
    'Biloxi, MS': (-88.8853, 30.3960),
    'Lafayette, LA': (-92.0198, 30.2241),
}


def create_map_visualization(envelope_34kt, envelope_50kt, envelope_64kt, track_line, track_df,
                            output_path=None, title="Hurricane Envelope",
                            focus_gulf_coast=True):
    """
    Create map visualization with 3 envelopes (34kt, 50kt, 64kt), track, coastlines, and cities

    Args:
        envelope_34kt: Shapely Polygon/MultiPolygon for 34kt winds
        envelope_50kt: Shapely Polygon/MultiPolygon for 50kt winds
        envelope_64kt: Shapely Polygon/MultiPolygon for 64kt winds
        track_line: Shapely LineString of track
        track_df: DataFrame with track data (lat, lon, max_wind, date)
        output_path: Path to save PNG (optional)
        title: Plot title
        focus_gulf_coast: If True, limit view to Gulf Coast region (TX to NC)

    Returns:
        matplotlib figure
    """

    fig, ax = plt.subplots(1, 1, figsize=(18, 14))

    # STEP 0: Load and plot basemap (coastlines and state boundaries)
    print("Loading basemap data...")
    try:
        # Load Natural Earth countries (direct URL)
        countries_url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
        countries = gpd.read_file(countries_url)

        # Define Gulf Coast focus region (TX to NC, Gulf of Mexico)
        if focus_gulf_coast:
            # Fixed bounds: Gulf Coast region only
            xlim = (-100, -75)  # Texas to North Carolina longitude
            ylim = (24, 37)     # Gulf of Mexico to North Carolina latitude
            print(f"  Using Gulf Coast focus: Lon {xlim}, Lat {ylim}")
        else:
            # Use envelope bounds with margin (use widest envelope - 34kt)
            bounds = envelope_34kt.bounds
            margin = 5  # degrees
            xlim = (bounds[0] - margin, bounds[2] + margin)
            ylim = (bounds[1] - margin, bounds[3] + margin)

        # Filter countries to map extent
        countries_view = countries.cx[xlim[0]:xlim[1], ylim[0]:ylim[1]]

        # Plot countries
        countries_view.plot(ax=ax, facecolor='lightgray', edgecolor='black',
                           linewidth=0.8, alpha=0.3, zorder=0)

        print("  ✅ Country borders loaded")

        # Load US states
        try:
            states_url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_1_states_provinces.zip"
            states = gpd.read_file(states_url)

            # Filter to US and view extent
            us_states = states[states['admin'] == 'United States of America']
            us_states_view = us_states.cx[xlim[0]:xlim[1], ylim[0]:ylim[1]]

            # Plot state boundaries
            us_states_view.plot(ax=ax, facecolor='none', edgecolor='darkgray',
                               linewidth=1, linestyle='--', alpha=0.6, zorder=0.5)

            print("  ✅ US state boundaries loaded")
        except Exception as e:
            print(f"  ⚠️ Could not load state boundaries: {e}")

    except Exception as e:
        print(f"  ⚠️ Could not load basemap: {e}")
        print("  Continuing without basemap...")

    # STEP 1: Plot all three envelope polygons (34kt, 50kt, 64kt)
    print("Plotting envelopes...")

    # Helper function to plot envelope
    def plot_envelope(envelope, color, label, alpha, zorder):
        if envelope is None:
            return
        if isinstance(envelope, MultiPolygon):
            for i, poly in enumerate(envelope.geoms):
                env_x, env_y = poly.exterior.xy
                if i == 0:
                    ax.fill(env_x, env_y, alpha=alpha, fc=color, ec=color,
                           linewidth=2, label=label, zorder=zorder)
                else:
                    ax.fill(env_x, env_y, alpha=alpha, fc=color, ec=color,
                           linewidth=2, zorder=zorder)
        else:
            env_x, env_y = envelope.exterior.xy
            ax.fill(env_x, env_y, alpha=alpha, fc=color, ec=color,
                   linewidth=2, label=label, zorder=zorder)

    # Plot 34kt envelope (lightest - widest extent)
    plot_envelope(envelope_34kt, 'lightblue', f'34kt winds ({envelope_34kt.area:.1f} sq°)',
                 alpha=0.15, zorder=1)

    # Plot 50kt envelope (medium)
    if envelope_50kt:
        plot_envelope(envelope_50kt, 'cornflowerblue', f'50kt winds ({envelope_50kt.area:.1f} sq°)',
                     alpha=0.20, zorder=1.5)

    # Plot 64kt envelope (darkest - smallest extent)
    if envelope_64kt:
        plot_envelope(envelope_64kt, 'steelblue', f'64kt winds ({envelope_64kt.area:.1f} sq°)',
                     alpha=0.25, zorder=2)

    print(f"  ✅ Envelopes plotted")

    # STEP 2: Filter track to Gulf Coast region only
    print("Filtering track to Gulf Coast region...")
    if focus_gulf_coast:
        # Only show track points within Gulf Coast region
        gulf_mask = (
            (track_df['lon'] >= xlim[0]) & (track_df['lon'] <= xlim[1]) &
            (track_df['lat'] >= ylim[0]) & (track_df['lat'] <= ylim[1])
        )
        track_df_view = track_df[gulf_mask].copy()

        if len(track_df_view) > 0:
            # Create track line from filtered points
            track_coords_view = list(zip(track_df_view['lon'], track_df_view['lat']))
            track_line_view = LineString(track_coords_view) if len(track_coords_view) > 1 else track_line
            print(f"  ✅ Filtered to {len(track_df_view)} Gulf Coast points")
        else:
            track_df_view = track_df
            track_line_view = track_line
            print(f"  ⚠️ No points in Gulf Coast region, showing all")
    else:
        track_df_view = track_df
        track_line_view = track_line

    # STEP 3: Plot New Orleans for geographic reference
    print("Plotting reference city...")
    # Only show New Orleans
    nola_coords = GULF_COAST_CITIES['New Orleans, LA']
    if xlim[0] <= nola_coords[0] <= xlim[1] and ylim[0] <= nola_coords[1] <= ylim[1]:
        ax.plot(nola_coords[0], nola_coords[1], 'ko', markersize=10, zorder=5)
        ax.annotate('New Orleans, LA', xy=nola_coords, xytext=(8, 8),
                   textcoords='offset points', fontsize=11, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.4', facecolor='yellow',
                            edgecolor='black', alpha=0.9, linewidth=1.5),
                   zorder=6)
        print(f"  ✅ New Orleans plotted")
    else:
        print(f"  ⚠️ New Orleans outside map bounds")

    # STEP 4: Plot the hurricane track line
    print("Plotting track line...")
    track_x, track_y = track_line_view.xy
    ax.plot(track_x, track_y, 'r-', linewidth=3, label='Hurricane Track', zorder=3)
    print(f"  ✅ Track line plotted: {len(track_x)} points")

    # STEP 5: Plot track points with wind speed color coding
    print("Plotting track points...")
    wind_speeds = track_df_view['max_wind'].values
    lons = track_df_view['lon'].values
    lats = track_df_view['lat'].values

    scatter = ax.scatter(lons, lats, c=wind_speeds, cmap='YlOrRd', s=120,
                        edgecolors='black', linewidth=1.5, zorder=4,
                        vmin=0, vmax=140)

    # Add colorbar for wind speeds
    cbar = plt.colorbar(scatter, ax=ax, label='Wind Speed (kt)', shrink=0.8)

    # Annotate key points (every 5th point + first/last)
    for i in [0] + list(range(4, len(track_df_view), 5)) + [len(track_df_view)-1]:
        point = track_df_view.iloc[i]
        ax.annotate(f"{int(point['max_wind'])}kt",
                   xy=(point['lon'], point['lat']),
                   xytext=(8, 8), textcoords='offset points',
                   fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                            edgecolor='black', alpha=0.8))
    print(f"  ✅ Track points plotted: {len(lons)} points")

    # STEP 6: Set map extent and formatting
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    # STEP 7: Add grid and formatting
    ax.set_xlabel('Longitude (°W)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Latitude (°N)', fontsize=14, fontweight='bold')
    ax.set_title(title, fontsize=18, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.4, linestyle='--', linewidth=0.5)
    ax.legend(loc='upper right', fontsize=12, framealpha=0.9)

    # Add stats box
    bounds = envelope_34kt.bounds
    geom_type = "MultiPolygon" if isinstance(envelope_34kt, MultiPolygon) else "Polygon"
    area_50kt = f"{envelope_50kt.area:.1f} sq°" if envelope_50kt else "N/A"
    area_64kt = f"{envelope_64kt.area:.1f} sq°" if envelope_64kt else "N/A"
    stats_text = f"""Envelope Statistics:
Type: {geom_type}
34kt Area: {envelope_34kt.area:.1f} sq°
50kt Area: {area_50kt}
64kt Area: {area_64kt}
Track Length: {track_line.length:.2f}°
Points: {len(track_df)}
Max Wind: {track_df['max_wind'].max()} kt
Lat: {bounds[1]:.1f}° to {bounds[3]:.1f}°N
Lon: {bounds[0]:.1f}° to {bounds[2]:.1f}°W"""

    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
           fontsize=11, verticalalignment='top', family='monospace',
           bbox=dict(boxstyle='round', facecolor='wheat', edgecolor='black',
                    alpha=0.95, linewidth=2))

    # Set aspect ratio
    ax.set_aspect('equal', adjustable='box')

    plt.tight_layout()

    # Save to file if path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"\n💾 Saved visualization to: {output_path}")

    return fig


if __name__ == "__main__":
    # Test visualization
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    from parse_raw import parse_hurdat2_file
    from profile_clean import clean_hurdat2_data
    from envelope_algorithm import create_storm_envelope

    print("=" * 60)
    print("HURRICANE IDA 2021: MAP VISUALIZATION")
    print("=" * 60)

    # Load data
    hurdat_file = Path(__file__).parent.parent / "input_data" / "hurdat2-atlantic.txt"
    df_raw = parse_hurdat2_file(hurdat_file)
    df_clean = clean_hurdat2_data(df_raw)

    # Select Hurricane Ida
    ida_track = df_clean[
        df_clean['storm_name'].str.contains('IDA', na=False) &
        (df_clean['year'] == 2021)
    ].sort_values('date').reset_index(drop=True)

    print(f"\nCreating envelope for Hurricane Ida ({len(ida_track)} points)...")
    envelope, track_line, diagnostics = create_storm_envelope(ida_track, verbose=False)

    # Create visualization
    output_file = Path(__file__).parent.parent / "outputs" / "hurricane_ida_map.png"
    fig = create_map_visualization(
        envelope, track_line, ida_track,
        output_path=output_file,
        title="Hurricane Ida 2021: Storm Envelope with Gulf Coast Cities"
    )

    print(f"\n✅ Visualization complete!")
    print(f"   Envelope area: {envelope.area:.2f} sq degrees")
    print(f"   Output: {output_file}")
