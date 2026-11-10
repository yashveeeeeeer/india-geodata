#!/usr/bin/env python3
"""Run the hourly air-quality fetch from a computer that can reach CPCB.

Since 16 October 2026 CPCB (airquality.cpcb.gov.in) and data.gov.in refuse
connections from GitHub's hosted runners, on Linux, Windows and macOS alike, so
.github/workflows/aq-hourly.yml runs every hour and publishes nothing. Both
answer from an ordinary connection in India. This script does the same steps as
that workflow, from such a computer:

  1. bring a dedicated clone up to date with origin/main
  2. fetch the current hour (scripts/fetch-aq-latest.py)
  3. fold the snapshot into today's Parquet in the aq-live release
  4. commit the refreshed latest.json and push it

It works in its own clone, never in a working copy someone is editing. The clone
is partial and sparse (only scripts/ and the air-quality data), so it stays small
although the repository's history is over a gigabyte. The first run creates it.
Keep it on an NTFS drive: on exFAT or FAT git refuses the folder ("dubious
ownership") because those file systems record no owner.

A push from here starts the site build like any other push, so the map updates
without the workflow_run chain the GitHub job needs.

Usage:
    python scripts/aq-hourly-local.py --clone C:/india-geodata-aq/repo
    python scripts/aq-hourly-local.py --clone C:/india-geodata-aq/repo --dry-run

--dry-run does every step except uploading the archive and pushing, and says
what it would have published. --log FILE appends everything to FILE instead of
the console; scripts/install-aq-hourly-task.ps1 sets this up as an hourly task.

Needs git, the gh CLI signed in with write access to the repository, and Python
with pandas and pyarrow. Exits non-zero when the hour could not be published;
nothing is published unless every step before the push succeeds.
"""

import argparse
import glob
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

REMOTE = "https://github.com/yashveeeeeeer/india-geodata.git"
REPO = "yashveeeeeeer/india-geodata"
RELEASE = "aq-live"
IST = timezone(timedelta(hours=5, minutes=30))
SPARSE = ["scripts", "docs/projects/air-quality/data", "docs/_data"]
PUBLISHED = ["docs/projects/air-quality/data/latest.json", "docs/_data/air_quality.json"]
LOCK_STALE_SECONDS = 50 * 60
LOG_KEEP_BYTES = 2_000_000
# pythonw has no console; without this every git, gh and python call it starts
# would flash a console window on the desktop once an hour.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def log(msg):
    print(f"[{datetime.now(IST):%Y-%m-%d %H:%M:%S} IST] {msg}", flush=True)


def run(cmd, cwd=None, check=True):
    log("$ " + " ".join(cmd))
    res = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, encoding="utf-8",
                         errors="replace", creationflags=NO_WINDOW)
    for line in (res.stdout + res.stderr).strip().splitlines():
        print("    " + line, flush=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"{cmd[0]} exited {res.returncode}")
    return res


def ensure_clone(clone):
    if os.path.isdir(os.path.join(clone, ".git")):
        return
    log(f"creating a partial, sparse clone in {clone}")
    os.makedirs(os.path.dirname(os.path.abspath(clone)), exist_ok=True)
    run(["git", "clone", "--filter=blob:none", "--sparse", "--branch", "main", REMOTE, clone])
    run(["git", "sparse-checkout", "set"] + SPARSE, cwd=clone)


def update_clone(clone):
    status = run(["git", "status", "--porcelain"], cwd=clone).stdout.strip()
    if status:
        # A run that died before cleaning up can leave latest.json modified. Only
        # files this script writes are allowed to be dirty; anything else means a
        # person is using the clone, so stop rather than touch their work.
        dirty = [line[3:] for line in status.splitlines()]
        foreign = [p for p in dirty if p not in PUBLISHED and not p.startswith((".aq-snapshots", ".aq-archive"))]
        if foreign:
            raise RuntimeError("the clone has changes this script did not make: " + ", ".join(foreign))
        run(["git", "checkout", "--"] + [p for p in dirty if p in PUBLISHED], cwd=clone)
    run(["git", "pull", "--rebase", "--quiet", "origin", "main"], cwd=clone)


def fetch_hour(clone):
    for old in glob.glob(os.path.join(clone, ".aq-snapshots", "aq-*.csv")):
        os.remove(old)   # anything left here was never published; this hour replaces it
    res = run([sys.executable, "scripts/fetch-aq-latest.py", "--snapshot-dir", ".aq-snapshots"],
              cwd=clone, check=False)
    if res.returncode != 0:
        for f in glob.glob(os.path.join(clone, ".aq-snapshots", "aq-*.csv")):
            os.remove(f)
        run(["git", "checkout", "--", PUBLISHED[0]], cwd=clone, check=False)
        return False
    return True


