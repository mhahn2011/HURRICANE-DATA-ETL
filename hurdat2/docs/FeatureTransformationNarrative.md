# Feature Transformation Narrative

This document describes the data transformations applied to HURDAT2 hurricane track data to create machine learning features for census tract-level storm impact analysis. Each feature is explained in natural language, describing the architectural choices and the reasoning behind the transformation approaches.

---

## Overview: From Raw Tracks to Storm-Tract Features

The transformation pipeline converts HURDAT2's raw hurricane observations—which arrive as 6-hourly snapshots of position, intensity, and wind field geometry—into a comprehensive feature matrix where each row represents one census tract's experience during one hurricane. The core challenge is inferring continuous spatial and temporal exposure from sparse, point-in-time measurements.

The pipeline addresses three fundamental questions:
1. **Where did the storm go?** (Spatial geometry)
2. **What winds did each location experience?** (Intensity interpolation)
3. **For how long?** (Temporal duration)

---

## Feature 1: Storm Envelope Construction

### The Problem

HURDAT2 provides wind radii in four quadrants (NE, SE, SW, NW) at specific intensity thresholds (34kt, 50kt, 64kt) for each track point. These radii describe an asymmetric wind field that changes size and shape as the storm evolves. To efficiently identify which census tracts were impacted, we need a single geometric envelope that encompasses the entire storm corridor without creating artificial coverage areas where the storm never actually reached.

### The Transformation: Alpha Shape with Spherical Trigonometry

The envelope algorithm transforms discrete wind radii measurements into a continuous polygon using a three-stage process:

**Stage 1: Spherical Projection**
Rather than treating wind radii as simple distance offsets on a flat plane (which accumulates large errors over 100+ nautical mile distances), the algorithm uses great-circle navigation mathematics. For each track point, it calculates the exact latitude and longitude reached when traveling along each of the four cardinal quadrant bearings (45°, 135°, 225°, 315°) for the specified radius distance. This treats the Earth as a sphere with radius 3440.065 nautical miles, ensuring that a 50-nautical-mile radius in the NE quadrant lands at the correct geographic coordinates even at high latitudes where longitude lines converge.

The mathematical approach uses the haversine formula's forward variant: given a starting position, bearing, and distance, it computes the destination point's coordinates. This replaces earlier attempts that simply added radii to latitude/longitude as if they were Cartesian coordinates—an approximation that broke down for large radii or when storms moved north-south where meridian convergence is significant.

**Stage 2: Imputation for Partial Data**
HURDAT2 wind radii are often incomplete, especially during early storm stages, over-land segments, or in historical records before 2004 when wind radii weren't systematically recorded. When a track point has some quadrant radii defined but not all four, the algorithm employs proportional imputation. It calculates a "shrinkage ratio" by comparing overlapping quadrants between consecutive time steps—if the NE radius decreased from 60nm to 45nm (ratio 0.75), that same 0.75 ratio is applied to impute missing quadrants at the current step based on their previous values.

This imputation strategy rests on the meteorological reality that adjacent wind field quadrants tend to expand or contract together as a storm intensifies or weakens. The algorithm only imputes when at least two quadrants are observed (providing enough signal to estimate the shrinkage pattern) and tracks a "was_imputed" flag for each value so downstream analyses can distinguish observed from inferred data.

**Stage 3: Segmented Alpha Shape Hull**
With wind extent points calculated for all track positions (observed or imputed), the algorithm constructs a concave hull—specifically an alpha shape—that wraps tightly around the point cloud. An alpha shape is superior to a simple convex hull because it can capture the irregular, curved corridors that hurricanes actually follow. The alpha parameter (set to 0.6 after sensitivity analysis) controls concavity: larger values create tighter, more indented hulls; smaller values trend toward a balloon-like convex boundary.

