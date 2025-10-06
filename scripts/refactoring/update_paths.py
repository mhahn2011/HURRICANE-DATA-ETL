#!/usr/bin/env python3
"""
Automatically update hardcoded legacy paths to new structure paths.

This script performs a safe find-and-replace of old paths with new paths
across all Python files in the repository.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Repository root
REPO_ROOT = Path("/Users/Michael/hurricane-data-etl")

# Path mappings (old → new)
PATH_MAPPINGS: Dict[str, str] = {
    # Data source paths
    'hurdat2/input_data': '01_data_sources/hurdat2/raw',
    'hurdat2/outputs/cleaned_data': '01_data_sources/hurdat2/processed',
    'hurdat2/outputs/qa_maps': '01_data_sources/hurdat2/visuals/html',
    'hurdat2/outputs/envelopes': '02_transformations/wind_coverage_envelope/outputs',
    'hurdat2/outputs': '01_data_sources/hurdat2/processed',  # Generic fallback
    'hurdat2/src': '01_data_sources/hurdat2/src',

    'census/input_data': '01_data_sources/census/raw',
    'census/outputs': '01_data_sources/census/processed',
    'census/src': '01_data_sources/census/src',

    # Transformation paths
    'hurdat2_census/outputs/transformations': '02_transformations/storm_tract_distance/visuals/results/html',
    'hurdat2_census/outputs/features': '02_transformations/storm_tract_distance/outputs',
    'hurdat2_census/outputs': '02_transformations/storm_tract_distance/outputs',
    'hurdat2_census/src': '02_transformations/storm_tract_distance/src',

    # Integration paths
    'integration/outputs/results': '03_integration/visuals/results/html',
    'integration/outputs/ml_ready': '03_integration/outputs/ml_ready',
    'integration/outputs': '03_integration/outputs',
    'integration/src': '03_integration/src',
}

# Import statement mappings
IMPORT_MAPPINGS: Dict[str, str] = {
    'from hurdat2.src': 'from _legacy_data_sources.hurdat2.src',
    'from census.src': 'from _legacy_data_sources.census.src',
    'from hurdat2_census.src': 'from _legacy_data_sources.hurdat2_census.src',
    'import hurdat2.': 'import _legacy_data_sources.hurdat2.',
    'import census.': 'import _legacy_data_sources.census.',
    'import hurdat2_census.': 'import _legacy_data_sources.hurdat2_census.',
}


def find_python_files() -> List[Path]:
    """Find all Python files in new structure folders."""
    python_files = []
    for folder in ["01_data_sources", "02_transformations", "03_integration", "04_src_shared", "05_tests"]:
        folder_path = REPO_ROOT / folder
        if folder_path.exists():
            python_files.extend(folder_path.rglob("*.py"))
    return python_files


def update_file_paths(file_path: Path, dry_run: bool = True) -> Tuple[int, List[str]]:
    """
    Update legacy paths in a single file.

    Args:
        file_path: Path to the Python file
        dry_run: If True, only report changes without writing

    Returns:
        Tuple of (num_changes, list_of_changes)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        updated_content = original_content
        changes = []

        # Sort mappings by length (longest first) to avoid partial replacements
        sorted_mappings = sorted(PATH_MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True)

        # Update file path strings
        for old_path, new_path in sorted_mappings:
            # Match paths in strings (both single and double quotes)
            patterns = [
                (f'"{old_path}', f'"{new_path}'),
                (f"'{old_path}", f"'{new_path}"),
                (f'"{old_path}/', f'"{new_path}/'),
                (f"'{old_path}/", f"'{new_path}/"),
            ]

            for old_pattern, new_pattern in patterns:
                if old_pattern in updated_content:
                    count = updated_content.count(old_pattern)
                    updated_content = updated_content.replace(old_pattern, new_pattern)
                    if count > 0:
                        changes.append(f"  → Replaced '{old_pattern}' with '{new_pattern}' ({count} occurrences)")

        # Update import statements (commented out for now - these need more careful handling)
        # for old_import, new_import in IMPORT_MAPPINGS.items():
        #     if old_import in updated_content:
        #         count = updated_content.count(old_import)
        #         updated_content = updated_content.replace(old_import, new_import)
        #         changes.append(f"  → Updated import: {old_import} → {new_import} ({count} times)")

        # Write changes if not dry run
        if changes and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

        return len(changes), changes

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, []


def main():
    """Main update function."""
    import argparse

    parser = argparse.ArgumentParser(description="Update legacy paths to new structure")
    parser.add_argument('--dry-run', action='store_true', help='Show changes without writing')
    parser.add_argument('--apply', action='store_true', help='Apply changes to files')
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Please specify either --dry-run or --apply")
        return

    dry_run = args.dry_run

    print("=" * 80)
    print("PATH UPDATE SCRIPT")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'APPLY CHANGES'}")
    print("=" * 80)

    # Find all Python files
    python_files = find_python_files()
    print(f"\nFound {len(python_files)} Python files to process")

    # Process each file
    total_changes = 0
    files_updated = 0

    for py_file in sorted(python_files):
        relative_path = py_file.relative_to(REPO_ROOT)
        num_changes, changes = update_file_paths(py_file, dry_run=dry_run)

        if changes:
            files_updated += 1
            total_changes += num_changes
            print(f"\n📄 {relative_path}")
            for change in changes:
                print(change)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files scanned: {len(python_files)}")
    print(f"Files with changes: {files_updated}")
    print(f"Total replacements: {total_changes}")

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No files were modified")
        print("Run with --apply to actually update files")
    else:
        print("\n✅ Files have been updated!")
        print("Review changes with 'git diff' before committing")

    print("=" * 80)


if __name__ == "__main__":
    main()
