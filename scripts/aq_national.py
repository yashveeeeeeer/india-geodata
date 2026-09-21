#!/usr/bin/env python3
"""Write the small files the page reads that are derived from the series folder.

Three of them, each rebuilt from what it describes rather than accumulated, so
none can drift away from it.

The strip spans the whole record — seventeen years — and it has to draw before
anything else loads, so it cannot pull a matrix per year to do it. It reads one
small file instead: daily/national.json, the national daily mean per pollutant
for every day we hold.

That file used to have no writer at all. It was built once by hand, so the strip
would have frozen on the day it was made while the rest of the page moved on:
the chart would gain a day, the strip would not, and the two would drift apart
without anything failing. This makes it a derived file, rebuilt from
series/india/<year>.json by whatever last touched those, so it cannot go stale
on its own.

Deriving it rather than accumulating it also means it cannot disagree with the
chart. Both come from the same numbers.

The second is series/index.json, the list of places whose series exist. The map
gives those cities a darker rim, so you can tell at a glance which dot has a
record behind it. The script that used to write it left the pipeline, and
nothing took it over — so the file 404ed on every page load, seriesIndex stayed
empty, and every dot looked alike.

The third is _data/air_quality.json, the handful of figures the Projects card
prints. It used to be typed into the page — "6 pollutants, 558 stations" — and
558 was never a number this project held: there are 496 monitors on the roster
and around 450 reporting in a given hour. A figure nobody recomputes is a figure
that drifts, so this one is counted.

It carries the span of the record and, beside it, how many pollutants hold every
year of that span. The span on its own reads as a record all six have kept since
2009: PM10 only starts in 2011 and skips 2012, and four of them hold no 2025.

Usage:
    python scripts/aq_national.py [--data docs/projects/air-quality/data]
"""

import argparse
import glob
import json
import os
import re


def build_national(data_dir):
    """What daily/national.json should contain, as a dict, without writing it.

    Kept separate from writing so the freshness check can ask for the same
    answer and compare: a file that merely disagrees with its own source is
    exactly the failure this whole thing exists to catch, and it cannot be
    caught by looking at the file alone.

    Raises rather than returning something short. A year that will not parse
    would otherwise lop its months off the strip while the run still reported
    success, and the nightly job would commit the truncated version."""
    series_dir = os.path.join(data_dir, "series", "india")

    by_pollutant = {}
    for path in sorted(glob.glob(os.path.join(series_dir, "*.json"))):
        year = os.path.basename(path)[:-5]
        if not re.fullmatch(r"\d{4}", year):
            continue                       # index.json and anything else
        try:
            doc = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise RuntimeError(f"cannot read {os.path.basename(path)} in "
                               f"series/india: {e}") from e
        if not isinstance(doc, dict):
            raise RuntimeError(f"series/india/{year}.json is not an object")
        for pollutant, s in doc.items():
            if not isinstance(s, dict):
                raise RuntimeError(f"series/india/{year}.json: {pollutant} is "
                                   f"not an object")
            t, v = s.get("t") or [], s.get("v") or []
            if len(t) != len(v):
                raise RuntimeError(f"series/india/{year}.json: {pollutant} has "
                                   f"{len(t)} days but {len(v)} values")
            by_pollutant.setdefault(pollutant, {}).update(zip(t, v))

    payload = {}
    for pollutant, table in by_pollutant.items():
        days = sorted(table)
        payload[pollutant] = {"t": days, "v": [table[d] for d in days]}

    if not payload:
        raise RuntimeError(f"nothing to build from in {series_dir}")
    return payload


