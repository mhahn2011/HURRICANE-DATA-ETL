# Hurricane Data ETL Pipeline

**Transform historical hurricane data into machine learning features for damage prediction**

## Project Overview

This repository processes HURDAT2 Atlantic hurricane data (1851-2024) into census tract-level features for hurricane damage modeling. The core innovation is the **Max Distance Envelope Approach** - an efficient method for calculating wind exposure at specific geographic locations using asymmetric hurricane wind fields.

**Key Output**: CSV where each row represents one hurricane's impact on one census tract, with wind speeds, exposure duration, and spatial relationship features.

---

## Document Guide & Usage

### **🚀 Start Here: Implementation**

#### **[HURDAT2 to ML Features Workflow](link-to-workflow)**
**Purpose**: Complete technical methodology and step-by-step implementation guide
**Use When**: Beginning development, understanding the envelope approach, structuring your code
**Key Sections**:
- Max Distance Envelope methodology (core algorithm)
- 7-section Jupyter notebook structure (22 progressive cells)
- Wind speed interpolation and duration calculations
- Feature engineering specifications

**For Cloud Code**: This document provides the complete technical roadmap for implementation.

---

### **📊 Data Reference**

#### **[HURDAT2 Data Schema & Field Definitions](link-to-schema)**
**Purpose**: Complete data dictionary for the HURDAT2 hurricane database
**Use When**: Writing parsing code, understanding field meanings, handling missing data
**Key Sections**:
- 21-field data line structure with units and ranges
- Storm status codes (TD/TS/HU) and record identifiers
- Wind radii interpretation (quadrant-based wind extents)
- Data quality eras (1979+, 2004+, 2021+)

**For Cloud Code**: Essential reference when parsing raw HURDAT2 format and validating data.

---

### **⚙️ Project Setup**

#### **[Hurricane Data ETL Repository Setup](link-to-setup)**
**Purpose**: Directory structure, dependencies, and development workflow
**Use When**: Setting up the repository, installing dependencies, organizing code
**Key Sections**:
- Multi-source folder structure (hurdat2/, fema/, census/, integration/)
- Python requirements (pandas, geopandas, shapely, ydata-profiling)
- Git workflow and file organization
- Shared utilities for spatial calculations

**For Cloud Code**: Provides the foundation for organizing code and understanding project structure.

---

### **📚 Strategic Context** *(Reference Only)*

#### **[Existing Machine Learning Hurricane Impact Models](link-to-models)**
**Purpose**: Academic research context and competitive landscape
**Use When**: Understanding how this work fits into existing research, writing papers/documentation
**Key Value**: Validates that your approach (economic loss prediction, census tract resolution, Random Forest) aligns with academic best practices

#### **[Hurricane Risk Modeling Data Sources](link-to-sources)**
**Purpose**: Catalog of available hurricane-related datasets
**Use When**: Planning future data integration (FEMA damage, Census demographics, NOAA surge)
**Key Value**: Roadmap for expanding beyond HURDAT2 to multi-source feature engineering

---

## Implementation Quick Start

### **Immediate Next Steps**
1. **Repository Setup**: Use the structure from "Repository Setup" document
2. **Data Understanding**: Review "Data Schema" for HURDAT2 format details  
3. **Begin Development**: Follow the 7-section notebook structure in "Workflow" document
4. **Start with Hurricane Ida**: Use as test case for envelope algorithm development

### **Development Approach**
```bash
# 1. Set up environment
pip install -r requirements.txt

# 2. Create notebook following workflow structure
jupyter notebook hurdat2/notebooks/hurdat2_to_features.ipynb

# 3. Implement progressively (22 cells in 7 sections)
# Section 1: Data acquisition & parsing
# Section 2: Data profiling  
# Section 3: Single storm envelope (Hurricane Ida test)
# Section 4: Census tract integration
# Section 5: Wind speed calculations
# Section 6: Scale to multiple storms
# Section 7: Export & validation
```

---

## Key Innovations

### **1. Max Distance Envelope Approach**
- **Problem**: Traditional methods assume circular wind fields or require complex modeling
- **Solution**: Use HURDAT2's 4-directional wind radii to create realistic storm footprint polygons
- **Benefit**: Computationally efficient while capturing asymmetric wind field geometry

### **2. Duration-Based Features**
- **Innovation**: Calculate time spent in different wind speed zones, not just peak winds
- **Hypothesis**: Sustained battering more predictive of damage than brief peak winds
- **Implementation**: Count 6-hour intervals above wind speed thresholds

### **3. Census Tract Granularity**
- **Advantage**: Higher resolution than county-level analysis
- **Challenge**: Massive data expansion (1 storm → thousands of tract rows)
- **Solution**: Spatial pre-filtering using envelope polygons for efficiency

---

## Technical Architecture

### **Data Flow**
```
Raw HURDAT2 Text → Clean DataFrame → Storm Envelopes → Tract Filtering → Wind Calculations → ML Features
```

### **Core Algorithm: Envelope Creation**
1. **Storm Path**: Connect hurricane track points into polyline
2. **Wind Extents**: Convert 4-directional radii to lat/lon coordinates  
3. **Envelope Boundary**: Find maximum perpendicular distances on each side of path
4. **Polygon Creation**: Combine boundaries into storm footprint polygon
5. **Spatial Filter**: Test which census tracts fall within polygon
6. **Wind Assignment**: Interpolate wind speeds based on distance to track

### **Output Schema**
Each row = one hurricane's impact on one census tract:
- **Identifiers**: tract_id, storm_id, storm_name, year
- **Wind Impact**: max_wind_experienced, exposure_duration_hours, distance_to_track
- **Timing**: time_of_peak_winds, exposure_start, exposure_end
- **Context**: storm_max_intensity, landfall_flag, approach_bearing

---

## Development Philosophy

### **Progressive Complexity**
Start simple, add sophistication incrementally:
1. **Single storm** (Hurricane Ida) → **Multiple storms**
2. **Basic wind assignment** → **Duration and timing features**
3. **HURDAT2 only** → **Multi-source integration**

### **Validation-Driven**
Each notebook section includes validation:
- Geometric validity checks (polygon creation)
- Data range validation (wind speeds 64-200 knots)
- Spatial consistency (tract locations, storm tracks)
- Temporal logic (exposure duration calculations)

### **Documentation Through Code**
The Jupyter notebook serves as both implementation and documentation - each cell tells part of the development story while building toward the final feature matrix.

---

## Future Expansion

This HURDAT2 foundation enables integration with additional data sources:
- **FEMA damage assessments** → Target variables for ML models
- **Census demographics** → Social vulnerability features
- **NOAA storm surge** → Coastal flooding impact features
- **Building inventory** → Infrastructure exposure features

The consistent ETL pattern (parse → profile → transform) scales to additional data sources while maintaining the census tract granularity and envelope-based spatial analysis approach.