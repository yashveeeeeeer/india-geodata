#!/usr/bin/env python3
"""Generate catalog.yml entries for Microsoft and Google buildings releases."""
import json, subprocess

def gh_api(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)

def fmt_size(b):
    if b >= 1073741824: return f"{b/1073741824:.1f} GB"
    if b >= 1048576: return f"{b/1048576:.1f} MB"
    if b >= 1024: return f"{b/1024:.1f} KB"
    return f"{b} B"

def get_fmt(n):
    for ext in [".geojsonl.7z.001", ".geojsonl.7z.002", ".geojsonl.7z.003",
                ".geojsonl.7z", ".parquet.meta.json", ".mosaic.json", ".parquet", ".pmtiles"]:
        if n.endswith(ext): return ext.lstrip(".")
    return "other"

configs = [
    {
        "tag": "buildings/microsoft",
        "name": "buildings-microsoft",
        "title": "Microsoft Building Footprints India",
        "desc": ("ML-derived building footprint polygons for India from Microsoft "
                 "global building dataset. Partitioned parquet, GeoJSON archives, and metadata."),
        "cat": "urban",
        "level": "buildings-microsoft",
    },
    {
        "tag": "buildings/google",
        "name": "buildings-google",
        "title": "Google Open Buildings India",
        "desc": ("ML-derived building footprint polygons for India from Google Open Buildings "
                 "V3 (2023). State-wise partitioned parquet files with confidence scores and geometry."),
        "cat": "urban",
        "level": "buildings-google",
    },
]

for cfg in configs:
    tag = cfg["tag"]
    rel = gh_api(f"repos/yashveeeeeeer/india-geodata/releases/tags/{tag}")
    assets = rel["assets"]
    base = f"https://github.com/yashveeeeeeer/india-geodata/releases/download/{tag}"
    fmts = sorted(set(get_fmt(a["name"]) for a in assets))

    print(f"- name: {cfg['name']}")
    print(f"  title: {cfg['title']}")
    print(f"  description: {cfg['desc']}")
    print(f"  category: {cfg['cat']}")
    print(f"  level: {cfg['level']}")
    print(f"  formats:")
    for f in fmts:
        print(f"  - {f}")
    print(f"  license_id: CC0-1.0")
    print(f"  storage: release")
    print(f"  release_tag: {tag}")
    print(f"  url: data/{tag}")
    print(f"  files:")
    for a in sorted(assets, key=lambda x: x["name"]):
        print(f"  - name: {a['name']}")
        print(f"    format: {get_fmt(a['name'])}")
        print(f"    size: {fmt_size(a['size'])}")
        print(f"    storage: release")
        print(f"    download_url: {base}/{a['name']}")
    print(f"  release_url: https://github.com/yashveeeeeeer/india-geodata/releases/tag/{tag}")
