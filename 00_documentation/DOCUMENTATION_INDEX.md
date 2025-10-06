# Documentation Index

**Last Updated:** 2025-10-06
**Quick Start:** See [REPOSITORY_GUIDE.md](./REPOSITORY_GUIDE.md)

---

## Primary Documentation (Read These)

### 1. [REPOSITORY_GUIDE.md](./REPOSITORY_GUIDE.md) ⭐ START HERE
**Purpose:** Comprehensive repository guide

**Includes:**
- Quick start commands
- Complete structure overview
- Design philosophy explained
- Common tasks with examples
- Contributing guidelines
- Architecture details
- Migration history

**Who should read:** Everyone (new developers, contributors, maintainers)

---

### 2. [FEATURE_METHODOLOGY.md](./FEATURE_METHODOLOGY.md)
**Purpose:** Algorithm documentation

**Includes:**
- Wind interpolation model (RMW plateau + decay)
- Duration calculation (15-min interpolation)
- Lead time detection (category thresholds)
- Alpha shape envelope construction
- Mathematical formulas and validation

**Who should read:** Those implementing features, writing papers, validating results

---

### 3. [ML_TOOLS_OVERVIEW.md](./ML_TOOLS_OVERVIEW.md)
**Purpose:** Explanation of MLflow, DVC, Hydra

**Includes:**
- What each tool does
- When to use them
- Integration examples
- Pros/cons for this project
- Quick start guides

**Who should read:** Those considering experiment tracking, data versioning, config management

---

## Quick References

### 4. [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md)
**Status:** Quick reference (detailed info in REPOSITORY_GUIDE.md)

**Purpose:** Fast lookup of folder structure

**Who should read:** Quick reference when you forget what `02_transformations/` contains

---

### 5. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
**Purpose:** Command cheat sheet

**Who should read:** Quick copy-paste of common commands

---

### 6. [VISUALIZATION_GUIDE.md](./VISUALIZATION_GUIDE.md)
**Purpose:** Guide to generated visualizations

**Includes:**
- What each HTML map shows
- How to interpret colors/legends
- Where visualizations are saved

**Who should read:** Those doing QA/QC, creating presentations, debugging

---

## Implementation Plans

### 7. [00_plans/MIGRATION_PLAN.md](../00_plans/MIGRATION_PLAN.md) 🔧
**Status:** Ready for execution

**Purpose:** Complete migration from legacy to numbered structure

**Includes:**
- File-by-file changes needed
- Step-by-step execution plan
- Import path updates
- Output path consolidation
- Test verification steps
- Rollback plan

**Who should read:** Maintainers executing migration

---

### 8. [00_plans/DASHBOARD_DEPLOYMENT_PLAN.md](../00_plans/DASHBOARD_DEPLOYMENT_PLAN.md)
**Status:** Phase 1 complete (Ida features generated)

**Purpose:** Steps to deploy Streamlit dashboard

**Who should read:** Those working on dashboard functionality

---

## Specialized Guides

### 9. [README.md](./README.md)
**Purpose:** Original project README

**Note:** May be outdated, see REPOSITORY_GUIDE.md for current info

---

### 10. [project_readme.md](./project_readme.md)
**Purpose:** Alternative project overview

---

### 11. [simple_hurdat_setup.md](./simple_hurdat_setup.md)
**Purpose:** Quick HURDAT2 data setup

---

## Archived Documentation

### [archive/pre-migration-2025-10-06/](./archive/pre-migration-2025-10-06/)

**Contains:**
- `REPOSITORY_ORGANIZATION_ANALYSIS.md` - Migration analysis
- `DOCUMENTATION_REFACTORING_RECOMMENDATIONS.md` - Old refactor plan
- `DESIGN_PHILOSOPHY_ASSESSMENT.md` - Design evaluation

**Purpose:** Historical record of migration planning

**Who should read:** Only if researching project evolution or decision rationale

**See:** `archive/pre-migration-2025-10-06/README.md` for details

---

## Document Status Legend

| Symbol | Meaning |
|--------|---------|
| ⭐ | Primary documentation - start here |
| 🔧 | Active implementation plan |
| ✅ | Complete and current |
| ⚠️ | Partial or outdated - see newer version |
| 📦 | Archived - historical reference only |

---

## Documentation by Audience

