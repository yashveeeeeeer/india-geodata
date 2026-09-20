#!/usr/bin/env python3
"""Fold the accumulated hourly archive into the files the page actually reads.

The hourly job captures readings and publishes them as Parquet, but nothing was
turning that into the daily matrices and series the map, chart and download use.
The archive grew while the page stayed frozen at its last hand-built snapshot —
which is exactly how a live feed quietly goes stale.

This closes that loop. It reads the day files from the archive release, works out
each monitor's daily mean, and merges those days into:

    docs/projects/air-quality/data/daily/<POLLUTANT>-<year>.json   per monitor
    docs/projects/air-quality/data/series/<city>.json              per city
    docs/projects/air-quality/data/series/india.json               national
    docs/projects/air-quality/data/series/state-<id>.json          per state

The archive holds what the feed said, and the feed reports the AQI sub-index
rather than the concentration, so every reading is converted here — before the
daily mean, because the sub-index bends at each band edge and averaging first
would put the kink in the wrong place.

Existing days are replaced, new days appended, so it is safe to run repeatedly.
Hour-by-month climatology is left alone: it is a long-run average and does not
move meaningfully day to day.

Usage:
    python scripts/rebuild-aq-from-archive.py --archive-dir .aq-archive
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aq_national import write_national, write_series_index, write_summary                 # noqa: E402
from aqi_scale import check_covered, to_concentration   # noqa: E402

POLLUTANTS = ["PM2.5", "PM10", "NO2", "CO", "OZONE", "NH3"]
check_covered(POLLUTANTS)


def norm(v):
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower())


def without_agency(v):
    return norm(str(v or "").rsplit(" - ", 1)[0])


def station_lookup(stations):
    """The archive names monitors; our files key them by id. The two sources
    disagree about the operator suffix, so fall back to the name without it."""
    exact, loose, clash = {}, {}, set()
    for st in stations:
        name = st.get("name")
        if not name:
            continue
        exact[norm(name)] = st["id"]
        b = without_agency(name)
        if b in loose and loose[b] != st["id"]:
            clash.add(b)
        loose[b] = st["id"]
    for b in clash:
        loose.pop(b, None)
    return exact, loose


def read_archive(archive_dir):
    files = sorted(glob.glob(os.path.join(archive_dir, "aq-*.parquet")))
    if not files:
        return None
    frames = []
    for f in files:
        try:
            frames.append(pd.read_parquet(f))
        except Exception as e:
            print(f"  ! skipping {os.path.basename(f)}: {e}")
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    print(f"  {len(files)} archive day(s), {len(df)} rows")
    return df


def station_daily(df, stations):
    """One mean per monitor, pollutant and day."""
    exact, loose = station_lookup(stations)

    def to_id(name):
        return exact.get(norm(name)) or loose.get(without_agency(name))

    df = df.copy()
    df["station_id"] = df["station"].map(to_id)
    df["pollutant_id"] = df["pollutant_id"].str.upper().replace({"OZONE": "OZONE"})
    df = df[df["pollutant_id"].isin(POLLUTANTS)]
    df = df.dropna(subset=["station_id", "avg_value", "collected_at"])
    # sub-index -> concentration, per reading, before anything is averaged
    df["avg_value"] = [to_concentration(p, v)
                       for p, v in zip(df["pollutant_id"], df["avg_value"])]
    df = df.dropna(subset=["avg_value"])
    df["day"] = pd.to_datetime(df["collected_at"]).dt.strftime("%Y-%m-%d")
    out = (df.groupby(["pollutant_id", "day", "station_id"], observed=True)["avg_value"]
             .mean().reset_index())
    print(f"  {out['station_id'].nunique()} monitors matched, "
          f"{out['day'].nunique()} day(s), {len(out)} monitor-days")
    return out


def merge_daily_matrix(path, pollutant, year, rows):
    """rows: {day: {station_id: value}} for this pollutant and year."""
    if os.path.exists(path):
        doc = json.load(open(path, encoding="utf-8"))
    else:
        doc = {"pollutant": pollutant, "year": year, "stations": [], "t": [], "v": []}

    table = {}
    for i, day in enumerate(doc["t"]):
        table[day] = {sid: doc["v"][i][j] for j, sid in enumerate(doc["stations"])
                      if doc["v"][i][j] is not None}
    for day, by_station in rows.items():
        table.setdefault(day, {}).update(by_station)

    ids = sorted({s for d in table.values() for s in d})
    dates = sorted(table)
    doc["stations"] = ids
    doc["t"] = dates
    doc["v"] = [[table[d].get(s) for s in ids] for d in dates]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, separators=(",", ":"))
    return len(dates), len(ids)


def merge_series(series_dir, name, key, rows):
    """rows: pollutant -> day -> (value, monitors). A place is a folder now: an
    index naming it and listing its years, and one file per year beside it."""
    folder = os.path.join(series_dir, key)
    os.makedirs(folder, exist_ok=True)

    by_year = defaultdict(lambda: defaultdict(dict))
    for p, days in rows.items():
        for day, val in days.items():
            by_year[day[:4]][p][day] = val

    for year, pols in by_year.items():
        path = os.path.join(folder, f"{year}.json")
        doc = {}
        if os.path.exists(path):
            try:
                doc = json.load(open(path, encoding="utf-8"))
            except ValueError as e:
                # Starting over would silently drop every day already in the file
                # and republish the year as whatever the last day or two of
                # archive happens to hold. Better to stop than to lose months.
                raise RuntimeError(f"cannot read {key}/{year}.json, "
                                   f"refusing to rebuild it from scratch: {e}") from e
        for p, days in pols.items():
            cur = doc.get(p) or {"t": [], "v": [], "n": []}
            merged = {t: (cur["v"][i], cur["n"][i]) for i, t in enumerate(cur["t"])}
            merged.update(days)
            t = sorted(merged)
            dp = 2 if p == "CO" else 1
            doc[p] = {"t": t,
                      "v": [round(merged[d][0], dp) for d in t],
                      "n": [int(merged[d][1]) for d in t]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, separators=(",", ":"))

    # keep the index honest about which years exist, without touching the cycle
    index_path = os.path.join(folder, "index.json")
    entry = {"id": key, "name": name, "years": []}
    if os.path.exists(index_path):
        try:
            entry = json.load(open(index_path, encoding="utf-8"))
        except ValueError:
            pass
    entry["id"] = key
    entry.setdefault("name", name)
    entry["years"] = sorted({f[:-5] for f in os.listdir(folder)
                             if f.endswith(".json") and f != "index.json"})
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(entry, f, separators=(",", ":"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-dir", default=".aq-archive")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = os.path.join(root, "docs", "projects", "air-quality", "data")
    daily_dir = os.path.join(data, "daily")
    series_dir = os.path.join(data, "series")

    stations = json.load(open(os.path.join(data, "stations.json"), encoding="utf-8"))
    cities = json.load(open(os.path.join(data, "cities.json"), encoding="utf-8"))
    coverage = json.load(open(os.path.join(data, "coverage.json"), encoding="utf-8"))
    unit_of = coverage.get("stationUnit", {})
    state_name = {fid: v["name"] for fid, v in coverage.get("states", {}).items()}
    city_name = {c["id"]: c for c in cities}

    df = read_archive(os.path.join(root, args.archive_dir))
    if df is None:
        print("  nothing in the archive yet")
        return 0

    sd = station_daily(df, stations)
    if sd.empty:
        print("  no usable readings")
        return 0

    # --- per-monitor matrices, the ones the map and download read ---
    by_py = defaultdict(lambda: defaultdict(dict))
    for p, day, sid, v in zip(sd["pollutant_id"], sd["day"], sd["station_id"], sd["avg_value"]):
        by_py[(p, day[:4])][day][sid] = round(float(v), 2 if p == "CO" else 1)
    for (p, year), rows in sorted(by_py.items()):
        path = os.path.join(daily_dir, f"{p}-{year}.json")
        n_days, n_ids = merge_daily_matrix(path, p, year, rows)
        print(f"  daily/{p}-{year}.json -> {n_days} days x {n_ids} monitors")

    index_path = os.path.join(daily_dir, "index.json")
    idx = {"pollutants": defaultdict(list)}
    for f in sorted(os.listdir(daily_dir)):
        m = re.match(r"(.+)-(\d{4})\.json$", f)
        if m:
            idx["pollutants"][m.group(1)].append(m.group(2))
    idx["pollutants"] = {k: sorted(v) for k, v in idx["pollutants"].items()}
    # the real span, so the date picker cannot offer days that hold nothing
    lo, hi = None, None
    for f in os.listdir(daily_dir):
        if not re.match(r".+-\d{4}\.json$", f):
            continue
        t = json.load(open(os.path.join(daily_dir, f), encoding="utf-8")).get("t") or []
        if t:
            lo = t[0] if lo is None or t[0] < lo else lo
            hi = t[-1] if hi is None or t[-1] > hi else hi
    idx["from"], idx["to"] = lo, hi
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, separators=(",", ":"))
    print(f"  span {lo} to {hi}")
    print("  daily/index.json -> " + ", ".join(
        f"{k} {'/'.join(v)}" for k, v in sorted(idx["pollutants"].items())))

    # --- city, state and national series, averaged in two stages ---
    city_rows = defaultdict(lambda: defaultdict(dict))
    unit_acc = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"vals": [], "n": 0})))
    per_city = defaultdict(list)
    for p, day, sid, v in zip(sd["pollutant_id"], sd["day"], sd["station_id"], sd["avg_value"]):
        u = unit_of.get(sid) or {}
        if u.get("city"):
            per_city[(p, day, u["city"])].append(float(v))

    for (p, day, cid), vals in per_city.items():
        mean = sum(vals) / len(vals)
        city_rows[cid][p][day] = (mean, len(vals))
        for unit in ("india", (coverage.get("cityUnit", {}).get(cid) or {}).get("state")):
            if unit:
                cell = unit_acc[unit][p][day]
                cell["vals"].append(mean)
                cell["n"] += len(vals)

    for cid, rows in city_rows.items():
        c = city_name.get(cid)
        merge_series(series_dir, c["name"] if c else cid, cid, rows)
    print(f"  {len(city_rows)} city series updated")

    for unit, rows in unit_acc.items():
        key = "india" if unit == "india" else f"state-{unit}"
        name = "All India" if unit == "india" else state_name.get(str(unit), key)
        flat = {p: {d: (sum(a["vals"]) / len(a["vals"]), a["n"]) for d, a in days.items()}
                for p, days in rows.items()}
        merge_series(series_dir, name, key, flat)
    print(f"  {len(unit_acc)} unit series updated")

    # the strip reads one file spanning every year; rebuild it from what we just
    # wrote, so it cannot fall behind the chart beside it
    n_pol, n_days, _ = write_national(data)
    print(f"  daily/national.json -> {n_pol} pollutants, up to {n_days} days")
    n_cities, n_places = write_series_index(data)
    print(f"  series/index.json -> {n_cities} cities, {n_places} places")
    summary = write_summary(data, root)
    print(f"  _data/air_quality.json -> {summary['stations']} stations, "
          f"{summary['cities']} cities, {summary['from']} to {summary['to']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
