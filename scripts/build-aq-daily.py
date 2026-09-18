#!/usr/bin/env python3
"""Build per-day, per-monitor matrices so the map can scrub through history.

The series files answer "one city, every day", which is what the chart needs. The
map needs the opposite — "one day, every monitor" — and loading 237 city files to
draw a single day would be absurd.

These are keyed by monitor, not city, deliberately: the page aggregates monitors
up to city, district or state with the same code it uses for the live feed, and a
city point cannot represent a city spanning several districts (Delhi covers
eleven). One file per pollutant-year, so scrubbing loads only what is on screen.

    docs/projects/air-quality/data/daily/<POLLUTANT>-<year>.json
        { "stations": [...ids...], "t": [...dates...], "v": [[per station], ...] }

Reads the bulk Parquet cached by backfill-aq-series.py.

Usage:
    python scripts/build-aq-daily.py [--cache .cache/aq-bulk]
"""

import argparse
import glob
import json
import os
import re
from collections import defaultdict

import pandas as pd
import pyarrow.parquet as pq

POLLUTANTS = ["PM2.5", "PM10", "NO2", "CO", "OZONE", "NH3"]
ALIAS = {"Ozone": "OZONE"}
COLUMNS = ["station_id", "parameter_name", "collected_at", "value"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(".cache", "aq-bulk"))
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, "docs", "projects", "air-quality", "data")
    out_dir = os.path.join(data_dir, "daily")
    cache = os.path.join(root, args.cache)
    os.makedirs(out_dir, exist_ok=True)

    known = {s["id"] for s in json.load(open(os.path.join(data_dir, "stations.json"),
                                             encoding="utf-8"))}
    files = sorted(glob.glob(os.path.join(cache, "*.parquet")))
    if not files:
        raise SystemExit(f"no cached Parquet in {args.cache}; run backfill-aq-series.py first")

    # (pollutant, year) -> day -> station -> value
    table = defaultdict(lambda: defaultdict(dict))
    for path in files:
        df = pq.read_table(path, columns=COLUMNS).to_pandas()
        df["parameter_name"] = df["parameter_name"].replace(ALIAS)
        df = df[df["parameter_name"].isin(POLLUTANTS)]
        df = df[df["station_id"].isin(known)]
        df["collected_at"] = pd.to_datetime(df["collected_at"], errors="coerce")
        df = df.dropna(subset=["collected_at", "value"])
        df["day"] = df["collected_at"].dt.strftime("%Y-%m-%d")

        daily = (df.groupby(["parameter_name", "day", "station_id"], observed=True)["value"]
                   .mean().reset_index())
        for p, d, sid, v in zip(daily["parameter_name"], daily["day"],
                                daily["station_id"], daily["value"]):
            table[(p, d[:4])][d][sid] = round(float(v), 1)
        print(f"  {os.path.basename(path):<18s} {len(daily):7d} station-days")

    index = defaultdict(list)
    for (p, year), days in sorted(table.items()):
        ids = sorted({s for d in days.values() for s in d})
        dates = sorted(days)
        rows = [[days[d].get(s) for s in ids] for d in dates]
        payload = {"pollutant": p, "year": year, "stations": ids, "t": dates, "v": rows}
        out = os.path.join(out_dir, f"{p}-{year}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
        index[p].append(year)
        print(f"  {p:<6s} {year}  {len(dates):3d} days x {len(ids):3d} monitors  "
              f"{os.path.getsize(out)/1024:5.0f} KB")

    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"pollutants": {p: sorted(y) for p, y in index.items()}},
                  f, separators=(",", ":"))

    total = sum(os.path.getsize(f) for f in glob.glob(os.path.join(out_dir, "*.json")))
    print(f"  {total/1048576:.1f} MB total")


if __name__ == "__main__":
    main()
