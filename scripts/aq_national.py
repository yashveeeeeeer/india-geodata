#!/usr/bin/env python3
"""Write the national daily mean the time strip is drawn from.

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
