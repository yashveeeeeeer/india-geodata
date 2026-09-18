#!/usr/bin/env python3
"""Backfill every city's series from the archive's bulk Parquet files.

Going city by city through the query API would be thousands of requests. The
archive also publishes one Parquet file per month, so a whole year is twelve
downloads and one pass, which is what this does.

For each city it writes daily means per pollutant plus an hour-by-month
climatology (the shape behind the diurnal/seasonal view):

    docs/projects/air-quality/data/series/<city-id>.json

Readings are averaged in two stages — station-day first, then across the
stations of a city — so a monitor that reported more hours does not dominate
the city's number.

Usage:
    python scripts/backfill-aq-series.py --start 2024-01 --end 2024-12
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict

import pandas as pd
import pyarrow.parquet as pq

BASE = "https://airquality.xkdr.org/v1/files/v1/measurements"
DEMO_KEY = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"      # reads the 2024 files
POLLUTANTS = ["PM2.5", "PM10", "NO2", "CO", "OZONE", "NH3"]
ALIAS = {"Ozone": "OZONE"}                           # archive spells it in full
COLUMNS = ["station_id", "parameter_name", "collected_at", "value"]


def months(start, end):
    y, m = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    while (y, m) <= (ey, em):
        yield y, m
        m += 1
        if m > 12:
            y, m = y + 1, 1


def download(y, m, key, cache):
    dest = os.path.join(cache, f"{y}-{m:02d}.parquet")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    url = f"{BASE}/year={y}/month={m:02d}/data.parquet"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}",
                                               "User-Agent": "india-geodata-build"})
    tmp = dest + ".part"
    with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    os.replace(tmp, dest)
    return dest


def month_frame(path, station_city):
    """One month -> per city, per pollutant, per day mean and station count,
    plus the hour-by-month sums needed for the climatology."""
    tbl = pq.read_table(path, columns=COLUMNS)
    df = tbl.to_pandas()
    del tbl

    df["parameter_name"] = df["parameter_name"].replace(ALIAS)
    df = df[df["parameter_name"].isin(POLLUTANTS)]
    df["city"] = df["station_id"].map(station_city)
    df = df.dropna(subset=["city", "value"])
    if df.empty:
        return None, None

    df["collected_at"] = pd.to_datetime(df["collected_at"], errors="coerce")
    df = df.dropna(subset=["collected_at"])
    df["day"] = df["collected_at"].dt.strftime("%Y-%m-%d")
    df["hour"] = df["collected_at"].dt.hour
    df["month"] = df["collected_at"].dt.month

    # stage 1: each station's own daily mean
    st = (df.groupby(["city", "parameter_name", "day", "station_id"], observed=True)["value"]
            .mean().reset_index())
    # stage 2: the city is the mean of its stations, not of its readings
    daily = (st.groupby(["city", "parameter_name", "day"], observed=True)["value"]
               .agg(["mean", "size"]).reset_index()
               .rename(columns={"mean": "v", "size": "n"}))

    cycle = (df.groupby(["city", "parameter_name", "month", "hour"], observed=True)["value"]
               .agg(["sum", "size"]).reset_index())
    return daily, cycle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01")
    ap.add_argument("--end", default="2024-12")
    ap.add_argument("--key", default=os.environ.get("AQI_KEY", DEMO_KEY))
    ap.add_argument("--cache", default=os.path.join(".cache", "aq-bulk"))
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, "docs", "projects", "air-quality", "data")
    out_dir = os.path.join(data_dir, "series")
    cache = os.path.join(root, args.cache)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(cache, exist_ok=True)

    stations = json.load(open(os.path.join(data_dir, "stations.json"), encoding="utf-8"))
    cities = json.load(open(os.path.join(data_dir, "cities.json"), encoding="utf-8"))
    station_city = {s["id"]: s["city"] + "|" + s["state"] for s in stations}
    city_id = {c["name"] + "|" + c["state"]: c["id"] for c in cities}
    name_of = {c["id"]: c["name"] for c in cities}

    dailies, cycles = [], []
    for y, m in months(args.start, args.end):
        try:
            path = download(y, m, args.key, cache)
        except urllib.error.HTTPError as e:
            print(f"  {y}-{m:02d}: HTTP {e.code} (a key of your own reads every month)")
            continue
        d, c = month_frame(path, station_city)
        if d is None:
            print(f"  {y}-{m:02d}: nothing usable")
            continue
        dailies.append(d)
        cycles.append(c)
        print(f"  {y}-{m:02d}: {len(d):6d} city-days, {d['city'].nunique():3d} cities")

    if not dailies:
        sys.exit("no months could be read")

    daily = pd.concat(dailies, ignore_index=True)
    cycle = pd.concat(cycles, ignore_index=True)
    cycle = (cycle.groupby(["city", "parameter_name", "month", "hour"], observed=True)[["sum", "size"]]
                  .sum().reset_index())
    cycle["mean"] = cycle["sum"] / cycle["size"]

    written = 0
    for key, grp in daily.groupby("city", observed=True):
        cid = city_id.get(key)
        if not cid:
            continue
        series = {}
        for p, g in grp.groupby("parameter_name", observed=True):
            g = g.sort_values("day")
            series[p] = {"t": g["day"].tolist(),
                         "v": [round(v, 1) for v in g["v"]],
                         "n": [int(n) for n in g["n"]]}
        cyc = {}
        sub = cycle[cycle["city"] == key]
        for p, g in sub.groupby("parameter_name", observed=True):
            grid = [[None] * 24 for _ in range(12)]
            for _, r in g.iterrows():
                grid[int(r["month"]) - 1][int(r["hour"])] = round(float(r["mean"]), 1)
            cyc[p] = grid
        payload = {"id": cid, "name": name_of.get(cid, key.split("|")[0]),
                   "series": series, "cycle": cyc}
        with open(os.path.join(out_dir, f"{cid}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
        written += 1

    present = sorted(f[:-5] for f in os.listdir(out_dir)
                     if f.endswith(".json") and f != "index.json")
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"cities": present, "start": args.start, "end": args.end},
                  f, separators=(",", ":"))

    total = sum(os.path.getsize(os.path.join(out_dir, f"{c}.json")) for c in present)
    print(f"  wrote {written} cities, index lists {len(present)}, "
          f"{total/1048576:.1f} MB total")


if __name__ == "__main__":
    main()
