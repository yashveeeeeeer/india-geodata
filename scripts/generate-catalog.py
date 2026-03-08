#!/usr/bin/env python3
"""Generate a Jekyll-compatible catalog YAML file from dataset metadata.

Walks all data/**/metadata.json files and produces docs/_data/catalog.yml
containing a sorted list of dataset entries for use with Jekyll site generation.

Usage:
    python scripts/generate-catalog.py [--data-dir DATA_DIR] [--output OUTPUT]

Options:
    --data-dir  Root directory containing dataset folders (default: data/)
    --output    Output YAML file path (default: docs/_data/catalog.yml)

Requires:
    pyyaml (pip install pyyaml)
"""

import argparse
import glob
import json
import os
import sys

try:
    import yaml
except ImportError:
    print(
        "ERROR: pyyaml is required. Install it with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)


def determine_storage_mode(storage):
    """Determine the storage mode from the storage section.

    Args:
        storage: The storage dict from metadata.json.

    Returns:
        One of 'repo', 'release', or 'both'.
    """
    repo_files = storage.get("repo_files", False)
    release_tag = storage.get("release_tag")
    has_release = release_tag is not None and release_tag != ""

    if repo_files and has_release:
        return "both"
    elif has_release:
        return "release"
    else:
        return "repo"


def extract_level(metadata, dataset_rel_path):
    """Extract the administrative level from metadata or infer from path.

    Args:
        metadata: The parsed metadata dict.
        dataset_rel_path: Relative path to the dataset directory from repo root.

    Returns:
        A string indicating the level (e.g. 'national', 'state', 'district')
        or None if it cannot be determined.
    """
    # Try direct field first
    if "level" in metadata:
        return metadata["level"]

    # Try to infer from coverage
    coverage = metadata.get("coverage", {})
    if "level" in coverage:
        return coverage["level"]

    # Try to infer from the directory path
    parts = dataset_rel_path.replace("\\", "/").split("/")
    known_levels = {"national", "state", "district", "subdistrict", "village", "city"}
    for part in parts:
        if part.lower() in known_levels:
            return part.lower()

    return None


def process_metadata_file(filepath, repo_root):
    """Process a single metadata.json file into a catalog entry.

    Args:
        filepath: Absolute path to the metadata.json file.
        repo_root: Absolute path to the repository root.

    Returns:
        A dict representing the catalog entry, or None if the file is invalid.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARNING: Skipping {filepath}: {e}", file=sys.stderr)
        return None

    if not isinstance(metadata, dict):
        print(f"WARNING: Skipping {filepath}: root is not a JSON object", file=sys.stderr)
        return None

    # Determine the dataset directory path relative to repo root
    dataset_dir = os.path.dirname(filepath)
    dataset_rel_path = os.path.relpath(dataset_dir, start=repo_root)
    # Normalize to forward slashes for consistency
    dataset_rel_path = dataset_rel_path.replace("\\", "/")

    storage = metadata.get("storage", {})
    license_info = metadata.get("license", {})

    entry = {
        "name": metadata.get("name", ""),
        "title": metadata.get("title", ""),
        "description": metadata.get("description", ""),
        "category": metadata.get("category", ""),
        "level": extract_level(metadata, dataset_rel_path),
        "formats": metadata.get("formats", []),
        "license_id": license_info.get("id", ""),
        "storage": determine_storage_mode(storage),
        "release_tag": storage.get("release_tag"),
        "url": dataset_rel_path,
    }

    return entry


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
    """Main entry point for catalog generation."""
    parser = argparse.ArgumentParser(
        description="Generate docs/_data/catalog.yml from dataset metadata.json files."
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Root directory containing dataset folders (default: data/)",
    )
    parser.add_argument(
        "--output",
        default=os.path.join("docs", "_data", "catalog.yml"),
        help="Output YAML file path (default: docs/_data/catalog.yml)",
    )
    args = parser.parse_args()

    # Determine repo root (parent of scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)

    data_dir = os.path.join(repo_root, args.data_dir)
    if not os.path.isdir(data_dir):
        print(f"ERROR: Data directory not found: {data_dir}", file=sys.stderr)
        sys.exit(1)

    metadata_files = find_metadata_files(data_dir)
    if not metadata_files:
        print(f"WARNING: No metadata.json files found under {data_dir}")
        sys.exit(0)

    catalog = []
    skipped = 0

    for filepath in metadata_files:
        entry = process_metadata_file(filepath, repo_root)
        if entry is not None:
            catalog.append(entry)
        else:
            skipped += 1

    # Sort by category, then by name
    catalog.sort(key=lambda e: (e.get("category", ""), e.get("name", "")))

    # Ensure output directory exists
    output_path = os.path.join(repo_root, args.output)
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    # Write YAML
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(
            catalog,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    print(f"Catalog written to {os.path.relpath(output_path, start=os.getcwd())}")
    print(f"  {len(catalog)} dataset(s) included, {skipped} skipped.")


if __name__ == "__main__":
    main()
