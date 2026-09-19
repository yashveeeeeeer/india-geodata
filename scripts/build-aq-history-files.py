#!/usr/bin/env python3
"""Turn the cached history into the files the page reads, split by year.

Holding every year in one file per place would mean fetching Delhi's whole record
to draw one chart — well over half a megabyte for a page that only ever shows a
slice of it. So each place gets a folder: a small index carrying its name, the
years it has and its hour-by-month shape, and one file per year beside it.

    docs/projects/air-quality/data/daily/<POLLUTANT>-<year>.json   per monitor
    docs/projects/air-quality/data/series/<id>/index.json          name, years, cycle
    docs/projects/air-quality/data/series/<id>/<year>.json         that year, daily

Places with nothing in a year simply have no file for it, so the early years cost
almost nothing — in 2009 barely a dozen monitors were running.

Usage:
    python scripts/build-aq-history-files.py [--cache .cache/aq-history]
"""

import argparse
import csv
import glob
import json
import os
import shutil
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aq_national import write_national, write_series_index               # noqa: E402

POLLUTANTS = {"PM2.5", "PM10", "NO2", "CO", "OZONE", "NH3"}
ALIAS = {"OZONE": "OZONE", "Ozone": "OZONE"}


# CO sits near 1 mg/m³ where one decimal is a ten per cent step, so it
# keeps two. Everything else is µg/m³, where one is plenty.
def dp(pollutant):
    return 2 if pollutant == "CO" else 1


def read_year(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = ALIAS.get(r.get("parameter_name"), r.get("parameter_name"))
            if p not in POLLUTANTS:
                continue
            try:
                v = float(r["mean"])
            except (TypeError, ValueError, KeyError):
                continue
            if v != v:
                continue
            day = (r.get("period_start") or "")[:10]
            if len(day) != 10:
                continue
            rows.append((p, day, r["station_id"], v))
    return rows


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    return os.path.getsize(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(".cache", "aq-history"))
    ap.add_argument("--keep-existing", action="store_true",
                    help="do not clear the series folder first")
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
    state_name = {fid: v["name"] for fid, v in coverage.get("states", {}).items()}
    city_name = {c["id"]: c["name"] for c in cities}
    known = {s["id"] for s in stations}

    files = sorted(glob.glob(os.path.join(cache, "*.csv")))
    if not files:
        raise SystemExit(f"nothing cached in {args.cache}; run backfill-aq-history.py first")

    # The hour-by-month shape was built from hourly readings; the history cache
    # holds daily means, so it cannot be recomputed here. Carry it across.
    cycles = {}
    if os.path.isdir(series_dir):
        for f in glob.glob(os.path.join(series_dir, "*.json")):
            key = os.path.basename(f)[:-5]
            if key == "index":
                continue
            try:
                doc = json.load(open(f, encoding="utf-8"))
            except ValueError:
                continue
            if doc.get("cycle"):
                cycles[key] = doc["cycle"]
        for f in glob.glob(os.path.join(series_dir, "*", "index.json")):
            key = os.path.basename(os.path.dirname(f))
            try:
                doc = json.load(open(f, encoding="utf-8"))
            except ValueError:
                continue
            if doc.get("cycle"):
                cycles.setdefault(key, doc["cycle"])
    print(f"  carried {len(cycles)} hour-by-month grids across")

    if not args.keep_existing and os.path.isdir(series_dir):
        shutil.rmtree(series_dir)
    os.makedirs(series_dir, exist_ok=True)
    os.makedirs(daily_dir, exist_ok=True)
    for f in glob.glob(os.path.join(daily_dir, "*.json")):
        os.remove(f)

    years_by_place = defaultdict(set)
    place_names = {"india": "All India"}
    span_lo, span_hi = None, None
    daily_index = defaultdict(list)

    for path in files:
        if os.path.getsize(path) == 0:
            continue
        year = os.path.basename(path)[:4]
        rows = read_year(path)
        if not rows:
            continue

        # --- per monitor, for the map and the download ---
        by_pol = defaultdict(lambda: defaultdict(dict))
        for p, day, sid, v in rows:
            if sid in known:
                by_pol[p][day][sid] = round(v, dp(p))
        for p, days in by_pol.items():
            ids = sorted({s for d in days.values() for s in d})
            dates = sorted(days)
            write_json(os.path.join(daily_dir, f"{p}-{year}.json"),
                       {"pollutant": p, "year": year, "stations": ids, "t": dates,
                        "v": [[days[d].get(s) for s in ids] for d in dates]})
            daily_index[p].append(year)
            if dates:
                span_lo = dates[0] if span_lo is None or dates[0] < span_lo else span_lo
                span_hi = dates[-1] if span_hi is None or dates[-1] > span_hi else span_hi

        # --- monitors into cities, then cities into state and country ---
        per_city = defaultdict(list)
        for p, day, sid, v in rows:
            u = unit_of.get(sid) or {}
            if u.get("city"):
                per_city[(u["city"], p, day)].append(v)

        place_rows = defaultdict(lambda: defaultdict(dict))
        unit_vals = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"v": [], "n": 0})))
        for (cid, p, day), vals in per_city.items():
            mean = sum(vals) / len(vals)
            place_rows[cid][p][day] = (mean, len(vals))
            place_names.setdefault(cid, city_name.get(cid, cid))
            st = (coverage.get("cityUnit", {}).get(cid) or {}).get("state")
            for unit in ("india", st):
                if not unit:
                    continue
                cell = unit_vals[unit][p][day]
                cell["v"].append(mean)
                cell["n"] += len(vals)

        for unit, pols in unit_vals.items():
            key = "india" if unit == "india" else f"state-{unit}"
            place_names.setdefault(key, "All India" if unit == "india"
                                   else state_name.get(str(unit), key))
            for p, days in pols.items():
                for day, cell in days.items():
                    place_rows[key][p][day] = (sum(cell["v"]) / len(cell["v"]), cell["n"])

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
        print(f"  {year}: {len(by_pol)} pollutants, {len(place_rows)} places", flush=True)

    # --- each place's index: what it is, which years it has ---
    for key, years in years_by_place.items():
        entry = {"id": key, "name": place_names.get(key, key), "years": sorted(years)}
        if cycles.get(key):
            entry["cycle"] = cycles[key]
        write_json(os.path.join(series_dir, key, "index.json"), entry)

    with open(os.path.join(daily_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"pollutants": {p: sorted(set(y)) for p, y in daily_index.items()},
                   "from": span_lo, "to": span_hi}, f, separators=(",", ":"))

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
