#!/usr/bin/env python3
"""Build the DataMeet pincode release files, filled out to India's official boundary.

DataMeet's pincode shapes stop where India Post stops, so Pakistan-occupied
Kashmir, Gilgit-Baltistan and Aksai Chin are empty: India's official map
includes them, but they have no PIN codes. This script keeps every DataMeet
shape as it is and adds one extra shape per state (Jammu & Kashmir, Ladakh)
covering the part of that state, as drawn by the Survey of India, that no
pincode shape covers. Those rows have an empty pincode and say "No PIN code".

Inputs:
    data/postal/pincodes-datameet/   the split DataMeet shapefile in this repo
    SOI_States.parquet               Survey of India states, release admin/states

Outputs, in --out (default .cache/datameet-pincodes/):
    DataMeet_Pincodes.parquet        GeoParquet
    DataMeet_Pincodes.geojsonl.7z    one GeoJSON feature per line, 7z compressed
    DataMeet_Pincodes.shp.zip        single-file shapefile, with the QGIS style inside
    DataMeet_Pincodes.qml            QGIS style: label by pincode

Usage:
    python scripts/build-datameet-pincodes.py [--cache DIR] [--out DIR]

Requires:
    geopandas, pyogrio, pyarrow (pip install geopandas pyogrio pyarrow)
    7-Zip on PATH as 7z (or pass --sevenzip)
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

import geopandas as gpd
import pandas as pd
import shapely

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATAMEET_DIR = os.path.join(REPO, "data", "postal", "pincodes-datameet")
SOI_STATES_URL = "https://github.com/yashveeeeeeer/india-geodata/releases/download/admin/states/SOI_States.parquet"
NAME = "DataMeet_Pincodes"

# Survey of India state name -> the spelling DataMeet's own rows use
STATES = {"JAMMU AND KASHMIR": "Jammu & Kashmir", "LADAKH": "Ladakh"}
# Uncovered pieces smaller than this are line-drawing slivers between the two
# sources, not places without PIN codes.
MIN_PIECE_KM2 = 1.0
EQUAL_AREA = "EPSG:6933"


def find_7z(given):
    for cand in [given, "7z", "7za", r"C:\Program Files\7-Zip\7z.exe"]:
        if cand and shutil.which(cand):
            return shutil.which(cand)
    sys.exit("7-Zip not found; install it or pass --sevenzip")


def read_datameet(sevenzip, tmp):
    """Reassemble the split archive (india_pincodes.shp.zip + .z01-.z05) and read it."""
    for name in sorted(os.listdir(DATAMEET_DIR)):
        if name.endswith(".zip"):          # 7-Zip picks up the .z01-.z05 parts of a split zip itself
            subprocess.run([sevenzip, "x", "-y", "-o" + tmp, os.path.join(DATAMEET_DIR, name)],
                           check=True, stdout=subprocess.DEVNULL)
    shp = os.path.join(tmp, "india_pincodes.shp")
    gdf = gpd.read_file(shp)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.set_crs(4326, allow_override=True)   # the .prj is plain GCS_WGS_1984
    return gdf


def read_soi_states(cache):
    path = os.path.join(cache, "SOI_States.parquet")
    if not os.path.exists(path):
        os.makedirs(cache, exist_ok=True)
        print("downloading", SOI_STATES_URL)
        urllib.request.urlretrieve(SOI_STATES_URL, path)
    states = gpd.read_parquet(path)
    if states.crs is None or states.crs.to_epsg() != 4326:
        states = states.set_crs(4326, allow_override=True)   # stored as OGC:CRS84, same axes as 4326 here
    states["geometry"] = shapely.make_valid(states.geometry.values)
    return states


def filler_rows(pins, states, columns):
    covered = shapely.unary_union(shapely.make_valid(pins.geometry.values))
    rows = []
    for soi_name, dm_name in STATES.items():
        match = states[states["STATE_C"] == soi_name]
        if len(match) != 1:
            sys.exit(f"expected one Survey of India row for {soi_name}, found {len(match)}")
        gap = match.geometry.iloc[0].difference(covered)
        pieces = gpd.GeoDataFrame(geometry=list(getattr(gap, "geoms", [gap])), crs=4326)
        pieces = pieces[pieces.geom_type.isin(["Polygon", "MultiPolygon"])]
        km2 = pieces.to_crs(EQUAL_AREA).area / 1e6
        kept = pieces[km2 > MIN_PIECE_KM2]
        if kept.empty:
            continue
        shape = shapely.make_valid(shapely.unary_union(kept.geometry.values))
        print(f"{dm_name}: {len(kept)} uncovered pieces, {km2[km2 > MIN_PIECE_KM2].sum():,.0f} km2 "
              f"(dropped {int((km2 <= MIN_PIECE_KM2).sum())} slivers, {km2[km2 <= MIN_PIECE_KM2].sum():.1f} km2)")
        row = {c: "" for c in columns}
        row.update({"state": dm_name, "officename": "No PIN code", "source": "Survey of India outline", "geometry": shape})
        rows.append(row)
    return gpd.GeoDataFrame(rows, columns=columns + ["source", "geometry"], crs=4326)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", default=os.path.join(REPO, ".cache", "datameet-pincodes"))
    ap.add_argument("--out", default=os.path.join(REPO, ".cache", "datameet-pincodes"))
    ap.add_argument("--sevenzip")
    args = ap.parse_args()
    sevenzip = find_7z(args.sevenzip)
    os.makedirs(args.out, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        pins = read_datameet(sevenzip, tmp)
    columns = [c for c in pins.columns if c != "geometry"]
    pins["source"] = "DataMeet"
    states = read_soi_states(args.cache)
    extra = filler_rows(pins, states, columns)
    out = gpd.GeoDataFrame(pd.concat([pins, extra], ignore_index=True), crs=4326)
    out = out[columns + ["source", "geometry"]]
    print(f"{len(pins)} DataMeet shapes + {len(extra)} no-PIN-code shapes = {len(out)}")

    base = os.path.join(args.out, NAME)
    out.to_parquet(base + ".parquet", compression="zstd")

    for ext in (".geojsonl", ".geojsonl.7z", ".shp.zip"):
        if os.path.exists(base + ext):
            os.remove(base + ext)
    out.to_file(base + ".geojsonl", driver="GeoJSONSeq", engine="pyogrio")
    subprocess.run([sevenzip, "a", "-t7z", "-mx=9", base + ".geojsonl.7z", base + ".geojsonl"],
                   check=True, stdout=subprocess.DEVNULL)
    os.remove(base + ".geojsonl")

    qml_src = os.path.join(DATAMEET_DIR, "india_pincodes.qml")
    shutil.copyfile(qml_src, base + ".qml")
    with tempfile.TemporaryDirectory() as tmp:
        shp = os.path.join(tmp, NAME + ".shp")
        out.to_file(shp, engine="pyogrio", encoding="UTF-8")
        shutil.copyfile(qml_src, os.path.join(tmp, NAME + ".qml"))
        with zipfile.ZipFile(base + ".shp.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for name in sorted(os.listdir(tmp)):
                z.write(os.path.join(tmp, name), name)

    for ext in (".parquet", ".geojsonl.7z", ".shp.zip", ".qml"):
        print(f"  {NAME}{ext}  {os.path.getsize(base + ext) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