Critically, the algorithm segments the track wherever wind radii are missing for five or more consecutive observations. This prevents the hull from bridging across data voids—for instance, when a storm makes landfall and transitions extratropical, wind radii often vanish for 6-10 observations. Without segmentation, the alpha shape would draw a corridor across hundreds of miles of land where the storm's organized wind field had actually dissipated. By creating separate hulls for each segment and then unioning them, the envelope respects these natural data boundaries.

### Why This Approach

Earlier iterations used perpendicular distance corridors, measuring how far left and right the wind extent points deviated from the track centerline. This worked for straight-moving storms but failed catastrophically when hurricanes curved (common in the Gulf of Mexico as storms recurve northeast). The perpendicular method created self-intersecting polygons at sharp track bends, invalid geometries that crashed spatial joins.

The alpha shape approach is rotation-invariant—it doesn't care about track direction, only the spatial distribution of wind extent points. It naturally handles loops, sharp turns, and even multiply-connected wind fields (rare but possible when a storm has discontinuous wind radii due to complex structure like concentric eyewalls). The segmentation logic was added after observing that non-segmented alpha shapes occasionally created 50-mile-wide corridors over the Appalachian Mountains where Hurricane Ida's remnants had no hurricane-force winds, simply because the algorithm connected its Louisiana landfall to its later Pennsylvania flooding track.

---

## Feature 2: Distance from Storm Track

### The Problem

Census tract centroids—the representative point for each tract's location—need to be associated with a single distance metric: how far from the hurricane's path was this community? This distance drives many impact correlations (wind damage, surge, rainfall) and serves as a fundamental sorting mechanism for machine learning models.

### The Transformation: Haversine to LineString with Quadrant Context

The distance calculation treats the hurricane track as a LineString (a connected sequence of lat/lon points) and each tract centroid as a Point geometry. Shapely's built-in distance function computes the shortest distance from the point to the line, measured in degrees. This degree distance is then converted to nautical miles using the standard conversion (1 degree of latitude = 60 nautical miles) and to kilometers using Earth's radius.

The algorithm performs this calculation in Euclidean projected space (degrees) rather than great-circle space because the storm track segments are short enough (6-hour intervals, typically 50-100 miles) that planar approximation introduces negligible error—less than 0.1% for segments under 200 miles. For very long, straight track segments, Shapely's distance already uses geodetic-aware calculations when coordinate reference systems are specified.

**Quadrant Enrichment**
Distance alone doesn't capture the asymmetry of hurricane wind fields—being 30 miles northeast of a storm is very different from being 30 miles southwest because wind radii are often double on the right side (northern hemisphere). The algorithm therefore identifies which quadrant (NE/SE/SW/NW) the centroid falls within relative to the nearest track point. It does this by calculating the angular offset (arctan of latitude difference over longitude difference) and binning it into one of the four 90-degree quadrants.

Once the quadrant is known, the algorithm retrieves the 64kt wind radius for that specific quadrant at the nearest track point. This enables a simple but powerful binary flag: `within_64kt` is True if the centroid's distance is less than or equal to the quadrant-specific 64kt radius. This flag effectively answers "was this tract within hurricane-force winds according to the HURDAT2 wind field observations?"

### Why This Approach

Earlier attempts calculated distance to every individual track point and took the minimum, which was computationally expensive (O(n·m) for n tracts and m track points) and produced identical results to LineString distance. The LineString method leverages optimized geometric algorithms that find the closest point on the polyline in logarithmic time.

The quadrant-aware design emerged from validation work showing that using a single "maximum wind radius" (the largest of the four quadrants) produced false positives—tracts 40 miles to the southwest flagged as impacted because the NE radius was 50 miles, even though the SW radius was only 25 miles. The quadrant-specific approach respects the wind field's actual asymmetry as recorded in HURDAT2.

---

## Feature 3: Maximum Wind Speed Experienced

### The Problem

HURDAT2 reports maximum sustained wind at the storm center (`max_wind`) every 6 hours, but a census tract 50 miles away experiences much lower winds due to distance decay. The challenge is to estimate the wind speed at each tract's location, accounting for: (a) the storm's intensity at closest approach, (b) the tract's distance from the storm center, (c) the radius of maximum winds where peak winds occur, and (d) the wind field boundaries defined by the 34/50/64kt radii.

