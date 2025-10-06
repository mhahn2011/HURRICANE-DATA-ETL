"""Process the 9 missing storms and create combined output."""

import pandas as pd
from pathlib import Path
import sys

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
    """Process missing storms."""
    ml_ready_dir = REPO_ROOT / "06_outputs" / "ml_ready"
    ml_ready_dir.mkdir(parents=True, exist_ok=True)

    for storm_id in MISSING_STORMS:
        output_path = ml_ready_dir / f"{storm_id.lower()}_features.csv"

        print(f"\n{'='*60}")
        print(f"Processing {storm_id}")
        print(f"{'='*60}")

        try:
            save_features_for_storm(
                storm_id=storm_id,
                output_path=output_path,
            )
            print(f"✅ Saved to {output_path}")
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

if __name__ == "__main__":
    main()
