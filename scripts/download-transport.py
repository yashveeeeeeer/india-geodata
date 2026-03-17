#!/usr/bin/env python3
"""
Download transport datasets from ramSeraph/indian_transport releases
and re-publish them as india-geodata releases.

Usage:
    python scripts/download-transport.py [--download-only] [--release RELEASE_TAG]

Requires: gh CLI authenticated with repo access.
"""

import subprocess
import sys
import os
import json
import shutil
from pathlib import Path

SOURCE_REPO = "ramSeraph/indian_transport"
TARGET_REPO = "yashveeeeeeer/india-geodata"

RELEASE_MAP = {
    "infra/national-highways": {
        "source_tag": "morth-roads",
        "title": "National Highways (MoRTH)",
        "description": (
            "National highway network, toll plazas, and MMLP from MoRTH via GatiShakti.\n\n"
            "Source: ramSeraph/indian_transport (morth-roads release)\n"
            "License: CC0 1.0\n\n"
            "Additional GeoJSON from datta07/INDIAN-SHAPEFILES."
        ),
    },
    "infra/soi-roads": {
        "source_tag": "soi-roads",
        "title": "SOI Roads and Transport Structures",
        "description": (
            "Road network and transport structures from Survey of India topographic maps.\n\n"
            "Includes: roads, tracks, bridges, tolls, passes, causeways, culverts, viaducts, fords, glacier routes.\n\n"
            "Source: ramSeraph/indian_transport (soi-roads release)\n"
            "License: CC0 1.0"
        ),
    },
    "infra/nic-roads": {
        "source_tag": "nic-roads",
        "title": "NIC Roads (Bharatmaps)",
        "description": (
            "Road network from the NIC Bharatmaps platform.\n\n"
            "Source: ramSeraph/indian_transport (nic-roads release)\n"
            "License: CC0 1.0"
        ),
    },
    "infra/ml-roads": {
        "source_tags": ["ms-roads", "fb-roads"],
        "title": "ML Road Detections (Microsoft + Facebook)",
        "description": (
            "Machine-learning-detected road networks from satellite imagery.\n\n"
            "Microsoft Road Detections (ODbL) + Facebook MapWithAI (MIT).\n\n"
            "Source: ramSeraph/indian_transport (ms-roads, fb-roads releases)"
        ),
    },
    "infra/urban-roads": {
        "source_tag": "urban-roads",
        "title": "Urban Roads",
        "description": (
            "Urban road networks from AMRUT cities, Bhuvan NUIS, and Telangana CDMA.\n\n"
            "Source: ramSeraph/indian_transport (urban-roads release)\n"
            "License: CC0 1.0"
        ),
    },
    "infra/pmgsy-roads": {
        "source_tag": "pmgsy-roads",
        "title": "PMGSY Roads (Enhanced Formats)",
        "description": (
            "PMGSY/GeoSadak rural road network in Parquet, PMTiles, GeoJSONL formats "
            "with road proposals by phase and bridge data.\n\n"
            "Source: ramSeraph/indian_transport (pmgsy-roads release)\n"
            "License: GODL"
        ),
    },
    "infra/railways": {
        "source_tag": "railways",
        "title": "Indian Railways",
        "description": (
            "Railway tracks, stations, sidings, metros, freight corridors, goods sheds, "
            "bridges from IR GeoPortal, SOI, GatiShakti, and Bhuvan.\n\n"
            "Source: ramSeraph/indian_transport (railways release)\n"
            "License: CC0 1.0\n\n"
            "Additional GeoJSON from datta07/INDIAN-SHAPEFILES."
        ),
    },
    "infra/inland-waterways": {
        "source_tag": "inland-waterways",
        "title": "Inland Waterways",
        "description": (
            "Inland waterway routes, navigation canals, facilities, locks, ferries, "
            "and steamer services from WRIS and Survey of India.\n\n"
            "Source: ramSeraph/indian_transport (inland-waterways release)\n"
            "License: CC0 1.0"
        ),
    },
}


def run(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if check and result.returncode != 0:
        print(f"ERROR: {cmd}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result


def download_release(source_tag, dest_dir):
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading {SOURCE_REPO} release '{source_tag}' -> {dest_dir}")
    run(f'gh release download "{source_tag}" --repo {SOURCE_REPO} --dir "{dest_dir}"')


def create_release(tag, title, description, asset_dir):
    asset_dir = Path(asset_dir)
    assets = list(asset_dir.glob("*"))
    if not assets:
        print(f"  WARNING: No assets found in {asset_dir}, creating release without files")
        run(
            f'gh release create "{tag}" --repo {TARGET_REPO} '
            f'--title "{title}" --notes "{description}"'
        )
        return

    asset_args = " ".join(f'"{a}"' for a in assets)
    run(
        f'gh release create "{tag}" --repo {TARGET_REPO} '
        f'--title "{title}" --notes "{description}" {asset_args}'
    )
    print(f"  Created release {tag} with {len(assets)} assets")


def main():
    download_only = "--download-only" in sys.argv
    target_release = None
    if "--release" in sys.argv:
        idx = sys.argv.index("--release")
        target_release = sys.argv[idx + 1]

    base_dir = Path("temp_transport_downloads")

    for tag, info in RELEASE_MAP.items():
        if target_release and tag != target_release:
            continue

        print(f"\n{'='*60}")
        print(f"Processing: {tag}")
        print(f"{'='*60}")

        dest_dir = base_dir / tag.replace("/", "_")

        source_tags = info.get("source_tags", [info.get("source_tag")])
        for stag in source_tags:
            download_release(stag, dest_dir)

        if not download_only:
            create_release(tag, info["title"], info["description"], dest_dir)

    if not download_only:
        print("\nDone! All releases created.")
    else:
        print(f"\nDownloaded to {base_dir}/")


if __name__ == "__main__":
    main()