### The Transformation: Hierarchical RMW Plateau with Radii Boundary Enforcement

The wind interpolation algorithm operates in four conceptual zones, prioritizing observed wind radii boundaries over modeled decay:

**Zone 1: Inside the Eyewall (RMW Plateau)**
The radius of maximum winds (RMW) defines the ring around the storm center where winds are strongest—often 10-30 nautical miles from the center for intense hurricanes. Any tract centroid falling within this radius experiences the full interpolated `max_wind` at the time of closest approach, with no decay. This reflects the meteorological reality that winds are roughly constant from the center out to the RMW, then decay beyond it.

For storms in 2021 and later, HURDAT2 includes observed RMW values. For earlier storms, the algorithm estimates RMW based on intensity: Category 3+ storms (≥96kt) default to 20nm, Category 1-2 to 30nm, and tropical storms to 40nm. These defaults are derived from climatological studies showing that more intense storms tend to have tighter, more compact wind fields.

**Zone 2: Between RMW and Wind Radii Boundary (Controlled Decay)**
If a tract lies outside the RMW but inside one of the wind radii quadrilaterals (64kt, 50kt, or 34kt), the algorithm applies linear decay from the maximum wind at the RMW edge down to the threshold of that quadrilateral. For example, a tract 50 miles from the center in the NE quadrant with a 64kt radius of 60 miles would decay from the storm's `max_wind` (say, 110kt) down to 64kt over the 50-60 mile range.

The decay uses the envelope edge as the outer boundary distance. The algorithm shoots a ray from the nearest track point through the centroid until it intersects the envelope boundary, giving the total distance over which decay occurs. The decay fraction is then `(centroid_distance - RMW) / (envelope_edge_distance - RMW)`, and the wind speed becomes `max_wind - decay_fraction * (max_wind - threshold)`.

This approach ensures that tracts near the wind radii boundary receive wind speeds close to the threshold (64kt, 50kt, or 34kt), honoring the observational data that defines these boundaries.

**Zone 3: Outside All Wind Radii (Envelope Decay to 64kt)**
For tracts that fall within the envelope but outside all observed wind radii quadrilaterals (rare, typically happens at envelope edges where data is sparse), the algorithm decays from `max_wind` to 64kt at the envelope boundary. This default assumes the envelope represents at least 64kt-threshold winds, consistent with the envelope being built from 64kt radii.

**Hierarchical Logic Implementation**
The key architectural decision is to check wind radii boundaries first, then apply RMW-based decay within those boundaries. Earlier versions applied RMW decay uniformly and ignored wind radii, leading to inconsistencies where a tract would receive 90kt winds despite being outside all observed wind radii. The current approach treats wind radii as "ground truth" constraints and uses RMW to model intensity variation within those constraints.

A `wind_source` column tracks which method was used for each tract: `rmw_plateau` (inside RMW), `rmw_decay_to_64kt` (64kt zone), `rmw_decay_to_50kt` (50kt zone), `rmw_decay_to_34kt` (34kt zone), or `rmw_decay_to_envelope` (outside all radii). This metadata enables validation and debugging—we can verify that tracts flagged as `within_64kt=True` in the distance calculation also have `wind_source` showing they're in a 64kt zone.

### Why This Approach

Pure distance-based decay (e.g., inverse distance weighting) ignores the observed wind radii that HURDAT2 provides. Using those radii as hard boundaries without RMW produced the opposite problem: a storm with center winds of 120kt but RMW of 15nm would show tracts at 10nm distance experiencing only 64kt if they fell in the 64kt zone, even though they're well inside the eyewall.

The hierarchical approach synthesizes both data sources: wind radii define where winds drop to specific thresholds (observed), RMW defines where peak winds occur (observed when available, estimated otherwise), and linear decay interpolates between these anchor points. This matches the conceptual model meteorologists use: constant winds in the eyewall, rapid decay outside RMW, leveling off at the wind radii thresholds.

