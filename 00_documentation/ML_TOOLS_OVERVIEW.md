# ML Tools Overview: MLflow, DVC, and Hydra

**Purpose:** Explanation of industry-standard ML workflow tools

---

## Quick Summary

| Tool | Purpose | Analogy |
|------|---------|---------|
| **DVC** | Version control for data & models | Git for datasets |
| **MLflow** | Experiment tracking & model registry | Lab notebook for ML |
| **Hydra** | Configuration management | Settings manager for experiments |

---

## 1. DVC (Data Version Control)

### What It Does
Tracks large data files and ML models using Git-like commands, without storing the actual files in Git.

### The Problem It Solves
**Without DVC:**
```bash
# Your repo
hurricane-data-etl/
├── data/
│   └── storm_data.csv  # 5 GB - can't commit to Git!
├── models/
│   └── predictor.pkl   # 200 MB - too large for Git!
```

**Git problems:**
- Can't track large files (GitHub limit: 100 MB)
- No way to version datasets
- Hard to reproduce experiments with old data

**With DVC:**
```bash
# Track data like Git tracks code
dvc add data/storm_data.csv
git add data/storm_data.csv.dvc  # Tiny metadata file
git commit -m "Add storm data v1"

# Later, get exact data version
git checkout old-commit
dvc pull  # Downloads data matching that commit
```

### How It Works
1. DVC stores data in cloud storage (S3, Google Cloud, Azure)
2. Git tracks tiny `.dvc` files (metadata pointers)
3. `dvc pull` downloads data, `dvc push` uploads it

### Example Use Case (Your Project)
```bash
# Track HURDAT2 data
dvc add hurdat2/input_data/hurdat2-atlantic.txt
dvc remote add -d myremote s3://my-bucket/hurricane-data

# Track generated features
dvc add integration/outputs/storm_tract_features.csv

# Push to cloud
dvc push

# Colleague can reproduce:
git clone <repo>
dvc pull  # Gets exact data you used
python integration/src/feature_pipeline.py  # Reproduces results
```

### Key Commands
```bash
dvc init              # Set up DVC in repo
dvc add <file>        # Track a data file
dvc push              # Upload data to remote storage
dvc pull              # Download data from remote
dvc repro             # Reproduce pipeline
```

### Benefits for Your Project
- **Reproducibility:** Anyone can get exact HURDAT2 version you used
- **Collaboration:** Share 5GB datasets without email
- **Versioning:** Track feature engineering changes alongside code
- **Space Saving:** Don't store large CSVs in Git

**Website:** https://dvc.org

---

## 2. MLflow

### What It Does
Tracks ML experiments (parameters, metrics, artifacts) and manages model lifecycle.

### The Problem It Solves
**Without MLflow:**
```python
# Experiment 1
max_wind_threshold = 64
alpha = 0.6
# ...run pipeline...
# Accuracy: 0.82
# Where did I save this? Was it alpha=0.6 or 0.5?

# Experiment 2
max_wind_threshold = 50
alpha = 0.7
# ...run pipeline...
# Accuracy: 0.79
# Wait, which settings gave 0.82 again? 🤔
```

**With MLflow:**
```python
import mlflow

mlflow.start_run()
mlflow.log_param("max_wind_threshold", 64)
mlflow.log_param("alpha", 0.6)
mlflow.log_metric("accuracy", 0.82)
mlflow.log_artifact("outputs/predictions.csv")
mlflow.end_run()

# Later: Browse all experiments in web UI
# See: "Run #47 with alpha=0.6 got accuracy=0.82"
```

### Key Features

#### 1. Experiment Tracking
Automatically logs:
- **Parameters:** alpha, wind_threshold, census_year
- **Metrics:** RMSE, MAE, tract_count
- **Artifacts:** CSVs, plots, model files
- **Code Version:** Git commit hash

#### 2. Model Registry
```python
# Register best model
mlflow.sklearn.log_model(model, "hurricane_predictor")

# Later: Load exact model
model = mlflow.sklearn.load_model("models:/hurricane_predictor/Production")
```

#### 3. Comparison UI
Web interface shows:
```
Experiment: Hurricane Feature Extraction
─────────────────────────────────────────
Run     Alpha   Threshold   Tracts   Duration
#47     0.6     64kt        563      4.2hrs   ← Best
#48     0.7     64kt        612      3.8hrs
#49     0.5     64kt        498      4.7hrs
```

