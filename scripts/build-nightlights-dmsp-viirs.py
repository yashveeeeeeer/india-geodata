#!/usr/bin/env python3
"""Build the district panel of harmonised DMSP and VIIRS nighttime lights.

Two satellites have measured night lights over India: DMSP-OLS (1992-2013)
and VIIRS (2012 onward). They are on different scales, so a long series needs
one put on the other's scale. Two published datasets do this, in opposite
directions, and this script sums each over the 641 Census 2011 districts:

  dmsp_like_*   Li, Zhou, Zhao & Zhao (2020). Inter-calibrated DMSP for
                1992-2013, then VIIRS converted to the DMSP scale.
                Digital number 0-63 per ~1 km pixel.
  viirs_like_*  Chen et al. (2021), Version 2 (2026). VIIRS-like radiance in
                nW/cm2/sr per ~500 m pixel. Years before 2013 are modelled
                from DMSP; 2013 onward come from VIIRS.

A pixel belongs to a district when its centre falls inside the district.

Usage:
    python scripts/build-nightlights-dmsp-viirs.py --download
    python scripts/build-nightlights-dmsp-viirs.py --cache D:/ntl --workers 3

The source rasters (~4.4 GB) live in --cache, never in the repository. Run
with --download again when either source publishes a new year; the file lists
are read from the publishers, so new years are picked up without code changes.

Requires:
    numpy, pandas, geopandas, rasterio
"""

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import urllib.request
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio import features
from rasterio.windows import from_bounds

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISTRICTS = os.path.join(
    ROOT, "data", "administrative", "districts", "census-2011", "2011_Dist.shp")
OUTPUT = os.path.join(
    ROOT, "data", "remote-sensing", "nightlights-dmsp-viirs",
    "nightlights_dmsp_viirs_district_panel.csv")

LI_API = "https://api.figshare.com/v2/articles/9828827"
LI_NAME = re.compile(r"Harmonized_DN_NTL_(\d{4})_(calDMSP|simVIIRS)\.tif")

CHEN_API = ("https://dataverse.harvard.edu/api/datasets/:persistentId/"
            "?persistentId=doi:10.7910/DVN/YGIVCD")
CHEN_FILE = "https://dataverse.harvard.edu/api/access/datafile/{}"
CHEN_NAME = re.compile(r"(\d{4})_Version2\.zip")
# Chen et al. train on 2013 VIIRS and check against 2012; earlier years are
# the model's reconstruction from DMSP.
CHEN_FIRST_VIIRS_YEAR = 2013

# Li et al. advise ignoring DN of 7 and below: low-light noise in DMSP, and
# already cut away in the years converted from VIIRS.
DN_THRESHOLD = 7

COLUMNS = [
    "district_id", "district_name", "state_name", "year",
    "dmsp_like_source", "dmsp_like_sum", "dmsp_like_sum_gt7",
    "dmsp_like_mean", "dmsp_like_max", "dmsp_like_lit_share_gt7",
    "dmsp_like_pixels",
    "viirs_like_source", "viirs_like_sum", "viirs_like_mean",
    "viirs_like_median", "viirs_like_max", "viirs_like_pixels",
]


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "india-geodata"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def published_files():
    """Every yearly file the two publishers list, with its URL and size."""
    files = []
    for f in fetch_json(LI_API)["files"]:
        if LI_NAME.fullmatch(f["name"]):
            files.append(("li2020", f["name"], f["download_url"], f["size"]))
    for f in fetch_json(CHEN_API)["data"]["latestVersion"]["files"]:
        d = f["dataFile"]
        if CHEN_NAME.fullmatch(d["filename"]):
            files.append(("chen-v2", d["filename"],
                          CHEN_FILE.format(d["id"]), d["filesize"]))
    return files