---

## Feature 4: Duration of Wind Exposure

### The Problem

HURDAT2 provides snapshots every 6 hours, but a hurricane's wind field is continuously moving. A census tract might experience 64kt winds for 4 hours as the storm passes, but if that 4-hour window falls between two 6-hour observations, the snapshot-based approach would miss it entirely or arbitrarily assign it to one time point. We need to estimate the continuous duration that each tract experienced winds above the 64kt threshold.

### The Transformation: 15-Minute Temporal Interpolation with Wind Field Polygons

The duration algorithm densifies the track temporally and tests envelope membership at each interpolated timestep:

**Stage 1: Temporal Interpolation**
The algorithm interpolates every field in the track DataFrame (latitude, longitude, `max_wind`, and all 12 wind radii quadrant values) to 15-minute intervals. It does this by linearly interpolating between consecutive 6-hour observations. For instance, if the storm moved from (28.5°N, 90.0°W) at 12:00 to (29.0°N, 89.5°W) at 18:00, the 15:00 position is calculated as `start + 0.5 * (end - start)`, yielding (28.75°N, 89.75°W).

Crucially, wind radii are also interpolated. If the NE 64kt radius was 50nm at 12:00 and 60nm at 18:00, the 15:00 value becomes 55nm. This reflects the physical reality that wind fields expand and contract gradually, not in 6-hour jumps.

The 15-minute interval was chosen as a balance between temporal resolution (finer resolution captures brief exposures better) and computational cost (each interval requires building a polygon and testing membership). Sensitivity tests showed that 10-minute intervals changed duration estimates by less than 5% while doubling computation time.

**Stage 2: Instantaneous Wind Field Polygons**
At each 15-minute timestep, the algorithm constructs a wind field polygon using the interpolated wind radii. It calculates the four wind extent points (NE, SE, SW, NW) using the spherical trigonometry function from the envelope algorithm, then creates a polygon from those four points.

A key detail: with only 3-4 points, the polygon can have sharp corners that exclude areas just outside the vertices even though those areas are clearly within the wind field. To address this, the algorithm applies a small buffer (0.02 degrees, approximately 1.3 nautical miles) to round the corners. This buffer creates a more realistic wind field shape—hurricane winds don't drop to zero instantly at the exact NE extent point; there's a gradual tapering.

Edge cases are handled explicitly: if only 1 extent point exists (3 quadrants missing), a circular buffer around that point represents the wind field. If 2 points exist, a LineString connects them with a buffer creating an elliptical field. These cases are rare but occur during storm formation or dissipation when wind fields are asymmetric or incomplete.

**Stage 3: Exposure Timeline Construction**
The algorithm tests whether the tract centroid falls inside each 15-minute wind field polygon, creating a boolean timeline: True when inside, False when outside. This timeline is then analyzed to extract metrics:

- **Total duration**: Count of True values multiplied by 15 minutes (converted to hours)
- **First entry time**: Timestamp of the first True value
- **Last exit time**: Timestamp of the last True value
- **Continuous exposure**: Whether all timesteps between first entry and last exit are True (no gaps)

The continuous exposure flag distinguishes tracts that experienced steady winds (the storm passed directly over or very close) from those that were clipped by the wind field's edge multiple times (in and out as the asymmetric field rotated or pulsed).

**Edge Interpolation for Boundary Tracts**
A subtle issue arises for tracts very close to the envelope edge: the interpolated wind radii might not extend quite far enough to include them at any timestep (yielding 0 duration), even though they're clearly within the overall envelope polygon. This happens because the 15-minute wind polygons are conservative (built from 4 points only), while the envelope is an alpha shape hull over all points.

For tracts with 0 duration but inside the envelope, the algorithm applies a distance-based interpolation. It measures how far the centroid is from the envelope boundary and linearly scales from a maximum possible duration (the time span of complete wind radii data) down to 0 at the boundary. A tract 0.05° from the edge might get 1 hour duration; one 0.18° from the edge (close to the 0.2° buffer threshold) gets near-zero duration.

