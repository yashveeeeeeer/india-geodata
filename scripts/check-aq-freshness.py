#!/usr/bin/env python3
"""Report how stale the published air quality feed is.

A feed that quietly stops updating is worse than one that is obviously missing:
the page keeps rendering, the numbers keep looking plausible, and nobody notices
for months. This is the check that makes that impossible to miss.

Prints a one-line status and exits 0 when fresh, 1 when stale, 2 when the feed is
missing or unreadable. Intended for a scheduled workflow that opens an issue on a
non-zero exit.

Usage:
    python scripts/check-aq-freshness.py [--max-age-hours 6]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-age-hours", type=float, default=6.0)
    ap.add_argument("--path", default=os.path.join(
        "docs", "projects", "air-quality", "data", "latest.json"))
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, args.path)

    if not os.path.exists(path):
        print("MISSING the feed has never been published")
        return 2
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"UNREADABLE {e}")
        return 2

    stamp = doc.get("updated") or doc.get("fetched")
    if not stamp:
        print("UNREADABLE the feed carries no timestamp")
        return 2
    try:
        when = datetime.fromisoformat(stamp)
    except ValueError:
        print(f"UNREADABLE cannot parse timestamp {stamp!r}")
        return 2
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)

    age = (datetime.now(timezone.utc) - when).total_seconds() / 3600
    pollutants = len(doc.get("pollutants") or {})
    stations = doc.get("stations", "?")
    summary = (f"age {age:.1f}h, {stations} monitors, {pollutants} pollutants, "
               f"updated {stamp}")

    if age > args.max_age_hours:
        print(f"STALE {summary}")
        return 1
    print(f"FRESH {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