### Example Use Case (Your Project)
```python
# In feature_pipeline.py
import mlflow

mlflow.set_experiment("hurricane_features")

with mlflow.start_run(run_name=f"ida_{storm_id}"):
    # Log parameters
    mlflow.log_param("alpha", 0.6)
    mlflow.log_param("wind_threshold", "64kt")
    mlflow.log_param("census_year", 2019)

    # Run pipeline
    features = extract_all_features_for_storm(storm_id)

    # Log metrics
    mlflow.log_metric("tract_count", len(features))
    mlflow.log_metric("mean_duration", features['duration'].mean())
    mlflow.log_metric("max_wind", features['max_wind'].max())

    # Log output
    mlflow.log_artifact("integration/outputs/ida_features.csv")

# View results: http://localhost:5000
```

### Key Commands
```bash
mlflow ui                    # Start web UI
mlflow run .                 # Run MLproject
mlflow models serve -m <model>  # Deploy model as API
```

### Benefits for Your Project
- **Compare:** Test alpha=0.5 vs 0.6 vs 0.7, see which is best
- **Reproduce:** "What settings gave 563 tracts for Ida?"
- **Audit:** "Which Git commit generated this CSV?"
- **Deploy:** Serve wind prediction model as REST API

**Website:** https://mlflow.org

---

## 3. Hydra

### What It Does
Manages configuration files and makes it easy to override parameters from command line.

### The Problem It Solves
**Without Hydra:**
```python
# Hardcoded parameters scattered in code
def extract_features(storm_id):
    alpha = 0.6  # Hardcoded!
    census_year = 2019  # Hardcoded!
    wind_threshold = '64kt'  # Hardcoded!

# To change alpha, edit code and risk forgetting to change back
```

**With Hydra:**
```yaml
# config.yaml
alpha: 0.6
census_year: 2019
wind_threshold: '64kt'
storm_id: AL092021
```

```python
# feature_pipeline.py
import hydra
from omegaconf import DictConfig

@hydra.main(config_path="configs", config_name="config")
def extract_features(cfg: DictConfig):
    alpha = cfg.alpha  # From YAML
    storm_id = cfg.storm_id
    # ...
```

```bash
# Run with defaults
python feature_pipeline.py

# Override from command line
python feature_pipeline.py alpha=0.7 storm_id=AL012005

# Use different config file
python feature_pipeline.py --config-name=production
```

### Key Features

#### 1. Configuration Composition
```yaml
# configs/data/hurdat2.yaml
source: hurdat2
path: hurdat2/input_data/hurdat2-atlantic.txt

# configs/data/census.yaml
source: census
year: 2019
states: [22, 28, 48, 01, 12]

# configs/config.yaml
defaults:
  - data: hurdat2  # Include hurdat2 config

alpha: 0.6
```

#### 2. Multi-Run (Sweep Parameters)
```bash
# Run with multiple alphas
python feature_pipeline.py -m alpha=0.5,0.6,0.7

# Runs 3 experiments:
# - alpha=0.5
# - alpha=0.6
# - alpha=0.7
```

#### 3. Type Safety
```python
from dataclasses import dataclass
from hydra.core.config_store import ConfigStore

@dataclass
class Config:
    alpha: float
    census_year: int
    storm_id: str

# Hydra validates types!
python feature_pipeline.py alpha="hello"  # Error: not a float
```

### Example Use Case (Your Project)

**Current (without Hydra):**
```python
# integration/src/feature_pipeline.py
def extract_all_features_for_storm(
    storm_id: str,
    hurdat_data_path: str = "hurdat2/input_data/hurdat2-atlantic.txt",
    census_year: int = 2019,
    gulf_states: list = ['22', '28', '48', '01', '12'],
    bounds_margin: float = 3.0,
):
    # Lots of parameters!
```

```bash
# Hard to override
python feature_pipeline.py AL092021 --census-year 2020 --bounds-margin 5.0
```

**With Hydra:**
```yaml
# configs/config.yaml
storm_id: AL092021
hurdat_data_path: hurdat2/input_data/hurdat2-atlantic.txt
census_year: 2019
gulf_states: [22, 28, 48, 01, 12]
bounds_margin: 3.0
```

```python
# integration/src/feature_pipeline.py
import hydra
from omegaconf import DictConfig

@hydra.main(config_path="../configs", config_name="config", version_base=None)
def main(cfg: DictConfig):
    features = extract_all_features_for_storm(
        storm_id=cfg.storm_id,
        hurdat_data_path=cfg.hurdat_data_path,
        census_year=cfg.census_year,
        gulf_states=cfg.gulf_states,
        bounds_margin=cfg.bounds_margin,
    )
```

```bash
# Easy to override
python feature_pipeline.py census_year=2020 bounds_margin=5.0

# Multi-run
python feature_pipeline.py -m bounds_margin=2.0,3.0,4.0 storm_id=AL092021,AL012005
```

### Key Commands
```bash
# Run with config
python app.py

# Override parameters
python app.py param1=value1 param2=value2

# Multi-run (parameter sweep)
python app.py -m param=1,2,3

# Use different config
python app.py --config-name=production
```