This edge interpolation prevents sharp discontinuities where a tract 1 mile inside the envelope gets 3 hours duration while one 1 mile outside gets 0, when both are essentially at the periphery of the wind field.

### Why This Approach

Simpler approaches were considered: using only the two closest 6-hour observations (interpolating just those two) or testing envelope membership once at the time of closest approach. The first approach missed tracts that were inside the wind field for only 2-3 hours between observations. The second approach ignored temporal variation entirely—a tract might be close to the track but the storm was moving so fast it only experienced winds for 45 minutes, which the single-timestep method couldn't capture.

The 15-minute interpolation provides temporal granularity that matches typical storm passage timescales. Hurricanes move at 10-30 mph in the Gulf; a storm moving at 15 mph covers 3.75 miles in 15 minutes, meaning consecutive polygons overlap significantly but shift enough to capture the wind field's progression. This granularity is fine enough to distinguish a 2-hour exposure from a 4-hour exposure—a difference that matters for structural damage modeling.

Building polygons at each timestep rather than interpolating distance-to-track leverages the quadrant asymmetry: a tract 40 miles west might be in the wind field at some times and out at others as the wind radii rotate and the strong quadrant shifts from NE to NW as the storm curves. Distance-based methods would miss this dynamic.

---

## Feature 5: Lead Time to Category Thresholds (Planned)

### The Problem

Emergency managers need to know how much advance warning a community received before experiencing maximum winds. A tract that had 24 hours from when the storm became a hurricane to when it experienced peak winds has very different preparedness capacity than one with only 6 hours. However, not all storms reach high categories (many Gulf storms make landfall as Category 1-2), so lead time to "Category 4" would be undefined for most events.

### The Transformation: Multi-Threshold Lead Time Calculation (Design)

The planned implementation calculates five separate lead time features, one for each Saffir-Simpson category:

**Stage 1: Threshold Crossing Detection**
For each intensity threshold (Cat 1 = 64kt, Cat 2 = 83kt, Cat 3 = 96kt, Cat 4 = 113kt, Cat 5 = 137kt), the algorithm scans the chronologically sorted track to find the first timestamp where `max_wind` meets or exceeds that threshold. This is the "threshold crossing time."

If the storm never reaches a category (e.g., many storms never exceed 95kt, so no Cat 3 crossing), that threshold's lead time is set to NaN rather than 0 or negative infinity. This allows models to distinguish "no warning because storm was weak" from "2 hours warning because storm intensified rapidly."

**Stage 2: Closest Approach Time**
The algorithm identifies when the storm came closest to the tract centroid. This is found by calculating the distance from centroid to track at each 6-hour observation and taking the timestamp of minimum distance. For tracts very close to the track, this is typically when the eye or center passes nearest.

**Stage 3: Lead Time Arithmetic**
Lead time for each category is simply `closest_approach_time - threshold_crossing_time`, converted to hours. Positive values indicate advance warning (storm reached Cat 3 twelve hours before closest approach). Negative values indicate the storm intensified after passing (rare but occurs when tracts are in the forward quadrants and the storm intensifies downstream).

Zero lead time means the storm reached that intensity exactly at closest approach—physically implausible due to 6-hour observation intervals, but possible after interpolation.

**Stage 4: Categorical Analysis**
With five lead time features, models can capture non-linear relationships: perhaps damage severity correlates most strongly with Cat 3 lead time (onset of major hurricane winds) regardless of whether the storm later reached Cat 5. Or perhaps Cat 1 lead time drives evacuation rates (first hurricane watch issuance) while Cat 4 lead time is irrelevant for storms that only reached Cat 2.

The multi-threshold approach also enables "intensification rate" proxies. A storm with Cat 1 lead time of 30 hours but Cat 4 lead time of only 6 hours intensified rapidly (24 hours to jump 3 categories), which has different preparedness implications than a storm with 28-hour Cat 4 lead time (slow, steady intensification).