def publish_archive(clone, dry_run):
    day = datetime.now(IST).strftime("%Y-%m-%d")
    name = f"aq-{day}.parquet"
    archive = os.path.join(clone, ".aq-archive")
    os.makedirs(archive, exist_ok=True)
    for old in glob.glob(os.path.join(archive, "aq-*.parquet")):
        os.remove(old)
    assets = run(["gh", "release", "view", RELEASE, "--repo", REPO, "--json", "assets",
                  "--jq", ".assets[].name"], cwd=clone).stdout.split()
    existing = ""
    if name in assets:
        # it must download cleanly before we rewrite it, or the day's earlier hours are lost
        run(["gh", "release", "download", RELEASE, "--repo", REPO, "--pattern", name,
             "--dir", archive, "--clobber"], cwd=clone)
        existing = os.path.join(archive, name)
    run([sys.executable, "scripts/append-aq-archive.py", "--snapshot-dir", ".aq-snapshots",
         "--out", ".aq-archive", "--existing", existing], cwd=clone)
    built = os.path.join(archive, name)
    if not os.path.exists(built):
        raise RuntimeError(f"append-aq-archive.py did not write {name}")
    if dry_run:
        log(f"dry run: would upload {name} ({os.path.getsize(built) / 1024:.0f} KB) to {RELEASE}")
        return
    run(["gh", "release", "upload", RELEASE, built, "--repo", REPO, "--clobber"], cwd=clone)
    for f in glob.glob(os.path.join(clone, ".aq-snapshots", "aq-*.csv")):
        os.remove(f)


def commit_and_push(clone, dry_run):
    if dry_run:
        changed = run(["git", "diff", "--stat", "--"] + PUBLISHED, cwd=clone).stdout.strip()
        log("dry run: would commit and push" if changed else "dry run: feed unchanged, nothing to commit")
        run(["git", "checkout", "--"] + PUBLISHED, cwd=clone)
        return
    run(["git", "add", "--"] + PUBLISHED, cwd=clone)
    if run(["git", "diff", "--cached", "--quiet"], cwd=clone, check=False).returncode == 0:
        log("feed unchanged, nothing to commit")
        return
    run(["git", "commit", "--quiet", "-m", "Air quality: refresh the hourly feed"], cwd=clone)
    for attempt in range(1, 4):
        if run(["git", "push", "--quiet", "origin", "HEAD:main"], cwd=clone, check=False).returncode == 0:
            return
        log(f"push rejected, rebasing (attempt {attempt})")
        run(["git", "pull", "--rebase", "--quiet", "origin", "main"], cwd=clone)
    raise RuntimeError("could not push after 3 attempts")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--clone", required=True, help="folder for the dedicated clone")
    ap.add_argument("--dry-run", action="store_true", help="do everything except upload and push")
    ap.add_argument("--log", help="append output to this file instead of the console")
    args = ap.parse_args()
    if args.log:
        if os.path.exists(args.log) and os.path.getsize(args.log) > 2 * LOG_KEEP_BYTES:
            with open(args.log, "rb") as f:     # keep the log from growing without end
                f.seek(-LOG_KEEP_BYTES, os.SEEK_END)
                tail = f.read()
            with open(args.log, "wb") as f:
                f.write(tail)
        sys.stdout = sys.stderr = open(args.log, "a", encoding="utf-8")
    clone = os.path.abspath(args.clone)

    os.makedirs(os.path.dirname(clone), exist_ok=True)
    lock = clone.rstrip("\\/") + ".lock"
    if os.path.exists(lock) and time.time() - os.path.getmtime(lock) < LOCK_STALE_SECONDS:
        log("another run is still going; skipping this hour")
        return 0
    with open(lock, "w") as f:
        f.write(str(os.getpid()))
    try:
        ensure_clone(clone)
        update_clone(clone)
        if not fetch_hour(clone):
            log("the fetch did not finish; publishing nothing this hour")
            return 1
        publish_archive(clone, args.dry_run)
        commit_and_push(clone, args.dry_run)
        log("done")
        return 0
    except Exception as e:   # one bad hour must not leave the next run stuck
        log(f"failed: {e}")
        return 1
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