def write_national(data_dir):
    """Write daily/national.json. Returns (pollutants, days, path)."""
    payload = build_national(data_dir)
    out = os.path.join(data_dir, "daily", "national.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    return len(payload), max(len(s["t"]) for s in payload.values()), out


def build_series_index(data_dir):
    """The places that have a series, so the map can mark them.

    Read off the folders rather than kept as a separate tally: a place has a
    record exactly when there is a folder holding one. Separate from writing for
    the same reason as build_national — the check needs the same answer."""
    series_dir = os.path.join(data_dir, "series")
    if not os.path.isdir(series_dir):
        raise RuntimeError(f"no series folder at {series_dir}")

    places = sorted(name for name in os.listdir(series_dir)
                    if os.path.isfile(os.path.join(series_dir, name, "index.json")))
    if not places:
        raise RuntimeError(f"no places with a series in {series_dir}")

    # The map only marks city dots, but the state and country rollups live here
    # too and cost a few bytes, so anything that wants them has them.
    cities = [p for p in places if not p.startswith("state-") and p != "india"]
    return {"cities": cities, "places": places}


def write_series_index(data_dir):
    """Write series/index.json. Returns (cities, places)."""
    payload = build_series_index(data_dir)
    out = os.path.join(data_dir, "series", "index.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    return len(payload["cities"]), len(payload["places"])


def span_years(index):
    """First and last year of the record, off the two dates daily/index.json
    carries. The card slices the year out of both, so a date it cannot slice is
    a date that reaches the page as four characters of nonsense."""
    edges = []
    for edge in ("from", "to"):
        value = index.get(edge)
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise RuntimeError(f"daily/index.json: {edge} is {value!r}, and the "
                               f"card prints the year out of it")
        edges.append(int(value[:4]))
    first, last = edges
    if first > last:
        raise RuntimeError(f"daily/index.json runs from {first} back to {last}")
    return first, last


def build_summary(data_dir):
    """What the Projects card says about this project, counted rather than typed.

    The span is the outer envelope of everything we hold, and printed on its own
    it promises something the record does not keep: PM10 only starts in 2011 and
    skips 2012, and four of the six hold no 2025 at all. One earliest year read
    as if every pollutant had it is the overstatement this counts against — the
    card gets the number of pollutants that really do hold every year of the
    span, off the same index the span itself comes from."""
    def load(name):
        with open(os.path.join(data_dir, name), encoding="utf-8") as f:
            return json.load(f)

    try:
        stations = load("stations.json")
        cities = load("cities.json")
        index = load(os.path.join("daily", "index.json"))
    except (OSError, ValueError) as e:
        raise RuntimeError(f"cannot read what the card counts: {e}") from e

    # Shapes, not just emptiness. A string where a list belongs would otherwise
    # be counted by its characters and published as a station count.
    if not isinstance(stations, list) or not isinstance(cities, list):
        raise RuntimeError("stations.json and cities.json should each be a list")
    if not isinstance(index, dict):
        raise RuntimeError("daily/index.json should be an object")
    held = index.get("pollutants")
    if held and not isinstance(held, dict):
        raise RuntimeError("daily/index.json should give each pollutant the years it holds")
    pollutants = sorted(held or {})
    if not (stations and cities and pollutants):
        raise RuntimeError("cannot count the project without stations, cities and days")

    first, last = span_years(index)
    if last - first < 1:
        raise RuntimeError(f"the record spans a single year ({first}); the card "
                           f"describes a range, so this is almost certainly a "
                           f"half-built rebuild rather than the real span")
    record = {str(y) for y in range(first, last + 1)}
    whole = 0
    for pollutant in pollutants:
        years = held[pollutant]
        if not isinstance(years, list):
            raise RuntimeError(f"daily/index.json: {pollutant} should carry a "
                               f"list of the years it holds")
        if not years:
            raise RuntimeError(f"daily/index.json: {pollutant} holds no years, "
                               f"and the card counts the years each one holds")
        if any(not isinstance(y, str) or not re.fullmatch(r"\d{4}", y) for y in years):
            raise RuntimeError(f"daily/index.json: {pollutant} lists something "
                               f"that is not a year")
        if record <= set(years):
            whole += 1

    return {
        "pollutants": len(pollutants),
        "stations": len({s.get("id") for s in stations}),
        "cities": len({c.get("id") for c in cities}),
        "from": index.get("from"),
        "to": index.get("to"),
        "unbroken": whole,
    }


def write_summary(data_dir, root):
    """Write docs/_data/air_quality.json, which the Projects card reads."""
    payload = build_summary(data_dir)
    out = os.path.join(root, "docs", "_data", "air_quality.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(
        "docs", "projects", "air-quality", "data"))
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        n_pol, n_days, out = write_national(os.path.join(root, args.data))
    except (RuntimeError, OSError, TypeError, AttributeError) as e:
        print(f"  {e}")
        return 1
    print(f"  daily/national.json -> {n_pol} pollutants, up to {n_days} days "
          f"({os.path.getsize(out) / 1024:.0f} KB)")
    n_cities, n_places = write_series_index(os.path.join(root, args.data))
    print(f"  series/index.json -> {n_cities} cities, {n_places} places")
    summary = write_summary(os.path.join(root, args.data), root)
    print(f"  _data/air_quality.json -> {summary['pollutants']} pollutants, "
          f"{summary['stations']} stations, {summary['cities']} cities, "
          f"{summary['from']} to {summary['to']}, {summary['unbroken']} of "
          f"{summary['pollutants']} holding every year of that")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
