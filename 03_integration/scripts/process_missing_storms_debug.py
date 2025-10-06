"""Process the 9 missing storms with detailed logging."""

import pandas as pd
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "03_integration" / "src"))

from feature_pipeline import save_features_for_storm

# Missing storms
MISSING_STORMS = [
    "AL072008",  # GUSTAV
    "AL092008",  # IKE
    "AL092017",  # HARVEY
    "AL092022",  # IAN
    "AL112017",  # IRMA
    "AL132020",  # LAURA
    "AL142018",  # MICHAEL
    "AL262020",  # DELTA
    "AL282020",  # ZETA
]

def main():
    """Process missing storms with timing."""
    ml_ready_dir = REPO_ROOT / "06_outputs" / "ml_ready"
    ml_ready_dir.mkdir(parents=True, exist_ok=True)

    overall_start = time.time()

    for idx, storm_id in enumerate(MISSING_STORMS, 1):
        output_path = ml_ready_dir / f"{storm_id.lower()}_features.csv"

        print(f"\n{'='*60}")
        print(f"[{idx}/9] Processing {storm_id}")
        print(f"{'='*60}")

        storm_start = time.time()

        try:
            print(f"  Starting feature extraction...")
            save_features_for_storm(
                storm_id=storm_id,
                output_path=output_path,
            )
            elapsed = time.time() - storm_start
            print(f"  ✅ Saved to {output_path.name} ({elapsed:.1f}s)")

        except Exception as e:
            elapsed = time.time() - storm_start
            print(f"  ❌ Error after {elapsed:.1f}s: {e}")
            import traceback
            traceback.print_exc()
            continue

    total_elapsed = time.time() - overall_start
    print(f"\n{'='*60}")
    print(f"Total time: {total_elapsed:.1f}s")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
