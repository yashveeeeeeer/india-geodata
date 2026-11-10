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
    python scripts/aq-hourly-local.py --clone "%USERPROFILE%/india-geodata-aq/repo"
    python scripts/aq-hourly-local.py --clone "%USERPROFILE%/india-geodata-aq/repo" --dry-run

--dry-run does every step except uploading the archive and pushing, and says
what it would have published. --log FILE appends everything to FILE instead of
the console; scripts/install-aq-hourly-task.ps1 sets this up as an hourly task.

Needs git, the gh CLI signed in with write access to the repository, and Python
with pandas and pyarrow. Exits non-zero when the hour could not be published;
nothing is published unless every step before the push succeeds.

Every run executes the scripts on main, so anyone who can push to main can run
code on this computer with its owner's git and gh credentials. Protect main.
Sign-in prompts are switched off: if a token expires, runs fail and say so in
the log instead of waiting for someone to click.
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
# Nobody is watching: a credential prompt must fail at once, never wait for a click.
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", GH_PROMPT_DISABLED="1",
           PYTHONIOENCODING="utf-8")


def log(msg):
    print(f"[{datetime.now(IST):%Y-%m-%d %H:%M:%S} IST] {msg}", flush=True)


def run(cmd, cwd=None, check=True, timeout=300):
    log("$ " + " ".join(cmd))
    try:
        res = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, encoding="utf-8",
                             errors="replace", creationflags=NO_WINDOW, env=ENV, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{cmd[0]} took longer than {timeout} s")
    for line in (res.stdout + res.stderr).replace("\0", "\n").splitlines():
        if line.strip():
            print("    " + line, flush=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"{cmd[0]} exited {res.returncode}")
    return res


def ist_day_of_snapshot(path):
    """aq-20261110T112920Z.csv -> 2026-11-10, in IST."""
    stamp = os.path.basename(path)[3:-4]
    try:
        when = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return when.astimezone(IST).strftime("%Y-%m-%d")


def ensure_clone(clone):
    if os.path.isdir(os.path.join(clone, ".git")):
        return
    log(f"creating a partial, sparse clone in {clone}")
    os.makedirs(os.path.dirname(os.path.abspath(clone)), exist_ok=True)
    run(["git", "clone", "--filter=blob:none", "--sparse", "--branch", "main", REMOTE, clone], timeout=900)
    run(["git", "sparse-checkout", "set"] + SPARSE, cwd=clone, timeout=900)


def restore_published(clone):
    """Put latest.json and air_quality.json back as the last commit has them, index included."""
    run(["git", "checkout", "HEAD", "--"] + PUBLISHED, cwd=clone, check=False)


def dirty_paths(clone):
    out = run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=no"], cwd=clone).stdout
    entries, paths, i = out.split("\0"), [], 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        paths.append(entry[3:])
        if entry[0] in "RC" and i < len(entries):   # a rename or copy is followed by its old path
            paths.append(entries[i])
            i += 1
    return paths


def update_clone(clone):
    git_dir = os.path.join(clone, ".git")
    if os.path.isdir(os.path.join(git_dir, "rebase-merge")) or os.path.isdir(os.path.join(git_dir, "rebase-apply")):
        log("a rebase was left half done; abandoning it")
        run(["git", "rebase", "--abort"], cwd=clone, check=False)
    # A run that died part way can leave latest.json modified or staged. Only the
    # files this script writes may be dirty; anything else means a person is using
    # the clone, so stop rather than touch their work.
    dirty = dirty_paths(clone)
    foreign = [p for p in dirty if p not in PUBLISHED]
    if foreign:
        raise RuntimeError("the clone has changes this script did not make: " + ", ".join(foreign))
    if dirty:
        restore_published(clone)
    run(["git", "fetch", "--quiet", "origin", "main"], cwd=clone)
    # An hourly commit still here was never pushed and is older than the hour about
    # to be fetched, so follow origin/main exactly.
    run(["git", "reset", "--quiet", "--keep", "origin/main"], cwd=clone)


