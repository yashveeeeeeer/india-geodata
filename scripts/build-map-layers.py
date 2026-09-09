#!/usr/bin/env python3
"""Build simplified TopoJSON boundary layers for the map maker (docs/maps/).

Reads the LGD boundary files published in this repository's GitHub Releases,
keeps only the fields the map maker needs, simplifies with mapshaper and
writes one TopoJSON file per level into docs/maps/data/.

Usage:
    python scripts/build-map-layers.py [--cache DIR] [--pct 5%]

Requires:
    geopandas, pyarrow (pip install geopandas pyarrow)
    Node.js (mapshaper is run through npx)
"""

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request

import geopandas as gpd

RELEASE = "https://github.com/yashveeeeeeer/india-geodata/releases/download"

LAYERS = {
    "states": {
        "url": f"{RELEASE}/admin/states/LGD_States.parquet",
        "fields": {"STNAME": "name", "State_LGD": "lgd", "STCODE11": "census"},
    },
    "districts": {
        "url": f"{RELEASE}/admin/districts/LGD_Districts.parquet",
        "fields": {"dtname": "name", "dist_lgd": "lgd", "dtcode11": "census",
                   "stname": "state", "state_lgd": "state_lgd"},
    },
    "subdistricts": {
        "url": f"{RELEASE}/admin/subdistricts/LGD_Subdistricts.parquet",
        "fields": {"sdtname": "name", "subdt_lgd": "lgd", "sdtcode11": "census",
                   "dtname": "district", "dist_lgd": "dist_lgd",
                   "stname": "state", "state_lgd": "state_lgd"},
    },
}

STATE_NAMES = {
    "ANDAMAN & NICOBAR": "Andaman & Nicobar Islands",
    "DADRA,NAGAR HAVELI,DAMAN & DIU": "Dadra & Nagar Haveli and Daman & Diu",
    "JAMMU & KASHMIR": "Jammu & Kashmir",
    "DELHI": "Delhi",
}


def state_title(raw):
    if raw in STATE_NAMES:
        return STATE_NAMES[raw]
    words = []
    for w in raw.split():
        words.append(w if w in ("&", "AND") else w.capitalize())
    return " ".join(words).replace(" And ", " and ")


def download(url, dest):
    if os.path.exists(dest):
        return
    print(f"  downloading {os.path.basename(dest)}")
    req = urllib.request.Request(url, headers={"User-Agent": "india-geodata-build"})
    with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def dedupe_ids(gdf):
    seen = {}
    ids = []
    for v in gdf["lgd"]:
        n = seen.get(v, 0)
        ids.append(str(v) if n == 0 else f"{v}-{n}")
        seen[v] = n + 1
    gdf["id"] = ids
    return gdf


def build(level, spec, cache, pct, out_dir):
    print(f"== {level}")
    src = os.path.join(cache, os.path.basename(spec["url"]))
    download(spec["url"], src)

    gdf = gpd.read_parquet(src)
    gdf = gdf[list(spec["fields"]) + ["geometry"]].rename(columns=spec["fields"])
    gdf["name"] = gdf["name"].astype(str).str.strip()
    if level == "states":
        gdf["name"] = gdf["name"].map(state_title)
    else:
        gdf["state"] = gdf["state"].astype(str).map(state_title)
        gdf["state_lgd"] = gdf["state_lgd"].astype(int)
    if "district" in gdf:
        gdf["district"] = gdf["district"].astype(str).str.strip()
        gdf["dist_lgd"] = gdf["dist_lgd"].astype(int)
    gdf["lgd"] = gdf["lgd"].astype(int)
    gdf["census"] = gdf["census"].astype(str).str.strip()
    gdf = dedupe_ids(gdf)

    tmp_geojson = os.path.join(cache, f"{level}.geojson")
    gdf.to_file(tmp_geojson, driver="GeoJSON")

    out = os.path.join(out_dir, f"{level}.topo.json")
    cmd = [
        "npx", "--yes", "mapshaper", tmp_geojson,
        "-simplify", pct, "keep-shapes",
        "-clean", "overlap-rule=min-area",
        "-rename-layers", level,
        "-o", "format=topojson", "quantization=1e5", "id-field=id", out,
    ]
    subprocess.run(cmd, check=True, shell=(os.name == "nt"))
    size = os.path.getsize(out) / 1048576
    print(f"  {len(gdf)} features -> {os.path.relpath(out)} ({size:.2f} MB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=".cache/map-layers")
    ap.add_argument("--pct", default="5%")
    ap.add_argument("--levels", default=",".join(LAYERS))
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache = os.path.join(root, args.cache)
    out_dir = os.path.join(root, "docs", "maps", "data")
    os.makedirs(cache, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    for level in args.levels.split(","):
        build(level, LAYERS[level], cache, args.pct, out_dir)


if __name__ == "__main__":
    sys.exit(main())
