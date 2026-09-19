#!/usr/bin/env python3
"""Build every file the page reads from the hourly bulk archive.

The daily route could give the page its numbers but not its shape: an
hour-by-month grid cannot be reconstructed from daily means. This reads the raw
hourly readings instead, so the diurnal cycle is computed from what was actually
measured, for every place and the whole record rather than one borrowed year.

Writes, split by year so no one fetches a decade to draw one chart:

    docs/projects/air-quality/data/daily/<POLLUTANT>-<year>.json   per monitor
    docs/projects/air-quality/data/series/<id>/<year>.json         per place, daily
    docs/projects/air-quality/data/series/<id>/index.json          name, years, cycle

Readings average in two stages throughout — monitors into cities, then cities
into the state and the country — so a city with many monitors does not speak for
a whole state.

Usage:
    python scripts/build-aq-hourly-files.py [--cache .cache/aq-bulk]
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aq_national import write_national, write_series_index               # noqa: E402

import pandas as pd
import pyarrow.parquet as pq

POLLUTANTS = {"PM2.5", "PM10", "NO2", "CO", "OZONE", "NH3"}
ALIAS = {"Ozone": "OZONE"}
COLUMNS = ["station_id", "parameter_name", "collected_at", "value"]


# CO sits near 1 mg/m³ where one decimal is a ten per cent step, so it
# keeps two. Everything else is µg/m³, where one is plenty.
def dp(pollutant):
    return 2 if pollutant == "CO" else 1


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    return os.path.getsize(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(".cache", "aq-bulk"))
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = os.path.join(root, "docs", "projects", "air-quality", "data")
    daily_dir = os.path.join(data, "daily")
    series_dir = os.path.join(data, "series")
    cache = os.path.join(root, args.cache)

    stations = json.load(open(os.path.join(data, "stations.json"), encoding="utf-8"))
    cities = json.load(open(os.path.join(data, "cities.json"), encoding="utf-8"))
    coverage = json.load(open(os.path.join(data, "coverage.json"), encoding="utf-8"))
    unit_of = coverage.get("stationUnit", {})
    city_unit = coverage.get("cityUnit", {})
    state_name = {fid: v["name"] for fid, v in coverage.get("states", {}).items()}
    city_name = {c["id"]: c["name"] for c in cities}
    known = {s["id"] for s in stations}

    files = sorted(glob.glob(os.path.join(cache, "*.parquet")))
    if not files:
        raise SystemExit(f"nothing in {args.cache}; run fetch-aq-bulk.py first")

    for d in (daily_dir, series_dir):
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    by_year = defaultdict(list)
    for f in files:
        m = re.match(r"(\d{4})-(\d{2})\.parquet$", os.path.basename(f))
        if m:
            by_year[m.group(1)].append(f)

    # place -> pollutant -> (month, hour) -> running mean of city means
    cycle = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"s": 0.0, "n": 0})))
    years_by_place = defaultdict(set)
    place_names = {"india": "All India"}
    daily_index = defaultdict(list)
    span_lo = span_hi = None

    for year in sorted(by_year):
        day_station = defaultdict(lambda: defaultdict(dict))   # pol -> day -> sid -> mean
        city_day = defaultdict(lambda: defaultdict(dict))      # pol -> day -> cid -> (mean, n)

        for path in sorted(by_year[year]):
            df = pq.read_table(path, columns=COLUMNS).to_pandas()
            df["parameter_name"] = df["parameter_name"].replace(ALIAS)
            df = df[df["parameter_name"].isin(POLLUTANTS)]
            df = df[df["station_id"].isin(known)]
            df["collected_at"] = pd.to_datetime(df["collected_at"], errors="coerce")
            df = df.dropna(subset=["collected_at", "value"])
            if df.empty:
                continue
            df["day"] = df["collected_at"].dt.strftime("%Y-%m-%d")
            df["city"] = df["station_id"].map(lambda s: (unit_of.get(s) or {}).get("city"))

            st = (df.groupby(["parameter_name", "day", "station_id"], observed=True)["value"]
                    .mean().reset_index())
            for p, d, sid, v in zip(st["parameter_name"], st["day"],
                                    st["station_id"], st["value"]):
                day_station[p][d][sid] = round(float(v), dp(p))

            sub = df.dropna(subset=["city"])
            if not sub.empty:
                sc = (sub.groupby(["parameter_name", "day", "city", "station_id"], observed=True)["value"]
                        .mean().reset_index())
                cd = (sc.groupby(["parameter_name", "day", "city"], observed=True)["value"]
                        .agg(["mean", "size"]).reset_index())
                for p, d, c, mv, n in zip(cd["parameter_name"], cd["day"], cd["city"],
                                          cd["mean"], cd["size"]):
                    city_day[p][d][c] = (float(mv), int(n))

                # the hour-by-month shape, from the readings themselves
                sub = sub.copy()
                sub["month"] = sub["collected_at"].dt.month
                sub["hour"] = sub["collected_at"].dt.hour
                ch = (sub.groupby(["parameter_name", "month", "hour", "city"], observed=True)["value"]
                        .mean().reset_index())
                for p, mo, hr, c, v in zip(ch["parameter_name"], ch["month"], ch["hour"],
                                           ch["city"], ch["value"]):
                    places = ["india", c]
                    stv = (city_unit.get(c) or {}).get("state")
                    if stv:
                        places.append("state-" + str(stv))
                    for key in places:
                        cell = cycle[key][p][(int(mo), int(hr))]
                        cell["s"] += float(v)
                        cell["n"] += 1
            del df

        for p, days in day_station.items():
            ids = sorted({s for d in days.values() for s in d})
            dates = sorted(days)
            if not dates:
                continue
            write_json(os.path.join(daily_dir, f"{p}-{year}.json"),
                       {"pollutant": p, "year": year, "stations": ids, "t": dates,
                        "v": [[days[d].get(s) for s in ids] for d in dates]})
            daily_index[p].append(year)
            span_lo = dates[0] if span_lo is None or dates[0] < span_lo else span_lo
            span_hi = dates[-1] if span_hi is None or dates[-1] > span_hi else span_hi

        place_rows = defaultdict(lambda: defaultdict(dict))
        for p, days in city_day.items():
            for d, byc in days.items():
                per_state = defaultdict(lambda: {"v": [], "n": 0})
                all_v, all_n = [], 0
                for c, (mv, n) in byc.items():
                    place_rows[c][p][d] = (mv, n)
                    place_names.setdefault(c, city_name.get(c, c))
                    stv = (city_unit.get(c) or {}).get("state")
                    if stv:
                        per_state[str(stv)]["v"].append(mv)
                        per_state[str(stv)]["n"] += n
                    all_v.append(mv)
                    all_n += n
                for stv, acc in per_state.items():
                    key = "state-" + stv
                    place_names.setdefault(key, state_name.get(stv, key))
                    place_rows[key][p][d] = (sum(acc["v"]) / len(acc["v"]), acc["n"])
                if all_v:
                    place_rows["india"][p][d] = (sum(all_v) / len(all_v), all_n)

        for key, pols in place_rows.items():
            series = {}
            for p, days in pols.items():
                t = sorted(days)
                series[p] = {"t": t,
                             "v": [round(days[d][0], dp(p)) for d in t],
                             "n": [int(days[d][1]) for d in t]}
            if series:
                write_json(os.path.join(series_dir, key, f"{year}.json"), series)
                years_by_place[key].add(year)
        print(f"  {year}: {len(day_station)} pollutants, {len(place_rows)} places", flush=True)

    for key, years in years_by_place.items():
        entry = {"id": key, "name": place_names.get(key, key), "years": sorted(years)}
        grids = {}
        for p, cells in cycle.get(key, {}).items():
            grid = [[None] * 24 for _ in range(12)]
            for (mo, hr), acc in cells.items():
                if acc["n"]:
                    grid[mo - 1][hr] = round(acc["s"] / acc["n"], dp(p))
            grids[p] = grid
        if grids:
            entry["cycle"] = grids
        write_json(os.path.join(series_dir, key, "index.json"), entry)

    write_json(os.path.join(daily_dir, "index.json"),
               {"pollutants": {p: sorted(set(y)) for p, y in daily_index.items()},
                "from": span_lo, "to": span_hi})

    n_files = sum(len(fs) for _, _, fs in os.walk(series_dir))
    size = sum(os.path.getsize(os.path.join(dp, f))
               for dp, _, fs in os.walk(series_dir) for f in fs)
    dsize = sum(os.path.getsize(f) for f in glob.glob(os.path.join(daily_dir, "*.json")))
    print(f"  {len(years_by_place)} places, {n_files} series files, {size/1048576:.1f} MB")
    print(f"  daily matrices {dsize/1048576:.1f} MB, span {span_lo} to {span_hi}")

    n_pol, n_days, _ = write_national(data)
    print(f"  daily/national.json -> {n_pol} pollutants, up to {n_days} days")
    n_cities, n_places = write_series_index(data)
    print(f"  series/index.json -> {n_cities} cities, {n_places} places")


if __name__ == "__main__":
    main()
