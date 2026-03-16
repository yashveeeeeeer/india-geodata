#!/usr/bin/env python3
"""Generate a Jekyll-compatible catalog YAML file from dataset metadata.

Walks all data/**/metadata.json files and produces docs/_data/catalog.yml
containing a sorted list of dataset entries with file-level download URLs
for use with Jekyll site generation.

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
import subprocess
import sys

try:
    import yaml
except ImportError:
    print(
        "ERROR: pyyaml is required. Install it with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)

GITHUB_OWNER = "yashveeeeeer"
GITHUB_REPO = "india-geodata"
GITHUB_BASE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
RAW_BASE = f"{GITHUB_BASE}/raw/main"
RELEASE_BASE = f"{GITHUB_BASE}/releases/download"

SKIP_FILES = {"metadata.json", "README.md", ".gitkeep", "Thumbs.db", ".DS_Store"}

_release_cache = {}


def fetch_release_assets(release_tag):
    """Fetch release assets from GitHub using the gh CLI.

    Returns a list of dicts with name, size (bytes), and download URL,
    or an empty list if the gh CLI is unavailable or the release is not found.
    """
    if release_tag in _release_cache:
        return _release_cache[release_tag]

    try:
        result = subprocess.run(
            [
                "gh", "release", "view", release_tag,
                "--repo", f"{GITHUB_OWNER}/{GITHUB_REPO}",
                "--json", "assets",
                "--jq", ".assets[] | {name, size, url: .url}",
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"  WARNING: gh release view {release_tag} failed: {result.stderr.strip()}", file=sys.stderr)
            _release_cache[release_tag] = []
            return []

        assets = []
        for line in result.stdout.strip().splitlines():
            if line:
                assets.append(json.loads(line))
        _release_cache[release_tag] = assets
        return assets
    except FileNotFoundError:
        print("WARNING: gh CLI not found — release assets will not be fetched.", file=sys.stderr)
        _release_cache[release_tag] = []
        return []
    except subprocess.TimeoutExpired:
        print(f"  WARNING: gh release view {release_tag} timed out.", file=sys.stderr)
        _release_cache[release_tag] = []
        return []


def human_size(size_bytes):
    """Convert bytes to a human-readable size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024:
            if unit in ("B", "KB"):
                return f"{size_bytes:.0f} {unit}"
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_format_from_filename(filename):
    """Determine the format from a filename extension."""
    lower = filename.lower()
    if lower.endswith(".geojsonl.7z"):
        return "geojsonl.7z"
    if lower.endswith(".geojson"):
        return "geojson"
    ext_map = {
        ".parquet": "parquet", ".pmtiles": "pmtiles",
        ".shp": "shapefile", ".shx": "shapefile", ".dbf": "shapefile",
        ".prj": "shapefile", ".cpg": "shapefile",
        ".csv": "csv", ".tsv": "tsv", ".json": "json",
        ".kml": "kml", ".kmz": "kmz", ".topojson": "topojson",
        ".zip": "zip", ".7z": "7z",
        ".tif": "geotiff", ".tiff": "geotiff",
        ".gif": "gif", ".png": "png",
    }
    _, ext = os.path.splitext(lower)
    return ext_map.get(ext, ext.lstrip(".") if ext else "unknown")


def determine_storage_mode(metadata):
    """Determine storage mode: 'repo', 'release', 'both', or 'external'."""
    if metadata.get("storage") == "external":
        return "external"

    storage = metadata.get("storage", {})
    if isinstance(storage, str):
        return storage

    repo_files = storage.get("repo_files", False)
    release_tag = storage.get("release_tag")
    has_release = release_tag is not None and release_tag != ""

    files = metadata.get("files", [])
    has_release_files = any(f.get("storage") == "release" for f in files)
    has_repo_files = repo_files or any(f.get("storage") == "repo" for f in files)

    if has_release or has_release_files:
        if has_repo_files:
            return "both"
        return "release"
    return "repo"


def get_release_tag(metadata):
    """Extract the release tag from metadata."""
    storage = metadata.get("storage", {})
    if isinstance(storage, dict):
        tag = storage.get("release_tag")
        if tag:
            return tag
    for f in metadata.get("files", []):
        tag = f.get("release_tag")
        if tag:
            return tag
    return None


def scan_directory_files(dataset_dir, dataset_rel_path):
    """Scan a directory for data files and return file entries with URLs."""
    files = []
    for root, dirs, filenames in os.walk(dataset_dir):
        dirs.sort()
        for fname in sorted(filenames):
            if fname in SKIP_FILES:
                continue
            fpath = os.path.join(root, fname)
            size = os.path.getsize(fpath)
            rel = os.path.relpath(fpath, dataset_dir).replace("\\", "/")
            files.append({
                "name": rel,
                "format": get_format_from_filename(fname),
                "size": human_size(size),
                "storage": "repo",
                "download_url": f"{RAW_BASE}/{dataset_rel_path}/{rel}",
            })
    return files


