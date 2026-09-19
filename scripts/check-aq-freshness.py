#!/usr/bin/env python3
"""Report how stale the published air quality data is.

A feed that quietly stops updating is worse than one that is obviously missing:
the page keeps rendering, the numbers keep looking plausible, and nobody notices
for months. This is the check that makes that impossible to miss.

It watches three things, because they fail separately:

  the feed    latest.json still being refreshed by the hourly job
  the record  the days behind the map and chart still reaching the present
  the strip   every pollutant in national.json reaching as far as the record

The third one is here because it has already happened: national.json had no
writer, so the record moved on and the strip stayed where it was, and nothing
failed. A file that is merely out of step with its own source will not announce
itself, so something has to go looking.

Prints a line per check and exits 0 when all are fresh, 1 when something is
stale, 2 when something is missing or unreadable. Intended for a scheduled
workflow that opens an issue on a non-zero exit.

Usage:
    python scripts/check-aq-freshness.py [--max-age-hours 6] [--max-record-days 3]
                                         [--path docs/.../latest.json]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone


def load(path):
    """(doc, problem) — a problem string means do not trust the doc."""
    if not os.path.exists(path):
        return None, "has never been published"
    try:
        return json.load(open(path, encoding="utf-8")), None
    except (OSError, ValueError) as e:
        return None, str(e)


def check_record(data_dir, max_days):
    """The map and the chart read daily/index.json and the per-year matrices.
    If the newest day they carry stops moving, the page is frozen however fresh
    the hourly feed looks."""
    doc, problem = load(os.path.join(data_dir, "daily", "index.json"))
    if problem:
        print(f"UNREADABLE record: daily/index.json {problem}")
        return 2, None
    newest = doc.get("to")
    if not newest:
        print("UNREADABLE record: daily/index.json carries no end date")
        return 2, None
    try:
        last = datetime.strptime(newest, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        print(f"UNREADABLE record: cannot parse end date {newest!r}")
        return 2, None

    behind = (datetime.now(timezone.utc) - last) / timedelta(days=1)
    summary = f"newest day {newest}, {behind:.1f} days back"
    if behind > max_days:
        print(f"STALE record: {summary}")
        return 1, newest
    print(f"FRESH record: {summary}")
    return 0, newest


def check_strip(data_dir, newest):
    """national.json is derived from the national series, so every pollutant in
    it should reach as far as the record. Judged per pollutant on purpose: the
    obvious version takes the newest day across all six, and then one healthy
    pollutant vouches for five frozen ones — which is the very drift this is
    here to catch."""
    doc, problem = load(os.path.join(data_dir, "daily", "national.json"))
    if problem:
        print(f"UNREADABLE strip: daily/national.json {problem}")
        return 2
    if not isinstance(doc, dict) or not doc:
        print("UNREADABLE strip: daily/national.json holds no pollutants")
        return 2

    ends = {}
    for p, s in doc.items():
        days = s.get("t") if isinstance(s, dict) else None
        ends[p] = days[-1] if days else None
    if not newest:
        # the record could not be read, so there is nothing to measure against
        print("UNKNOWN strip: no record to compare against")
        return 0

    adrift = sorted(p for p, e in ends.items() if not e or e < newest)
    if adrift:
        detail = ", ".join(f"{p} {ends[p] or 'empty'}" for p in adrift)
        print(f"STALE strip: the record reaches {newest} but {detail}")
        return 1
    print(f"FRESH strip: all {len(ends)} pollutants reach {newest}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-age-hours", type=float, default=6.0)
    ap.add_argument("--max-record-days", type=float, default=3.0)
    ap.add_argument("--path", default=os.path.join(
        "docs", "projects", "air-quality", "data", "latest.json"))
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, args.path)
    data_dir = os.path.dirname(path)

    worst, newest = check_record(data_dir, args.max_record_days)
    worst = max(worst, check_strip(data_dir, newest))

    if not os.path.exists(path):
        print("MISSING feed: latest.json has never been published")
        return max(worst, 2)
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"UNREADABLE feed: {e}")
        return max(worst, 2)

    stamp = doc.get("updated") or doc.get("fetched")
    if not stamp:
        print("UNREADABLE feed: no timestamp")
        return max(worst, 2)
    try:
        when = datetime.fromisoformat(stamp)
    except ValueError:
        print(f"UNREADABLE feed: cannot parse timestamp {stamp!r}")
        return max(worst, 2)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)

    age = (datetime.now(timezone.utc) - when).total_seconds() / 3600
    pollutants = len(doc.get("pollutants") or {})
    stations = doc.get("stations", "?")
    summary = (f"age {age:.1f}h, {stations} monitors, {pollutants} pollutants, "
               f"updated {stamp}")

    if age > args.max_age_hours:
        print(f"STALE feed: {summary}")
        return max(worst, 1)
    print(f"FRESH feed: {summary}")
    return worst


if __name__ == "__main__":
    sys.exit(main())