def fetch_hour(clone):
    snaps = os.path.join(clone, ".aq-snapshots")
    today = datetime.now(IST).strftime("%Y-%m-%d")
    # Snapshots from today that are still here were never published (the upload
    # failed), so they are folded in with this hour. Older ones belong to a day
    # whose file is closed, so they go.
    for old in glob.glob(os.path.join(snaps, "aq-*.csv")):
        if ist_day_of_snapshot(old) != today:
            os.remove(old)
    before = set(glob.glob(os.path.join(snaps, "aq-*.csv")))
    res = run([sys.executable, "scripts/fetch-aq-latest.py", "--snapshot-dir", ".aq-snapshots"],
              cwd=clone, check=False, timeout=900)
    if res.returncode != 0:
        for f in set(glob.glob(os.path.join(snaps, "aq-*.csv"))) - before:
            os.remove(f)
        restore_published(clone)
        return False
    return True


def release_assets(clone):
    """Asset names in the aq-live release, or None when the release does not exist."""
    res = run(["gh", "release", "view", RELEASE, "--repo", REPO, "--json", "assets",
               "--jq", ".assets[].name"], cwd=clone, check=False)
    if res.returncode == 0:
        return res.stdout.split()
    if "release not found" in (res.stdout + res.stderr).lower():
        return None
    raise RuntimeError("could not read the aq-live release")


def publish_archive(clone, dry_run):
    day = datetime.now(IST).strftime("%Y-%m-%d")
    name = f"aq-{day}.parquet"
    archive = os.path.join(clone, ".aq-archive")
    remote_dir = os.path.join(archive, "remote")
    os.makedirs(remote_dir, exist_ok=True)
    for old in glob.glob(os.path.join(remote_dir, "*")):
        os.remove(old)
    for old in glob.glob(os.path.join(archive, "aq-*.parquet")):
        if os.path.basename(old) != name:
            os.remove(old)
    kept = os.path.join(archive, name)   # left by a run whose upload failed, if any

    assets = release_assets(clone)
    existing = ""
    if assets and name in assets:
        # it must download cleanly before we rewrite it, or the day's earlier hours are lost
        run(["gh", "release", "download", RELEASE, "--repo", REPO, "--pattern", name,
             "--dir", remote_dir, "--clobber"], cwd=clone)
        existing = os.path.join(remote_dir, name)
    elif os.path.exists(kept):
        # gh deletes the old asset before uploading the new one, so a failed upload
        # can leave the release without today's file; this copy still has those hours
        log(f"{name} is missing from the release; rebuilding from the copy kept here")
        existing = kept
    run([sys.executable, "scripts/append-aq-archive.py", "--snapshot-dir", ".aq-snapshots",
         "--out", ".aq-archive", "--existing", existing], cwd=clone)
    built = os.path.join(archive, name)
    if not os.path.exists(built):
        raise RuntimeError(f"append-aq-archive.py did not write {name}")
    if dry_run:
        log(f"dry run: would upload {name} ({os.path.getsize(built) / 1024:.0f} KB) to {RELEASE}")
        return
    if assets is None:
        run(["gh", "release", "create", RELEASE, "--repo", REPO, "--title", "Air quality, live archive",
             "--notes", "Hourly CPCB readings, one Parquet file per day. Rebuilt by "
             ".github/workflows/aq-hourly.yml or scripts/aq-hourly-local.py."], cwd=clone)
    run(["gh", "release", "upload", RELEASE, built, "--repo", REPO, "--clobber"], cwd=clone, timeout=600)
    # only now is the hour safe on GitHub
    for f in glob.glob(os.path.join(clone, ".aq-snapshots", "aq-*.csv")):
        os.remove(f)
    os.remove(built)


def commit_and_push(clone, dry_run):
    if dry_run:
        changed = run(["git", "diff", "--stat", "--"] + PUBLISHED, cwd=clone).stdout.strip()
        log("dry run: would commit and push" if changed else "dry run: feed unchanged, nothing to commit")
        restore_published(clone)
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
        run(["git", "fetch", "--quiet", "origin", "main"], cwd=clone)
        if run(["git", "rebase", "--quiet", "origin/main"], cwd=clone, check=False).returncode != 0:
            # Someone else (the GitHub job, if CPCB lets it in again) published
            # latest.json in the meantime. Theirs is as new as ours: give way.
            run(["git", "rebase", "--abort"], cwd=clone, check=False)
            run(["git", "reset", "--quiet", "--keep", "origin/main"], cwd=clone)
            log("latest.json was published by someone else this hour; keeping theirs")
            return
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