def build_file_list(metadata, dataset_dir, dataset_rel_path):
    """Build the file list for a dataset with download URLs."""
    files_meta = metadata.get("files", [])
    release_tag = get_release_tag(metadata)

    if files_meta:
        result = []
        for f in files_meta:
            fname = f.get("filename", f.get("name", ""))
            entry = {
                "name": fname,
                "format": f.get("format", get_format_from_filename(fname)),
                "size": f.get("size", ""),
                "storage": f.get("storage", "repo"),
            }
            if f.get("description"):
                entry["description"] = f["description"]

            file_storage = f.get("storage", "repo")
            file_release_tag = f.get("release_tag", release_tag)
            if file_storage == "release" and file_release_tag:
                entry["download_url"] = f"{RELEASE_BASE}/{file_release_tag}/{fname}"
            elif file_storage == "repo":
                entry["download_url"] = f"{RAW_BASE}/{dataset_rel_path}/{fname}"

            result.append(entry)
        return result

    # No files in metadata — scan the directory first
    local_files = scan_directory_files(dataset_dir, dataset_rel_path)
    if local_files:
        return local_files

    # No local data files either — try fetching from GitHub Releases
    if release_tag:
        assets = fetch_release_assets(release_tag)
        if assets:
            print(f"  Fetched {len(assets)} release asset(s) for tag '{release_tag}'")
            return [
                {
                    "name": a["name"],
                    "format": get_format_from_filename(a["name"]),
                    "size": human_size(a["size"]),
                    "storage": "release",
                    "download_url": a["url"],
                }
                for a in assets
            ]

    return []


def extract_level(metadata, dataset_rel_path):
    """Extract the administrative level from metadata or infer from path."""
    if "level" in metadata:
        return metadata["level"]
    coverage = metadata.get("coverage", {})
    if "level" in coverage:
        return coverage["level"]
    parts = dataset_rel_path.replace("\\", "/").split("/")
    known_levels = {"national", "state", "district", "subdistrict", "village", "city"}
    for part in parts:
        if part.lower() in known_levels:
            return part.lower()
    return None


def process_metadata_file(filepath, repo_root):
    """Process a single metadata.json file into a catalog entry."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARNING: Skipping {filepath}: {e}", file=sys.stderr)
        return None

    if not isinstance(metadata, dict):
        print(f"WARNING: Skipping {filepath}: root is not a JSON object", file=sys.stderr)
        return None

    dataset_dir = os.path.dirname(filepath)
    dataset_rel_path = os.path.relpath(dataset_dir, start=repo_root).replace("\\", "/")

    license_info = metadata.get("license", {})
    if isinstance(license_info, str):
        license_id = license_info
    else:
        license_id = license_info.get("id", "")
    storage_mode = determine_storage_mode(metadata)
    release_tag = get_release_tag(metadata)

    entry = {
        "name": metadata.get("name", ""),
        "title": metadata.get("title", ""),
        "description": metadata.get("description", ""),
        "category": metadata.get("category", ""),
        "level": extract_level(metadata, dataset_rel_path),
        "formats": metadata.get("formats", []),
        "license_id": license_id,
        "storage": storage_mode,
        "release_tag": release_tag,
        "url": dataset_rel_path,
    }

    if storage_mode == "external":
        entry["external_url"] = metadata.get("external_url", "")
        entry["external_docs"] = metadata.get("external_docs", "")
        entry["files"] = []
    else:
        entry["files"] = build_file_list(metadata, dataset_dir, dataset_rel_path)

    if release_tag:
        entry["release_url"] = f"{GITHUB_BASE}/releases/tag/{release_tag}"

    return entry


def find_metadata_files(data_dir):
    """Find all metadata.json files under the given directory."""
    pattern = os.path.join(data_dir, "**", "metadata.json")
    return sorted(glob.glob(pattern, recursive=True))


def main():
    """Main entry point for catalog generation."""
    parser = argparse.ArgumentParser(
        description="Generate docs/_data/catalog.yml from dataset metadata.json files."
    )
    parser.add_argument(
        "--data-dir", default="data",
        help="Root directory containing dataset folders (default: data/)",
    )
    parser.add_argument(
        "--output", default=os.path.join("docs", "_data", "catalog.yml"),
        help="Output YAML file path (default: docs/_data/catalog.yml)",
    )
    args = parser.parse_args()

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
    total_files = 0

    for filepath in metadata_files:
        entry = process_metadata_file(filepath, repo_root)
        if entry is not None:
            catalog.append(entry)
            total_files += len(entry.get("files", []))
        else:
            skipped += 1

    catalog.sort(key=lambda e: (e.get("category", ""), e.get("name", "")))

    output_path = os.path.join(repo_root, args.output)
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"Catalog written to {os.path.relpath(output_path, start=os.getcwd())}")
    print(f"  {len(catalog)} dataset(s), {total_files} file(s) indexed, {skipped} skipped.")


if __name__ == "__main__":
    main()
