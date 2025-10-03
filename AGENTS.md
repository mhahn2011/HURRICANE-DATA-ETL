# Repository Guidelines

## Project Structure & Module Organization
- `hurdat2/src` contains core ETL modules: `parse_raw.py` for ingest, `profile_clean.py` for validation, `transform_ml.py` for feature engineering.
- `census`, `fema`, and `integration` store complementary pipelines with `input_data/`, `outputs/`, and future `src/` modules; keep sample inputs light and document any new schema in `docs/`.
- Shared helpers live in `shared/` (`data_quality.py`, `spatial_utils.py`); extend these before duplicating utilities.
- Tests sit in `tests/`; integration artifacts belong in `integration/outputs/`; notebooks belong in `hurdat2/notebooks/`.

## Build, Test, and Development Commands
- Set up a virtualenv (`python -m venv .venv && source .venv/bin/activate`) and install deps with `pip install -r requirements.txt`, updating it when libraries change.
- Run unit tests with `pytest` (default `-v --tb=short --strict-markers` via `pytest.ini`).
- Skip long-running suites locally with `pytest -m "not slow"`; include them before merging.
- Recreate outputs via `python hurdat2/src/transform_ml.py` or targeted notebooks when datasets change.

## Coding Style & Naming Conventions
- Use Python 3.11, 4-space indentation, and type-informed docstrings for public functions.
- Name modules and files in snake_case; class names PascalCase; constants UPPER_SNAKE_CASE.
- Prefer pandas/geopandas vectorization; isolate IO boundaries.
- Prefer enriching shared utilities over inline helpers; keep functions under ~50 lines when practical.

## Testing Guidelines
- Write `pytest` tests in `tests/` using `test_<feature>.py`; match fixture names to directory paths.
- Mark resource-heavy cases with `@pytest.mark.slow` or `@pytest.mark.integration`.
- Validate new datasets with assertions on ranges, nulls, and geometry validity; mirror checks found in `profile_clean.py`.
- When adding notebooks, extract critical logic into importable functions and cover them with tests.

## Commit & Pull Request Guidelines
- Use imperative commit subjects (`Implement`, `Fix`, `Rearrange`).
- Keep commits focused on one change set and reference storms or modules in the subject.
- PRs should summarize intent, list data files touched, note required reruns, and include screenshots or CSV diffs for new outputs.
- Link tracking issues and declare outstanding validation steps; request review from module owners (hurdat2, census, fema, integration) as appropriate.

## Data & Security Notes
- Do not commit large or sensitive inputs; store raw feeds under `input_data/` and gitignore bulky files.
- Document external download steps in `docs/` and note API keys or rate limits separately.

## Agent Review Responsibilities
- Serve as the secondary reviewer: surface critical errors, regressions, and data-quality risks before merge.
- Provide actionable reproduction hints and remediation ideas so feature owners iterate quickly toward the goal.