### New Team Members
1. [REPOSITORY_GUIDE.md](./REPOSITORY_GUIDE.md) - Understand structure
2. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Common commands
3. [FEATURE_METHODOLOGY.md](./FEATURE_METHODOLOGY.md) - Understand algorithms

### Feature Developers
1. [REPOSITORY_GUIDE.md](./REPOSITORY_GUIDE.md) - See "Contributing" section
2. [FEATURE_METHODOLOGY.md](./FEATURE_METHODOLOGY.md) - Algorithm details
3. `05_tests/README.md` - Testing guidelines

### Maintainers
1. [00_plans/MIGRATION_PLAN.md](../00_plans/MIGRATION_PLAN.md) - Execute migration
2. [REPOSITORY_GUIDE.md](./REPOSITORY_GUIDE.md) - Architecture details
3. [archive/](./archive/) - Historical context

### Data Scientists (Using Outputs)
1. [FEATURE_METHODOLOGY.md](./FEATURE_METHODOLOGY.md) - Feature definitions
2. [VISUALIZATION_GUIDE.md](./VISUALIZATION_GUIDE.md) - QA/QC interpretation
3. [ML_TOOLS_OVERVIEW.md](./ML_TOOLS_OVERVIEW.md) - Experiment tracking

---

## Quick Navigation

**I want to...**

- **Get started** → [REPOSITORY_GUIDE.md](./REPOSITORY_GUIDE.md)
- **Understand the code structure** → [REPOSITORY_GUIDE.md](./REPOSITORY_GUIDE.md) (Structure section)
- **Run a command** → [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
- **Understand an algorithm** → [FEATURE_METHODOLOGY.md](./FEATURE_METHODOLOGY.md)
- **Add a new feature** → [REPOSITORY_GUIDE.md](./REPOSITORY_GUIDE.md) (Contributing section)
- **Execute migration** → [00_plans/MIGRATION_PLAN.md](../00_plans/MIGRATION_PLAN.md)
- **Use MLflow/DVC** → [ML_TOOLS_OVERVIEW.md](./ML_TOOLS_OVERVIEW.md)
- **Interpret visualizations** → [VISUALIZATION_GUIDE.md](./VISUALIZATION_GUIDE.md)
- **Understand history** → [archive/](./archive/)

---

## Maintenance Guidelines

### Adding New Documentation

**Where to put it:**
- General guide content → Update [REPOSITORY_GUIDE.md](./REPOSITORY_GUIDE.md)
- New algorithm → Update [FEATURE_METHODOLOGY.md](./FEATURE_METHODOLOGY.md)
- Implementation plan → Create in `00_plans/`
- Quick command → Add to [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)

**Don't create new docs unless:**
- Topic too specialized for existing docs
- Would make existing docs too long (>500 lines)
- Completely separate concern

### Archiving Old Documentation

**When to archive:**
- Content superseded by newer doc
- Information consolidated elsewhere
- Historical interest only

**How to archive:**
```bash
mkdir -p 00_documentation/archive/{date}-{reason}/
mv outdated_doc.md 00_documentation/archive/{date}-{reason}/
# Create README.md explaining what was archived and why
```

### Updating This Index

**When to update:**
- New primary doc created
- Doc archived
- Major restructure

**What to update:**
- Add new doc to appropriate section
- Update status symbols
- Add to "Quick Navigation"
- Update "Documentation by Audience"

---

## Summary

**Primary docs:**
- [REPOSITORY_GUIDE.md](./REPOSITORY_GUIDE.md) ⭐ - Everything about the repo
- [FEATURE_METHODOLOGY.md](./FEATURE_METHODOLOGY.md) - Algorithm details
- [ML_TOOLS_OVERVIEW.md](./ML_TOOLS_OVERVIEW.md) - Tool explanations

**Execution plans:**
- [00_plans/MIGRATION_PLAN.md](../00_plans/MIGRATION_PLAN.md) 🔧 - Migration steps
- [00_plans/DASHBOARD_DEPLOYMENT_PLAN.md](../00_plans/DASHBOARD_DEPLOYMENT_PLAN.md) - Dashboard setup

**Everything else:** Quick references or archived

**Start reading:** [REPOSITORY_GUIDE.md](./REPOSITORY_GUIDE.md)
