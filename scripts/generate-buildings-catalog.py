#!/usr/bin/env python3
"""Generate catalog.yml entries for buildings releases from GitHub API."""
import json
import subprocess
import sys

def gh_api(path):
    result = subprocess.run(
        ["gh", "api", path],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)

def format_size(bytes_val):
    if bytes_val >= 1024 * 1024 * 1024:
        return f"{bytes_val / 1024**3:.1f} GB"
    if bytes_val >= 1024 * 1024:
        return f"{bytes_val / 1024**2:.1f} MB"
    if bytes_val >= 1024:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{bytes_val} B"

def get_format(name):
    if name.endswith(".geojsonl.7z"):
        return "geojsonl.7z"
    if name.endswith(".parquet"):
        return "parquet"
    if name.endswith(".pmtiles"):
        return "pmtiles"
    return "unknown"

def main():
    release_tag = sys.argv[1] if len(sys.argv) > 1 else "buildings/urban"
    release = gh_api(f"repos/yashveeeeeeer/india-geodata/releases/tags/{release_tag}")
    base_url = f"https://github.com/yashveeeeeeer/india-geodata/releases/download/{release_tag}"
    
    print("  files:")
    for asset in release["assets"]:
        name = asset["name"]
        size = format_size(asset["size"])
        fmt = get_format(name)
        print(f"  - name: {name}")
        print(f"    format: {fmt}")
        print(f"    size: {size}")
        print(f"    storage: release")
        print(f"    download_url: {base_url}/{name}")

if __name__ == "__main__":
    main()
