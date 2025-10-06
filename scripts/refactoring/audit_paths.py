#!/usr/bin/env python3
"""
Audit all hardcoded paths in Python scripts to identify migration issues.

Compares:
1. Paths referenced in scripts (imports, file I/O)
2. Actual directory structure (old vs new)
3. Generates mapping report for updating
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Repository root
REPO_ROOT = Path("/Users/Michael/hurricane-data-etl")

# Old structure folders (now in _legacy_data_sources)
OLD_FOLDERS = ["hurdat2", "census", "hurdat2_census", "fema"]

# New structure folders
NEW_FOLDERS = ["01_data_sources", "02_transformations", "03_integration", "04_src_shared", "05_tests"]


def find_all_python_files():
    """Find all Python files in the repository."""
    python_files = []
    for folder in NEW_FOLDERS:
        folder_path = REPO_ROOT / folder
        if folder_path.exists():
            python_files.extend(folder_path.rglob("*.py"))
    return python_files


def extract_path_references(file_path):
    """Extract all path references from a Python file."""
    references = {
        'imports': [],
        'file_paths': [],
        'output_dirs': []
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

            # Find import statements
            import_patterns = [
                r'from (hurdat2|census|hurdat2_census|fema)\.[\w.]+',
                r'import (hurdat2|census|hurdat2_census|fema)',
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                references['imports'].extend(matches)

            # Find file path strings (quoted)
            path_patterns = [
                r'"([^"]*(?:hurdat2|census|hurdat2_census|fema|integration|data_sources|transformations)[^"]*)"',
                r"'([^']*(?:hurdat2|census|hurdat2_census|fema|integration|data_sources|transformations)[^']*)'",
            ]
            for pattern in path_patterns:
                matches = re.findall(pattern, content)
                references['file_paths'].extend(matches)

            # Find output directory assignments
            output_patterns = [
                r'OUTPUT_DIR\s*=\s*["\']([^"\']+)["\']',
                r'output_path\s*=\s*["\']([^"\']+)["\']',
                r'\.to_csv\(["\']([^"\']+)["\']',
                r'\.to_html\(["\']([^"\']+)["\']',
                r'with open\(["\']([^"\']+)["\']',
            ]
            for pattern in output_patterns:
                matches = re.findall(pattern, content)
                references['output_dirs'].extend(matches)

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return references


def scan_actual_directories():
    """Scan actual directory structure."""
    structure = {
        'legacy': defaultdict(list),
        'new': defaultdict(list)
    }

    # Scan legacy structure
    legacy_path = REPO_ROOT / "_legacy_data_sources"
    if legacy_path.exists():
        for folder in OLD_FOLDERS:
            folder_path = legacy_path / folder
            if folder_path.exists():
                structure['legacy'][folder] = [
                    str(p.relative_to(REPO_ROOT))
                    for p in folder_path.rglob("*")
                    if p.is_dir()
                ]

    # Scan new structure
    for folder in NEW_FOLDERS:
        folder_path = REPO_ROOT / folder
        if folder_path.exists():
            structure['new'][folder] = [
                str(p.relative_to(REPO_ROOT))
                for p in folder_path.rglob("*")
                if p.is_dir()
            ]

    return structure


def generate_path_mapping():
    """Generate old path → new path mapping."""
    mappings = {
        # Data sources
        'hurdat2/input_data': '01_data_sources/hurdat2/raw',
        'hurdat2/outputs/cleaned_data': '01_data_sources/hurdat2/processed',
        'hurdat2/outputs/qa_maps': '01_data_sources/hurdat2/visuals/html',
        'hurdat2/src': '01_data_sources/hurdat2/src',

        'census/input_data': '01_data_sources/census/raw',
        'census/outputs': '01_data_sources/census/processed',
        'census/src': '01_data_sources/census/src',

        # Transformations
        'hurdat2/src/envelope_algorithm.py': '02_transformations/wind_coverage_envelope/src/envelope_algorithm.py',
        'hurdat2/outputs/envelopes': '02_transformations/wind_coverage_envelope/outputs',

        'hurdat2_census/src/storm_tract_distance.py': '02_transformations/storm_tract_distance/src/storm_tract_distance.py',
        'hurdat2_census/src/wind_interpolation.py': '02_transformations/wind_interpolation/src/wind_interpolation.py',
        'hurdat2_census/src/duration_calculator.py': '02_transformations/duration/src/duration_calculator.py',
        'hurdat2_census/src/lead_time_calculator.py': '02_transformations/lead_time/src/lead_time_calculator.py',
        'hurdat2_census/outputs/transformations': '02_transformations/storm_tract_distance/visuals/results/html',

        # Integration
        'integration/outputs': '03_integration/outputs/ml_ready',
        'integration/outputs/results': '03_integration/visuals/results/html',
        'integration/src': '03_integration/src',
    }
    return mappings


def main():
    """Main audit function."""
    print("=" * 80)
    print("REPOSITORY PATH AUDIT")
    print("=" * 80)

    # Find all Python files
    print("\n[1] Scanning Python files...")
    python_files = find_all_python_files()
    print(f"Found {len(python_files)} Python files")

    # Extract path references
    print("\n[2] Extracting path references...")
    all_references = defaultdict(lambda: defaultdict(list))

    for py_file in python_files:
        relative_path = py_file.relative_to(REPO_ROOT)
        refs = extract_path_references(py_file)

        if refs['imports']:
            all_references[str(relative_path)]['imports'] = refs['imports']
        if refs['file_paths']:
            all_references[str(relative_path)]['file_paths'] = refs['file_paths']
        if refs['output_dirs']:
            all_references[str(relative_path)]['output_dirs'] = refs['output_dirs']

    # Scan directory structure
    print("\n[3] Scanning directory structure...")
    structure = scan_actual_directories()

    # Generate mapping
    print("\n[4] Generating path mappings...")
    mappings = generate_path_mapping()

    # Print report
    print("\n" + "=" * 80)
    print("LEGACY PATH REFERENCES FOUND IN CODE")
    print("=" * 80)

    for file_path, refs in sorted(all_references.items()):
        has_legacy = False

        # Check for legacy imports
        if refs.get('imports'):
            legacy_imports = [imp for imp in refs['imports'] if imp in OLD_FOLDERS]
            if legacy_imports:
                has_legacy = True

        # Check for legacy file paths
        if refs.get('file_paths'):
            legacy_paths = [p for p in refs['file_paths'] if any(old in p for old in OLD_FOLDERS)]
            if legacy_paths:
                has_legacy = True

        if has_legacy:
            print(f"\n📄 {file_path}")

            if refs.get('imports'):
                legacy_imports = [imp for imp in refs['imports'] if imp in OLD_FOLDERS]
                if legacy_imports:
                    print(f"  ⚠️  Legacy imports: {set(legacy_imports)}")

            if refs.get('file_paths'):
                legacy_paths = [p for p in refs['file_paths'] if any(old in p for old in OLD_FOLDERS)]
                if legacy_paths:
                    print(f"  ⚠️  Legacy paths:")
                    for path in set(legacy_paths):
                        print(f"      - {path}")
                        # Suggest new path
                        for old_pattern, new_pattern in mappings.items():
                            if old_pattern in path:
                                suggested = path.replace(old_pattern, new_pattern)
                                print(f"        → Suggested: {suggested}")

            if refs.get('output_dirs'):
                print(f"  📂 Output locations:")
                for out_dir in set(refs['output_dirs']):
                    print(f"      - {out_dir}")

    print("\n" + "=" * 80)
    print("ACTUAL DIRECTORY STRUCTURE")
    print("=" * 80)

    print("\n📁 New Structure (Numbered Folders):")
    for folder, subdirs in sorted(structure['new'].items()):
        print(f"\n  {folder}/")
        for subdir in sorted(subdirs)[:5]:  # Show first 5
            print(f"    - {subdir}")
        if len(subdirs) > 5:
            print(f"    ... and {len(subdirs) - 5} more")

    print("\n📦 Legacy Structure (Archived):")
    for folder, subdirs in sorted(structure['legacy'].items()):
        print(f"\n  _legacy_data_sources/{folder}/")
        for subdir in sorted(subdirs)[:3]:  # Show first 3
            print(f"    - {subdir}")
        if len(subdirs) > 3:
            print(f"    ... and {len(subdirs) - 3} more")

    print("\n" + "=" * 80)
    print("PATH MIGRATION MAPPINGS")
    print("=" * 80)

    for old_path, new_path in sorted(mappings.items()):
        old_exists = (REPO_ROOT / "_legacy_data_sources" / old_path).exists()
        new_exists = (REPO_ROOT / new_path).exists()

        status = "✅" if new_exists else "❌"
        print(f"\n{status} {old_path}")
        print(f"   → {new_path}")
        if not new_exists:
            print(f"   ⚠️  New location does not exist!")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_files_with_legacy = len([f for f in all_references if all_references[f]])
    print(f"\n📊 Files with legacy references: {total_files_with_legacy}")
    print(f"📊 Total Python files scanned: {len(python_files)}")
    print(f"📊 Legacy folders archived: {len(structure['legacy'])}")
    print(f"📊 New structure folders: {len(structure['new'])}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
