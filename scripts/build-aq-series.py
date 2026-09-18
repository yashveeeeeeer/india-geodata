#!/usr/bin/env python3
"""Build per-city daily time series for the air quality project page.

The page loads one small file per city, lazily, when that city is selected. This
script produces those files: daily means per pollutant, aggregated from the
station-level archive.

Stations are averaged in one step here because a city's monitors all sit in the
same city; the station -> city -> larger-unit two-stage mean matters at state and
district level, which is built separately.

    docs/projects/air-quality/data/series/<city-id>.json

Usage:
    python scripts/build-aq-series.py --cities delhi-delhi,mumbai-maharashtra \\
        --start 2024-01 --end 2024-12
"""

import argparse
import calendar
import csv
import datetime
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

API = "https://airquality.xkdr.org/v1/measurements"
DEMO_KEY = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"
POLLUTANTS = ["PM2.5", "PM10", "NO2", "CO", "OZONE", "NH3"]
# the archive names ozone in full; the live feed calls it OZONE
ALIAS = {"Ozone": "OZONE"}


def months(start, end):
    y, m = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    while (y, m) <= (ey, em):
        yield y, m
        m += 1
        if m > 12:
            y, m = y + 1, 1


def fetch_window(city, d0, d1, key, depth=0):
    """One request for [d0, d1]. A truncated response means the row cap hit, so
    halve the window and retry; otherwise big cities silently lose stations."""
    q = urllib.parse.urlencode({"city": city, "start": d0, "end": d1,
                                "agg": "daily", "format": "csv"})
    req = urllib.request.Request(f"{API}?{q}",
                                 headers={"Authorization": f"Bearer {key}",
                                          "User-Agent": "india-geodata-build"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            truncated = r.headers.get("X-Truncated") == "true"
            rows = list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))
    except urllib.error.HTTPError as e:
        print(f"      ! {d0}..{d1} HTTP {e.code}", file=sys.stderr)
        return []

    if not truncated:
        return rows
    if d0 == d1 or depth > 6:
        print(f"      ! {d0}..{d1} still truncated at one day", file=sys.stderr)
        return rows
    a = datetime.date.fromisoformat(d0)
    b = datetime.date.fromisoformat(d1)
    mid = a + (b - a) // 2
    return (fetch_window(city, d0, mid.isoformat(), key, depth + 1)
            + fetch_window(city, (mid + datetime.timedelta(days=1)).isoformat(), d1, key, depth + 1))


def fetch(city, y, m, key):
    last = calendar.monthrange(y, m)[1]
    return fetch_window(city, f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last}", key)


def build_city(city_name, city_id, start, end, key, out_dir):
    # pollutant -> date -> [station means]
    acc = defaultdict(lambda: defaultdict(list))
    for y, m in months(start, end):
        for r in fetch(city_name, y, m, key):
            p = ALIAS.get(r["parameter_name"], r["parameter_name"])
            if p not in POLLUTANTS:
                continue
            try:
                v = float(r["mean"])
            except (TypeError, ValueError):
                continue
            if v != v:
                continue
            acc[p][r["period_start"][:10]].append(v)

    series = {}
    for p, days in acc.items():
        dates = sorted(days)
        series[p] = {
            "t": dates,
            "v": [round(sum(days[d]) / len(days[d]), 1) for d in dates],
            "n": [len(days[d]) for d in dates],          # stations behind each day
        }
    if not series:
        return None

    payload = {"id": city_id, "name": city_name, "series": series}
    path = os.path.join(out_dir, f"{city_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    days = len(next(iter(series.values()))["t"])
    print(f"  {city_name:<16s} {len(series)} pollutants, {days:4d} days "
          f"-> {os.path.getsize(path)/1024:.0f} KB")
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cities", default="", help="comma-separated city ids from cities.json")
    ap.add_argument("--start", default="2024-01")
    ap.add_argument("--end", default="2024-12")
    ap.add_argument("--key", default=os.environ.get("AQI_KEY", DEMO_KEY))
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, "docs", "projects", "air-quality", "data")
    out_dir = os.path.join(data_dir, "series")
    os.makedirs(out_dir, exist_ok=True)

    cities = json.load(open(os.path.join(data_dir, "cities.json"), encoding="utf-8"))
    by_id = {c["id"]: c for c in cities}
    wanted = [w for w in args.cities.split(",") if w] or [c["id"] for c in cities]

    built = []
    for cid in wanted:
        c = by_id.get(cid)
        if not c:
            print(f"  ? unknown city id: {cid}", file=sys.stderr)
            continue
        if build_city(c["name"], cid, args.start, args.end, args.key, out_dir):
            built.append(cid)

    # The index lists every series on disk, not just this run's, so rebuilding one
    # city does not drop the others.
    present = sorted(f[:-5] for f in os.listdir(out_dir)
                     if f.endswith(".json") and f != "index.json")
    index = os.path.join(out_dir, "index.json")
    with open(index, "w", encoding="utf-8") as f:
        json.dump({"cities": present, "start": args.start, "end": args.end},
                  f, separators=(",", ":"))
    print(f"  built {len(built)}, index lists {len(present)} -> {os.path.relpath(index, root)}")


if __name__ == "__main__":
    main()