### Benefits for Your Project
- **Flexibility:** Test different parameters without editing code
- **Organization:** All settings in YAML, not scattered in code
- **Sweeps:** Easily run experiments with multiple alpha values
- **Reproducibility:** Config file shows exact settings used
- **Validation:** Catches type errors before running

**Website:** https://hydra.cc

---

## How They Work Together

### Typical ML Workflow with All Three

```bash
# 1. Hydra manages configuration
python feature_pipeline.py \
  alpha=0.6 \
  storm_id=AL092021 \
  census_year=2019

# 2. MLflow tracks the experiment
# (automatically logs Hydra config)
# Logs: alpha=0.6, storm_id=AL092021, duration_mean=4.2

# 3. DVC versions the output
dvc add integration/outputs/ida_features.csv
git add integration/outputs/ida_features.csv.dvc
git commit -m "Extract Ida features with alpha=0.6"
dvc push
```

### Example: Parameter Sweep

```bash
# Run 9 experiments (3 alphas × 3 storms)
python feature_pipeline.py -m \
  alpha=0.5,0.6,0.7 \
  storm_id=AL092021,AL012005,AL092017

# Hydra: Runs all combinations
# MLflow: Tracks each run's metrics
# DVC: Versions all outputs

# Later: View MLflow UI to see which alpha performed best
mlflow ui
```

---

## Quick Comparison

| Feature | DVC | MLflow | Hydra |
|---------|-----|--------|-------|
| **Purpose** | Data versioning | Experiment tracking | Config management |
| **Tracks** | Data files, models | Params, metrics, code | Settings, parameters |
| **Storage** | Cloud (S3, GCS) | Local or server | YAML files in Git |
| **UI** | CLI only | Web dashboard | CLI only |
| **Learning Curve** | Medium | Easy | Medium |
| **Integration** | Works with any code | Python, R, Java | Python (mainly) |

---

## Should You Use Them?

### Your Current Project Scale

**Current:**
- 14 storms
- Single pipeline
- 1-2 developers
- Manual parameter tuning

**Recommendation:**

| Tool | Priority | Reasoning |
|------|----------|-----------|
| **Hydra** | 🟡 Optional | Nice for parameter sweeps, but argparse works fine for now |
| **MLflow** | 🟢 **Recommended** | Would help compare alpha values, track which settings work best |
| **DVC** | 🔴 Not Yet | Only if you have data >100MB or need to share large files |

### When to Adopt

**MLflow** - Adopt when:
- Testing multiple parameter combinations
- Need to compare experiment results
- Want to track "best" model version
- **Effort:** 2-3 hours to integrate

**Hydra** - Adopt when:
- Running many parameter sweeps
- Config files getting complex
- Need to maintain multiple environments (dev/prod)
- **Effort:** 3-4 hours to migrate from argparse

**DVC** - Adopt when:
- Data files >100 MB
- Multiple people need same datasets
- Need to version data alongside code
- **Effort:** 1-2 hours initial setup

---

## Simple Example: MLflow for Your Project

**Minimal integration (~30 minutes):**

```python
# integration/src/feature_pipeline.py
import mlflow

def main():
    args = _parse_cli_args()

    # Start tracking
    with mlflow.start_run(run_name=f"extract_{args.storm_id}"):
        # Log what you're doing
        mlflow.log_param("storm_id", args.storm_id)
        mlflow.log_param("census_year", args.census_year)
        mlflow.log_param("bounds_margin", args.bounds_margin)

        # Run pipeline
        features = extract_all_features_for_storm(...)

        # Log results
        mlflow.log_metric("tract_count", len(features))
        mlflow.log_metric("mean_duration", features['duration_in_envelope_hours'].mean())
        mlflow.log_artifact(str(output_path))

        print(f"✅ Tracked in MLflow: http://localhost:5000")
```

```bash
# View results
mlflow ui
# Open http://localhost:5000
```

---

## Summary

**MLflow, DVC, and Hydra are NOT required**, but they solve common ML problems:

- **DVC:** "How do I version 5GB datasets?" → Git for data
- **MLflow:** "Which alpha value worked best?" → Experiment tracker
- **Hydra:** "How do I test 10 parameter combos?" → Config manager

**For your current project:**
- ✅ MLflow would be useful for comparing alpha/threshold experiments
- 🟡 Hydra optional but nice for parameter sweeps
- ❌ DVC not needed yet (data <100MB, single developer)

**Industry standard:** Most production ML teams use all three together.

---

## Learn More

- **MLflow Tutorial:** https://mlflow.org/docs/latest/quickstart.html
- **DVC Tutorial:** https://dvc.org/doc/start
- **Hydra Tutorial:** https://hydra.cc/docs/intro/

**Try MLflow first** - easiest to integrate and immediate value for experiment tracking.
