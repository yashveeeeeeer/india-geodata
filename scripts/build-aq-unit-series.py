#!/usr/bin/env python3
"""Build daily series for India and for each state, alongside the city ones.

The page needs something to show before anyone has clicked a city — on load, and
after zooming into a state. Without these it falls back to nothing, and the whole
right-hand side sits empty.

Same shape as the city files, so the page reads them with the same code:

    docs/projects/air-quality/data/series/india.json
    docs/projects/air-quality/data/series/state-<feature id>.json

Readings average in two stages, monitors into cities and then cities into the
unit, so a city with many monitors does not speak for a whole state. Districts are
deliberately not built: 785 files for units that mostly hold a single monitor is
tens of megabytes for very little, and the page falls back to the containing
state instead.

Reads the bulk Parquet cached by backfill-aq-series.py.

Usage:
    python scripts/build-aq-unit-series.py [--cache .cache/aq-bulk]
"""

import argparse
import glob
import json
import os
from collections import defaultdict

import pandas as pd
import pyarrow.parquet as pq

POLLUTANTS = ["PM2.5", "PM10", "NO2", "CO", "OZONE", "NH3"]
ALIAS = {"Ozone": "OZONE"}
COLUMNS = ["station_id", "parameter_name", "collected_at", "value"]


def write_unit(out_dir, key, name, daily, cycle):
    """daily: pollutant -> day -> [city means]; cycle: pollutant -> (month, hour) -> [sums]"""
    series = {}
    for p, days in daily.items():
        dates = sorted(days)
        if not dates:
            continue
        series[p] = {
            "t": dates,
            "v": [round(sum(days[d]["vals"]) / len(days[d]["vals"]), 1) for d in dates],
            "n": [days[d]["monitors"] for d in dates],
        }
    cyc = {}
    for p, cells in cycle.items():
        grid = [[None] * 24 for _ in range(12)]
        for (m, h), acc in cells.items():
            if acc["n"]:
                grid[m - 1][h] = round(acc["sum"] / acc["n"], 1)
        cyc[p] = grid
    if not series:
        return 0
    payload = {"id": key, "name": name, "series": series, "cycle": cyc}
    path = os.path.join(out_dir, key + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    return os.path.getsize(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(".cache", "aq-bulk"))
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, "docs", "projects", "air-quality", "data")
    out_dir = os.path.join(data_dir, "series")
    cache = os.path.join(root, args.cache)

    stations = json.load(open(os.path.join(data_dir, "stations.json"), encoding="utf-8"))
    coverage = json.load(open(os.path.join(data_dir, "coverage.json"), encoding="utf-8"))
    unit_of = coverage.get("stationUnit", {})
    state_name = {fid: v["name"] for fid, v in coverage.get("states", {}).items()}

    city_of = {s["id"]: s["city"] + "|" + s["state"] for s in stations}
    state_of = {s["id"]: (unit_of.get(s["id"]) or {}).get("state") for s in stations}

    files = sorted(glob.glob(os.path.join(cache, "*.parquet")))
    if not files:
        raise SystemExit(f"no cached Parquet in {args.cache}; run backfill-aq-series.py first")

    # unit -> pollutant -> day -> {vals: [city means], monitors: n}
    daily = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"vals": [], "monitors": 0})))
    cycle = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"sum": 0.0, "n": 0})))

    for path in files:
        df = pq.read_table(path, columns=COLUMNS).to_pandas()
        df["parameter_name"] = df["parameter_name"].replace(ALIAS)
        df = df[df["parameter_name"].isin(POLLUTANTS)]
        df["city"] = df["station_id"].map(city_of)
        df["state"] = df["station_id"].map(state_of)
        df = df.dropna(subset=["city", "value"])
        df["collected_at"] = pd.to_datetime(df["collected_at"], errors="coerce")
        df = df.dropna(subset=["collected_at"])
        df["day"] = df["collected_at"].dt.strftime("%Y-%m-%d")
        df["hour"] = df["collected_at"].dt.hour
        df["month"] = df["collected_at"].dt.month

        # stage 1: a city's day is the mean of its monitors' days
        st = (df.groupby(["state", "city", "parameter_name", "day", "station_id"], observed=True)["value"]
                .mean().reset_index())
        city_day = (st.groupby(["state", "city", "parameter_name", "day"], observed=True)["value"]
                      .agg(["mean", "size"]).reset_index())

        for stv, _city, p, d, v, n in zip(city_day["state"], city_day["city"],
                                          city_day["parameter_name"], city_day["day"],
                                          city_day["mean"], city_day["size"]):
            for unit in ("india", stv):
                if unit is None:
                    continue
                cell = daily[unit][p][d]
                cell["vals"].append(float(v))
                cell["monitors"] += int(n)

        # climatology, from the same city-level means
        ch = (df.groupby(["state", "city", "parameter_name", "month", "hour"], observed=True)["value"]
                .mean().reset_index())
        for stv, p, m, h, v in zip(ch["state"], ch["parameter_name"], ch["month"],
                                   ch["hour"], ch["value"]):
            for unit in ("india", stv):
                if unit is None:
                    continue
                acc = cycle[unit][p][(int(m), int(h))]
                acc["sum"] += float(v)
                acc["n"] += 1

        print(f"  {os.path.basename(path)} folded in")

    total = 0
    written = 0
    for unit in sorted(daily, key=lambda u: (u != "india", str(u))):
        if unit == "india":
            key, name = "india", "All India"
        else:
            key, name = "state-" + str(unit), state_name.get(str(unit), "State " + str(unit))
        size = write_unit(out_dir, key, name, daily[unit], cycle[unit])
        if size:
            written += 1
            total += size
            print(f"  {name:<34s} -> {key}.json ({size/1024:.0f} KB)")

    # the page reads this to know what exists
    index_path = os.path.join(out_dir, "index.json")
    index = json.load(open(index_path, encoding="utf-8")) if os.path.exists(index_path) else {}
    present = sorted(f[:-5] for f in os.listdir(out_dir)
                     if f.endswith(".json") and f != "index.json")
    index["cities"] = [c for c in present if c != "india" and not c.startswith("state-")]
    index["units"] = [c for c in present if c == "india" or c.startswith("state-")]
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, separators=(",", ":"))
    print(f"  {written} unit files, {total/1048576:.1f} MB")


if __name__ == "__main__":
    main()
