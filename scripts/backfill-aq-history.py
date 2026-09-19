#!/usr/bin/env python3
"""Pull the whole CAAQM record, 2009 onwards, into a local cache.

The bulk Parquet files need a key of their own, but the query API serves every
year and is not fussy about which. So this walks the record a window at a time,
asking for every station and every pollutant at once, and halves the window
whenever a response comes back truncated — early years go a month per request,
recent ones a few days.

Writes one CSV per year into the cache, and skips years already written, so it
can be stopped and restarted without losing work.

    .cache/aq-history/<year>.csv

Usage:
    python scripts/backfill-aq-history.py --start 2009 --end 2025
"""

import argparse
import csv
import datetime as dt
import io
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://airquality.xkdr.org/v1/measurements"
DEMO_KEY = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"
FIELDS = ["station_id", "parameter_name", "unit", "period_start", "mean", "min", "max", "n"]


def fetch(start, end, key, pause, tries=5):
    q = urllib.parse.urlencode({"start": start, "end": end, "agg": "daily", "format": "csv"})
    req = urllib.request.Request(f"{API}?{q}",
                                 headers={"Authorization": f"Bearer {key}",
                                          "User-Agent": "india-geodata-build"})
    delay = 4
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                truncated = r.headers.get("X-Truncated") == "true"
                rows = list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))
            if pause:
                time.sleep(pause)
            return rows, truncated
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == tries - 1:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or delay
            print(f"      HTTP {e.code}, waiting {wait}s", flush=True)
            time.sleep(wait)
            delay = min(delay * 2, 120)
        except urllib.error.URLError:
            if attempt == tries - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 120)
    return [], False


def walk(d0, d1, key, pause, depth=0):
    """Ask for [d0, d1]. A truncated answer means the cap was hit, so halve it.
    Without this the dense years silently lose stations."""
    rows, truncated = fetch(d0.isoformat(), d1.isoformat(), key, pause)
    if not truncated or d0 == d1 or depth > 8:
        return rows
    mid = d0 + (d1 - d0) // 2
    return (walk(d0, mid, key, pause, depth + 1)
            + walk(mid + dt.timedelta(days=1), d1, key, pause, depth + 1))


def year_windows(year):
    """A month at a time; walk() splits further wherever that is too much."""
    d = dt.date(year, 1, 1)
    while d.year == year:
        nxt = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        yield d, min(nxt - dt.timedelta(days=1), dt.date(year, 12, 31))
        d = nxt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2009)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--key", default=os.environ.get("AQI_KEY", DEMO_KEY))
    ap.add_argument("--cache", default=os.path.join(".cache", "aq-history"))
    ap.add_argument("--pause", type=float, default=0.25)
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache = os.path.join(root, args.cache)
    os.makedirs(cache, exist_ok=True)

    for year in range(args.start, args.end + 1):
        out = os.path.join(cache, f"{year}.csv")
        if os.path.exists(out) and os.path.getsize(out) > 0:
            print(f"  {year}: already cached")
            continue
        got = []
        for d0, d1 in year_windows(year):
            try:
                rows = walk(d0, d1, args.key, args.pause)
            except urllib.error.HTTPError as e:
                print(f"  {year}-{d0.month:02d}: HTTP {e.code}, skipped", file=sys.stderr)
                continue
            got.extend(rows)
            print(f"  {year}-{d0.month:02d}: {len(rows):6d} rows "
                  f"(running {len(got)})", flush=True)
        if not got:
            print(f"  {year}: nothing returned")
            open(out, "w").close()          # remember it was tried
            continue
        tmp = out + ".part"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(got)
        os.replace(tmp, out)
        print(f"  {year}: {len(got)} rows -> {os.path.relpath(out, root)} "
              f"({os.path.getsize(out)/1048576:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