def download(cache):
    for folder, name, url, size in published_files():
        dest = os.path.join(cache, folder, name)
        if os.path.exists(dest) and os.path.getsize(dest) == size:
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        print(f"  downloading {folder}/{name} ({size / 1e6:.0f} MB)")
        part = dest + ".part"
        req = urllib.request.Request(url, headers={"User-Agent": "india-geodata"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(part, "wb") as out:
            while chunk := resp.read(1 << 20):
                out.write(chunk)
        if os.path.getsize(part) != size:
            os.remove(part)
            sys.exit(f"ERROR: {name} came down at the wrong size")
        os.replace(part, dest)


def local_tasks(cache):
    """(series, year, source label, raster path) for every file on disk."""
    tasks = []
    li_dir = os.path.join(cache, "li2020")
    for name in sorted(os.listdir(li_dir)) if os.path.isdir(li_dir) else []:
        m = LI_NAME.fullmatch(name)
        if m:
            label = "dmsp" if m[2] == "calDMSP" else "viirs_converted"
            tasks.append(("dmsp_like", int(m[1]), label, os.path.join(li_dir, name)))
    chen_dir = os.path.join(cache, "chen-v2")
    for name in sorted(os.listdir(chen_dir)) if os.path.isdir(chen_dir) else []:
        m = CHEN_NAME.fullmatch(name)
        if m:
            year = int(m[1])
            label = "viirs" if year >= CHEN_FIRST_VIIRS_YEAR else "dmsp_reconstructed"
            path = os.path.abspath(os.path.join(chen_dir, name)).replace(os.sep, "/")
            inner = [n for n in zipfile.ZipFile(path).namelist() if n.endswith(".tif")]
            if len(inner) != 1:
                sys.exit(f"ERROR: expected one GeoTIFF inside {name}, found {inner}")
            # Read straight out of the zip: unpacked, each year is ~10 GB.
            tasks.append(("viirs_like", year, label, f"/vsizip/{{{path}}}/{inner[0]}"))
    return tasks


_districts = None
_labels = {}


def load_districts():
    d = gpd.read_file(DISTRICTS).to_crs("EPSG:4326")
    return d.sort_values("censuscode").reset_index(drop=True)


def district_labels(shape, transform):
    """Raster of 1-based district positions, 0 outside every district."""
    key = (shape, tuple(transform))
    if key not in _labels:
        shapes = ((geom, i + 1) for i, geom in enumerate(_districts.geometry))
        _labels[key] = features.rasterize(
            shapes, out_shape=shape, transform=transform, fill=0, dtype="int32")
    return _labels[key]


def init_worker():
    global _districts
    _districts = load_districts()


def summarise(task):
    """Per-district statistics for one series and year."""
    series, year, label, path = task
    with rasterio.open(path) as src:
        window = from_bounds(*_districts.total_bounds, src.transform)
        window = window.round_offsets().round_lengths()
        values = src.read(1, window=window).astype("float32")
        transform = src.window_transform(window)

    labels = district_labels(values.shape, transform)
    inside = (labels > 0) & np.isfinite(values) & (values >= 0)
    lab = labels[inside]
    val = values[inside].astype("float64")
    del values

    n = len(_districts) + 1
    pixels = np.bincount(lab, minlength=n)[1:]
    total = np.bincount(lab, weights=val, minlength=n)[1:]
    grouped = pd.Series(val).groupby(lab)
    peak = grouped.max().reindex(range(1, n)).to_numpy()

    out = pd.DataFrame({
        "district_id": _districts["censuscode"].astype(int).to_numpy(),
        "year": year,
        f"{series}_source": label,
        f"{series}_sum": total,
        f"{series}_mean": np.divide(total, pixels, out=np.full(n - 1, np.nan),
                                    where=pixels > 0),
        f"{series}_max": peak,
        f"{series}_pixels": pixels,
    })
    if series == "dmsp_like":
        bright = val > DN_THRESHOLD
        out["dmsp_like_sum_gt7"] = np.bincount(
            lab, weights=val * bright, minlength=n)[1:]
        out["dmsp_like_lit_share_gt7"] = np.divide(
            np.bincount(lab, weights=bright, minlength=n)[1:], pixels,
            out=np.full(n - 1, np.nan), where=pixels > 0)
    else:
        out["viirs_like_median"] = grouped.median().reindex(range(1, n)).to_numpy()
    print(f"  {series} {year}: {pixels.sum():,} pixels", flush=True)
    return series, out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cache", default=os.environ.get(
        "NTL_CACHE", os.path.join(ROOT, ".cache", "ntl")),
        help="folder for the source rasters (default: .cache/ntl or $NTL_CACHE)")
    parser.add_argument("--download", action="store_true",
                        help="fetch any source file missing from --cache first")
    parser.add_argument("--workers", type=int, default=3,
                        help="parallel processes; each needs ~1.5 GB of memory")
    parser.add_argument("--output", default=OUTPUT)
    args = parser.parse_args()

    if args.download:
        print("Checking the publishers' file lists...")
        download(args.cache)

    tasks = local_tasks(args.cache)
    if not tasks:
        sys.exit(f"ERROR: no source rasters in {args.cache}; run with --download")
    print(f"Summarising {len(tasks)} rasters over Census 2011 districts...")

    parts = {"dmsp_like": [], "viirs_like": []}
    with cf.ProcessPoolExecutor(args.workers, initializer=init_worker) as pool:
        for series, frame in pool.map(summarise, tasks):
            parts[series].append(frame)

    districts = load_districts()
    names = pd.DataFrame({
        "district_id": districts["censuscode"].astype(int),
        "district_name": districts["DISTRICT"],
        "state_name": districts["ST_NM"],
    })
    keys = ["district_id", "year"]
    panel = None
    for frames in parts.values():
        if frames:
            block = pd.concat(frames, ignore_index=True)
            panel = block if panel is None else panel.merge(block, on=keys, how="outer")
    panel = names.merge(panel, on="district_id", how="right")
    for col in COLUMNS:
        if col not in panel:
            panel[col] = np.nan
    panel = panel[COLUMNS].sort_values(keys).reset_index(drop=True)

    # DN sums are whole numbers; radiance keeps enough places to be exact
    # at district scale.
    for col in ("dmsp_like_sum", "dmsp_like_sum_gt7", "dmsp_like_max",
                "dmsp_like_pixels", "viirs_like_pixels"):
        panel[col] = panel[col].round().astype("Int64")
    for col in ("dmsp_like_mean", "dmsp_like_lit_share_gt7", "viirs_like_mean",
                "viirs_like_median", "viirs_like_max"):
        panel[col] = panel[col].round(4)
    panel["viirs_like_sum"] = panel["viirs_like_sum"].round(2)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    panel.to_csv(args.output, index=False, lineterminator="\n")
    years = panel["year"]
    print(f"Wrote {len(panel):,} rows ({panel['district_id'].nunique()} districts, "
          f"{years.min()}-{years.max()}) to {os.path.relpath(args.output, ROOT)}")


if __name__ == "__main__":
    main()