### Why This Approach

Single-threshold lead time (e.g., only Cat 4) fails for 70% of Gulf storms that never reach Cat 4. Using "maximum intensity" threshold creates a moving target—impossible to calculate until the storm is over, useless for real-time forecasting.

The five-threshold design mirrors how emergency management operates: hurricane watches trigger at Cat 1 potential, different building codes activate at Cat 3, extreme measures (hospital evacuation) engage at Cat 4+. Each threshold has operational meaning, so giving models access to all five as separate features lets them learn which thresholds drive which impacts.

This approach also handles extratropical transition gracefully. If a storm reaches Cat 2, makes landfall, then weakens to tropical storm before transitioning, Cat 1 and Cat 2 lead times are well-defined, but Cat 3/4/5 are NaN. Models can learn that "NaN Cat 4 lead time" is informative—it signals a weaker event class.

---

## Architectural Patterns Across Features

Several design principles recur across the feature transformations:

**Spherical Geometry Fidelity**
All distance and direction calculations use great-circle mathematics when distances exceed ~50 nautical miles. Within that range, planar approximations are acceptable (< 1% error), but for 100+ mile wind radii or long track segments, spherical trigonometry is essential. The Earth's curvature is not negligible at hurricane scales.

**Temporal Densification**
Sparse 6-hour observations are interpolated to finer resolutions (15 minutes for duration, effectively continuous for wind speed via closest-point-on-line). This reflects the physical reality that storms don't teleport—they move continuously, and communities experience gradual wind increases and decreases, not instantaneous jumps every 6 hours.

**Hierarchical Boundary Enforcement**
When multiple data sources provide overlapping information (wind radii + RMW, envelope + individual wind fields), the transformations prioritize observed boundaries over modeled decay. Wind radii are measurements; RMW fills in detail within those boundaries. The envelope constrains duration calculations; 15-minute polygons add temporal precision within that envelope.

**Edge Case Explicitness**
Rather than letting missing data propagate NaNs through calculations, each transformation has explicit logic for edge cases: single-point wind fields get buffered, zero-duration boundary tracts get distance-based interpolation, storms that never reach Cat 4 get NaN (not 0) lead time. These choices ensure that missing or extreme values carry semantic meaning rather than representing calculation failures.

**Validation Metadata**
Features include companion columns that track methodology: `wind_source` shows which decay model was used, `was_imputed` flags estimated wind radii, `continuous_exposure` indicates whether duration was uninterrupted. This metadata enables validation (checking that methods were applied correctly) and could serve as features themselves (perhaps imputed wind radii correlate with higher uncertainty in damage predictions).

---

## Integration: The Complete Pipeline

The feature transformations execute in dependency order:

1. **Envelope construction** creates the spatial domain, determining which tracts are potentially impacted
2. **Distance calculation** provides the fundamental metric (how far?) and quadrant context
3. **Wind interpolation** estimates intensity (how strong?) using distance, quadrant, and temporal position
4. **Duration calculation** estimates exposure time (how long?) using temporal interpolation within the envelope
5. **Lead time calculation** estimates warning time (how much notice?) using intensity thresholds and approach timing

Each stage consumes outputs from previous stages: wind interpolation uses the envelope from stage 1 and distance from stage 2; duration uses the envelope and temporal track from stage 1. This pipeline architecture ensures that expensive calculations (envelope construction) happen once and their results propagate through all downstream features.

The final output is a feature matrix with 24+ columns per storm-tract pair: identifiers (tract FIPS, storm ID), spatial metrics (distance, quadrant), intensity metrics (max wind experienced, center wind, RMW), temporal metrics (duration, entry/exit times, continuous exposure flag), and warning metrics (5 category lead times). This matrix serves as input to machine learning models that predict damage, evacuation rates, or recovery timelines—the transformations have converted raw meteorological observations into decision-relevant exposure features.
