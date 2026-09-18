#!/usr/bin/env python3
"""Fold hourly snapshots into the day's Parquet file.

The raw archive is deliberately kept out of git: an hourly commit of a growing
data file would put gigabytes into the repository's history within a year. It
lives as a GitHub Release asset instead, which carries no history.

This reads the snapshot CSVs written by fetch-aq-latest.py, merges them into
today's Parquet (downloading the existing one first if the release has it), and
writes it back out for the workflow to upload.

Usage:
    python scripts/append-aq-archive.py --snapshot-dir .aq-snapshots --out .aq-archive
"""

import argparse
import glob
import os
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

IST = timezone(timedelta(hours=5, minutes=30))
KEEP = ["state", "city", "station", "collected_at", "pollutant_id",
        "min_value", "max_value", "avg_value", "latitude", "longitude"]


def read_snapshots(snap_dir):
    files = sorted(glob.glob(os.path.join(snap_dir, "aq-*.csv")))
    if not files:
        return None, []
    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)
        except Exception as e:                      # a truncated snapshot must not stop the run
            print(f"  ! skipping {os.path.basename(f)}: {e}")
            continue
        if not len(df):
            continue
        frames.append(df)
    if not frames:
        return None, files
    return pd.concat(frames, ignore_index=True), files


def normalise(df):
    df = df.rename(columns={"last_update": "collected_at"})
    for c in KEEP:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[KEEP]
    df["collected_at"] = pd.to_datetime(df["collected_at"], format="%d-%m-%Y %H:%M:%S",
                                        errors="coerce")
    for c in ("min_value", "max_value", "avg_value", "latitude", "longitude"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["collected_at", "station", "pollutant_id"])
    # one reading per station, pollutant and timestamp: reruns and overlapping
    # snapshots must not inflate the archive
    return df.drop_duplicates(subset=["station", "pollutant_id", "collected_at"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot-dir", default=".aq-snapshots")
    ap.add_argument("--out", default=".aq-archive")
    ap.add_argument("--existing", default="", help="previously published Parquet to merge into")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    snap_dir = os.path.join(root, args.snapshot_dir)
    out_dir = os.path.join(root, args.out)
    os.makedirs(out_dir, exist_ok=True)

    fresh, files = read_snapshots(snap_dir)
    if fresh is None:
        print("  no snapshots to fold in")
        return 0
    fresh = normalise(fresh)
    print(f"  {len(files)} snapshot(s) -> {len(fresh)} rows")

    if args.existing and os.path.exists(args.existing):
        prior = pd.read_parquet(args.existing)
        before = len(prior)
        fresh = pd.concat([prior, fresh], ignore_index=True)
        fresh = fresh.drop_duplicates(subset=["station", "pollutant_id", "collected_at"])
        print(f"  merged with {before} existing rows -> {len(fresh)}")

    fresh = fresh.sort_values(["station", "pollutant_id", "collected_at"])
    day = datetime.now(IST).strftime("%Y-%m-%d")
    out = os.path.join(out_dir, f"aq-{day}.parquet")
    fresh.to_parquet(out, index=False, compression="zstd")
    print(f"  -> {os.path.relpath(out, root)} "
          f"({len(fresh)} rows, {os.path.getsize(out)/1024:.0f} KB)")

    # Snapshots are deliberately left in place. The caller deletes them only once
    # the Parquet has been published; dropping them here would lose the hour if
    # that upload failed. Re-folding the same snapshot is harmless — the rows
    # de-duplicate on (station, pollutant, timestamp).
    return 0


if __name__ == "__main__":
    sys.exit(main())
