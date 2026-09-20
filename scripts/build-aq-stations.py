#!/usr/bin/env python3
"""Build the air quality project's station and city geography files.

Reads the station list from the India Air Quality Database API and writes two
small JSON files the page loads once:

    docs/projects/air-quality/data/stations.json   every monitor with coordinates
    docs/projects/air-quality/data/cities.json     monitors grouped by city

Values are not included here; they come from the hourly feed. This file only
answers "where are the monitors, and how many does each city have".

Usage:
    python scripts/build-aq-stations.py [--key KEY] [--out DIR]
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request

API = "https://airquality.xkdr.org/v1/stations?format=csv"
DEMO_KEY = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"   # published on airquality.xkdr.org

# Coordinates the source gets wrong, keyed by station id. A monitor's own
# registered address is the better evidence: the board that runs it named the
# place. Each entry says which address it was taken from so it can be rechecked.
CORRECTED = {
    # CPCB publishes 16.5038, 74.3623 for this one, which falls in Belagavi
    # district, Karnataka, 46 km southwest of the address it is registered at:
    # "Collector Office Premises, Near District Court, Sangli Miraj Road, Vijay
    # Nagar, Sangli". MPCB is Maharashtra's board and runs no monitors in
    # Karnataka. Uncorrected, Sangli's readings become part of Karnataka's state
    # average while every label on the page still reads Maharashtra.
    "site_5774": (16.84269, 74.60926, "Sangli collector office, Sangli-Miraj Road"),
}


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s).lower())).strip("-")


def fetch(key):
    req = urllib.request.Request(API, headers={"Authorization": f"Bearer {key}",
                                               "User-Agent": "india-geodata-build"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def num(v):
    try:
        f = float(v)
        return f if f == f else None          # drop NaN
    except (TypeError, ValueError):
        return None


def canonical_states(rows):
    """The source spells some states two ways ("Tamil Nadu" and "TamilNadu"), which
    would split a city into two entries. Collapse each group to the most
    word-separated spelling, breaking ties by how often it appears."""
    groups = {}
    for r in rows:
        s = (r.get("state_name") or "").strip()
        if s:
            groups.setdefault(re.sub(r"[^a-z0-9]", "", s.lower()), []).append(s)
    out = {}
    for key, seen in groups.items():
        best = max(set(seen), key=lambda v: (len(re.findall(r"[^A-Za-z0-9]", v)), seen.count(v)))
        for v in set(seen):
            out[v] = best
    return out


def build(rows):
    states = canonical_states(rows)
    fixed = sum(1 for r in rows
                if states.get((r.get("state_name") or "").strip()) not in
                (None, (r.get("state_name") or "").strip()))
    if fixed:
        print(f"  normalised {fixed} rows with variant state spellings")
    stations, cities = [], {}
    for r in rows:
        lat, lon = num(r.get("latitude")), num(r.get("longitude"))
        if lat is None or lon is None:
            continue                          # decommissioned monitors carry no coordinates
        if r["station_id"] in CORRECTED:
            lat, lon, why = CORRECTED[r["station_id"]]
            print(f"  moved {r['station_id']} to its registered address ({why})")
        city = (r.get("city_name") or "").strip()
        state = states.get((r.get("state_name") or "").strip(),
                           (r.get("state_name") or "").strip())
        if not city:
            continue
        stations.append({
            "id": r["station_id"],
            "name": (r.get("station_name") or "").strip(),
            "city": city,
            "state": state,
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "source": r.get("source", ""),
        })
        key = slug(f"{city}-{state}")
        c = cities.setdefault(key, {"id": key, "name": city, "state": state,
                                    "lat": 0.0, "lon": 0.0, "n": 0})
        c["lat"] += lat
        c["lon"] += lon
        c["n"] += 1

    out = []
    for c in cities.values():
        c["lat"] = round(c["lat"] / c["n"], 5)   # city point = centroid of its monitors
        c["lon"] = round(c["lon"] / c["n"], 5)
        out.append(c)
    out.sort(key=lambda c: (-c["n"], c["name"]))
    return stations, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("AQI_KEY", DEMO_KEY))
    ap.add_argument("--out", default=os.path.join("docs", "projects", "air-quality", "data"))
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, args.out)
    os.makedirs(out_dir, exist_ok=True)

    rows = fetch(args.key)
    stations, cities = build(rows)
    if not stations:
        sys.exit("no stations with coordinates returned")

    for name, payload in (("stations.json", stations), ("cities.json", cities)):
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
        print(f"  {len(payload):4d} -> {os.path.relpath(path, root)} "
              f"({os.path.getsize(path)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
