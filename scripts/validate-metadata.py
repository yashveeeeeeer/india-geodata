#!/usr/bin/env python3
"""Validate all metadata.json files in the data/ directory tree.

Checks each metadata.json for required fields, correct types, and structural
constraints. Prints OK/FAIL for each file and exits non-zero if any fail.

Usage:
    python scripts/validate-metadata.py [--data-dir DATA_DIR]

Options:
    --data-dir  Root directory containing dataset folders (default: data/)
"""

import argparse
import glob
import json
import os
import sys


REQUIRED_TOP_LEVEL_FIELDS = [
    "name",
    "title",
    "description",
    "category",
    "coverage",
    "sources",
    "license",
    "formats",
    "coordinate_system",
    "storage",
]


def validate_coverage(coverage, errors):
    """Validate the coverage section of metadata."""
    if not isinstance(coverage, dict):
        errors.append("'coverage' must be a dict")
        return
    if "spatial" not in coverage:
        errors.append("'coverage' must contain a 'spatial' field")


def validate_sources(sources, errors):
    """Validate the sources section of metadata."""
    if not isinstance(sources, list):
        errors.append("'sources' must be a list")
        return
    if len(sources) == 0:
        errors.append("'sources' must be a non-empty list")
        return
    for i, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"'sources[{i}]' must be a dict")
            continue
        for field in ("name", "url", "authority"):
            if field not in source:
                errors.append(f"'sources[{i}]' missing required field '{field}'")


def validate_license(license_info, errors):
    """Validate the license section of metadata."""
    if not isinstance(license_info, dict):
        errors.append("'license' must be a dict")
        return
    for field in ("id", "name", "url"):
        if field not in license_info:
            errors.append(f"'license' missing required field '{field}'")


def validate_formats(formats, errors):
    """Validate the formats section of metadata."""
    if not isinstance(formats, list):
        errors.append("'formats' must be a list")
        return
    if len(formats) == 0:
        errors.append("'formats' must be a non-empty list")


def validate_storage(storage, errors):
    """Validate the storage section of metadata."""
    if not isinstance(storage, dict):
        errors.append("'storage' must be a dict")
        return
    if "repo_files" not in storage:
        errors.append("'storage' missing required field 'repo_files'")
    elif not isinstance(storage["repo_files"], bool):
        errors.append("'storage.repo_files' must be a boolean")
    if "release_tag" not in storage:
        errors.append("'storage' missing required field 'release_tag'")
    else:
        rt = storage["release_tag"]
        if rt is not None and not isinstance(rt, str):
            errors.append("'storage.release_tag' must be a string or null")


def validate_metadata_file(filepath):
    """Validate a single metadata.json file.

    Args:
        filepath: Path to the metadata.json file.

    Returns:
        A list of error strings. Empty list means the file is valid.
    """
    errors = []

    # Read and parse JSON
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except OSError as e:
        return [f"Cannot read file: {e}"]

    if not isinstance(data, dict):
        return ["Root element must be a JSON object"]

    # Check required top-level fields
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in data:
            errors.append(f"Missing required field '{field}'")

    # Validate individual sections if they exist
    if "coverage" in data:
        validate_coverage(data["coverage"], errors)

    if "sources" in data:
        validate_sources(data["sources"], errors)

    if "license" in data:
        validate_license(data["license"], errors)

    if "formats" in data:
        validate_formats(data["formats"], errors)

    if "storage" in data:
        validate_storage(data["storage"], errors)

    return errors


def find_metadata_files(data_dir):
    """Find all metadata.json files under the given directory.

    Args:
        data_dir: Root directory to search.

    Returns:
        Sorted list of metadata.json file paths.
    """
    pattern = os.path.join(data_dir, "**", "metadata.json")
    return sorted(glob.glob(pattern, recursive=True))


def main():
    """Main entry point for metadata validation."""
    parser = argparse.ArgumentParser(
        description="Validate all metadata.json files in the data/ directory tree."
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Root directory containing dataset folders (default: data/)",
    )
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    if not os.path.isdir(data_dir):
        print(f"ERROR: Data directory not found: {data_dir}", file=sys.stderr)
        sys.exit(1)

    metadata_files = find_metadata_files(data_dir)
    if not metadata_files:
        print(f"WARNING: No metadata.json files found under {data_dir}")
        sys.exit(0)

    total = 0
    passed = 0
    failed = 0

    for filepath in metadata_files:
        total += 1
        rel_path = os.path.relpath(filepath, start=os.getcwd())
        errors = validate_metadata_file(filepath)

        if errors:
            failed += 1
            print(f"FAIL  {rel_path}")
            for error in errors:
                print(f"      - {error}")
        else:
            passed += 1
            print(f"OK    {rel_path}")

    # Summary
    print()
    print(f"Validated {total} file(s): {passed} passed, {failed} failed.")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
