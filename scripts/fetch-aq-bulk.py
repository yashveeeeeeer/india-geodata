#!/usr/bin/env python3
"""Download the archive's monthly Parquet files.

These hold the raw hourly readings. The published demo key is refused for
anything but 2024, so this needs a key of its own — free from
airquality.xkdr.org — passed as AQI_KEY.

Going through the bulk files rather than the query API matters for two reasons:
the readings arrive hourly rather than as daily means, which is what the
hour-by-hour shape is built from, and a key of your own has no row cap, so a
month is one download instead of dozens of paged requests.

Already-downloaded months are skipped, so this can be stopped and restarted.

    .cache/aq-bulk/<year>-<month>.parquet

Usage:
    python scripts/fetch-aq-bulk.py --start 2009 --end 2025
"""

import argparse
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://airquality.xkdr.org/v1/files/v1/measurements"


def download(year, month, key, cache, tries=4):
    dest = os.path.join(cache, f"{year}-{month:02d}.parquet")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest, 0
    url = f"{BASE}/year={year}/month={month:02d}/data.parquet"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}",
                                               "User-Agent": "india-geodata-build"})
    delay = 5
    for attempt in range(tries):
        try:
            tmp = dest + ".part"
            with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            os.replace(tmp, dest)
            return dest, os.path.getsize(dest)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, 0                      # month simply not published
            if e.code == 403:
                raise SystemExit(
                    "403 from the archive. The published demo key only serves 2024; "
                    "set AQI_KEY to a key of your own from airquality.xkdr.org.")
            if attempt == tries - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 60)
        except urllib.error.URLError:
            if attempt == tries - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 60)
    return None, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2009)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--key", default=os.environ.get("AQI_KEY", ""))
    ap.add_argument("--cache", default=os.path.join(".cache", "aq-bulk"))
    args = ap.parse_args()

    if not args.key:
        sys.exit("no key: set AQI_KEY or pass --key")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache = os.path.join(root, args.cache)
    os.makedirs(cache, exist_ok=True)

    total, got, missing = 0, 0, 0
    for year in range(args.start, args.end + 1):
        for month in range(1, 13):
            path, size = download(year, month, args.key, cache)
            if path is None:
                missing += 1
                continue
            got += 1
            total += size
            if size:
                print(f"  {year}-{month:02d}  {size/1048576:6.1f} MB", flush=True)
    print(f"  {got} month files, {total/1048576:.0f} MB downloaded, {missing} not published")


if __name__ == "__main__":
    sys.exit(main())
