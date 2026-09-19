#!/usr/bin/env python3
"""Fetch the current hour of CPCB readings and write what the page needs.

Source: data.gov.in resource 3b01bcb8 ("Real time Air Quality Index from various
locations"), published by CPCB. It is a snapshot with no history, so this runs
hourly and the archive is accumulated from the snapshots.

The feed reports the AQI sub-index, not the concentration, so every reading is
converted before it is published (see scripts/aqi_scale.py). The snapshot keeps
the feed's own numbers untouched, because it is the record of what the API said;
the rebuild converts them on the way to the page.

Writes:
    docs/projects/air-quality/data/latest.json   city means per pollutant, for the map
    <snapshot dir>/aq-<UTC timestamp>.csv        the raw rows, for the archive step

Get a free key at https://data.gov.in and pass it with --key or DATA_GOV_IN_KEY.
The published sample key works but returns 10 rows per request, so this pages.

Pages are read down one connection, with a short wait between them. Opening a
fresh TLS connection for each of thirty-odd pages and firing them back to back
reads like a burst, and data.gov.in starts refusing: the first page answers in
under two seconds and the second is met with a closed door.

Usage:
    python scripts/fetch-aq-latest.py [--key KEY] [--snapshot-dir DIR]
"""

import argparse
import csv
import http.client
import json
import os
import random
import re
import sys
import time
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aqi_scale import check_covered, to_concentration   # noqa: E402

RESOURCE = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
HOST = "api.data.gov.in"
PATH = f"/resource/{RESOURCE}"
API = f"https://{HOST}{PATH}"
UA = "india-geodata-build"
SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"  # public sample
POLLUTANTS = {"PM2.5", "PM10", "NO2", "CO", "OZONE", "NH3"}
check_covered(POLLUTANTS)
IST = timezone(timedelta(hours=5, minutes=30))
NA = {"", "na", "n/a", "nan", "null", "none", "-"}


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s).lower())).strip("-")


# One connection, reused for every page. Kept at module level because the paging
# loop below has no object to hang it on, and there is only ever one of them.
_conn = None


def _connection(timeout):
    global _conn
    if _conn is None:
        _conn = http.client.HTTPSConnection(HOST, timeout=timeout)
    return _conn


def _drop_connection():
    global _conn
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = None


def get(key, limit, offset, tries=5, timeout=45.0):
    """One page, retrying on throttling and transient server errors. data.gov.in
    returns 429 readily, and an hourly job must not fall over because of it.

    A refused connection is treated as the throttle it almost always is: the
    connection is dropped and reopened, and the wait grows faster than for a
    plain timeout."""
    q = urllib.parse.urlencode({"api-key": key, "format": "json",
                                "limit": limit, "offset": offset})
    delay = 3
    for attempt in range(tries):
        try:
            t0 = time.time()
            conn = _connection(timeout)
            conn.request("GET", f"{PATH}?{q}", headers={
                "User-Agent": UA, "Accept": "application/json",
                "Connection": "keep-alive"})
            resp = conn.getresponse()
            body = resp.read()          # always drain, or the socket cannot be reused
            if resp.status >= 400:
                retry_after = resp.getheader("Retry-After")
                if resp.status not in (429, 500, 502, 503, 504) or attempt == tries - 1:
                    _drop_connection()
                    raise SystemExit(f"data.gov.in answered HTTP {resp.status} "
                                     f"for offset {offset}")
                try:
                    wait = int(retry_after or 0) or delay
                except ValueError:
                    wait = delay        # an HTTP-date Retry-After; our own backoff will do
                print(f"      HTTP {resp.status}, waiting {wait}s", flush=True)
                time.sleep(wait)
                delay = min(delay * 2, 120)
                continue
            if resp.status in (301, 302, 303, 307, 308):
                # urllib used to follow these for us; http.client does not.
                raise SystemExit(f"data.gov.in redirected to "
                                 f"{resp.getheader('Location')!r}; the endpoint has moved")
            try:
                out = json.loads(body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as e:
                # Answered, quickly, with something that is not our JSON. Retrying
                # will not help and calling it a throttle sends the next person
                # looking in the wrong place.
                _drop_connection()
                raise SystemExit(f"data.gov.in answered HTTP {resp.status} with "
                                 f"{len(body)} bytes that are not JSON ({e}); "
                                 f"first 200: {body[:200]!r}")
            if offset == 0:
                print(f"  first page: {len(out.get('records') or [])} rows "
                      f"in {time.time() - t0:.1f}s", flush=True)
            return out
        except SystemExit:
            raise
        except (OSError, http.client.HTTPException) as e:
            # A half-used connection is worse than none; start the next try fresh.
            refused = isinstance(e, ConnectionError)
            _drop_connection()
            print(f"      {'refused' if refused else 'request failed'} ({e}); "
                  f"attempt {attempt + 1} of {tries}", flush=True)
            if attempt == tries - 1:
                raise SystemExit(
                    "data.gov.in did not respond. The API answers quickly from a normal "
                    "connection, so a persistent refusal here usually means the runner's "
                    "address is being throttled. Try a longer --pause or a smaller --page.")
            time.sleep(delay * (2 if refused else 1))
            delay = min(delay * 2, 60)


class OutOfTime(SystemExit):
    """Ran long. Raised as SystemExit so the caller exits 1 like any other giving
    up — a job-level timeout would cancel the run and mark it failed, which is
    the one thing this hour is not supposed to do."""


def _breathe(pause):
    """A short, uneven wait. Even spacing from a job that runs on the hour still
    arrives as a recognisable pattern; a little jitter does not."""
    if pause > 0:
        time.sleep(pause * random.uniform(0.6, 1.4))


def fetch_all(key, page=100, pause=0.4, timeout=45.0, deadline=600.0):
    """Page until the reported total is covered. A key with a smaller ceiling than
    `page` simply returns fewer rows, and the page size adapts to what came back.

    Gives up after `deadline` seconds. Thirty-odd pages, each with its own retry
    budget, can otherwise run for hours against a merely slow endpoint."""
    started = time.monotonic()
    first = get(key, page, 0, timeout=timeout)
    total = int(first.get("total") or 0)
    rows = list(first.get("records") or [])
    if not rows:
        _drop_connection()
        return rows, total
    step = len(rows)
    while len(rows) < total:
        spent = time.monotonic() - started
        if spent > deadline:
            _drop_connection()
            took = f"{spent / 60:.1f} min" if spent >= 60 else f"{spent:.0f}s"
            raise OutOfTime(f"gave up after {took} with {len(rows)} of {total} rows; "
                            f"data.gov.in is answering but slowly. Nothing was published.")
        _breathe(pause)                 # before the request, not after the last one
        batch = get(key, step, len(rows), timeout=timeout)
        got = batch.get("records") or []
        if not got:
            break
        rows.extend(got)
    _drop_connection()
    return rows, total


def to_float(v):
    if v is None or str(v).strip().lower() in NA:
        return None
    try:
        f = float(str(v).strip())
    except ValueError:
        return None
    return f if f == f else None


def city_lookup(cities):
    """Map the feed's city/state naming onto our city ids. Exact city+state first;
    a bare city name only when it is unambiguous across states."""
    exact, bare, ambiguous = {}, {}, set()
    for c in cities:
        exact[slug(f"{c['name']}-{c['state']}")] = c["id"]
        k = slug(c["name"])
        if k in bare and bare[k] != c["id"]:
            ambiguous.add(k)
        bare[k] = c["id"]
    for k in ambiguous:
        bare.pop(k, None)
    return exact, bare


def _norm(v):
    return re.sub(r"[^a-z0-9]", "", (v or "").lower())


def _without_agency(v):
    """Drop the trailing " - OPERATOR". The two sources disagree about who runs a
    monitor — the feed says IITM where our records say IMD for the same physical
    station — so the operator is not safe to match on."""
    return _norm((v or "").rsplit(" - ", 1)[0])


def station_lookup(stations):
    """The feed names a monitor ("Alipur, Delhi - DPCC") where our records carry an
    id. Both come from CPCB's registry, so the names line up once punctuation and
    spacing are stripped. Falls back to the name without its operator suffix, but
    only where that is unambiguous."""
    exact, loose, clash = {}, {}, set()
    for st in stations:
        name = st.get("name")
        if not name:
            continue
        exact[_norm(name)] = st["id"]
        b = _without_agency(name)
        if b in loose and loose[b] != st["id"]:
            clash.add(b)
        loose[b] = st["id"]
    for b in clash:
        loose.pop(b, None)
    return exact, loose


def aggregate(rows, cities, stations=None):
    exact, bare = city_lookup(cities)
    by_name, by_base = station_lookup(stations or [])
    per_station = defaultdict(dict)
    unmatched_stations = set()
    # pollutant -> city id -> [station values]
    acc = defaultdict(lambda: defaultdict(list))
    stamps, unknown, used = [], set(), set()

    for r in rows:
        p = (r.get("pollutant_id") or "").strip().upper()
        if p not in POLLUTANTS:
            continue
        # the feed's value is a sub-index; the page reads concentrations
        v = to_concentration(p, to_float(r.get("avg_value")))
        if v is None:
            continue
        cid = (exact.get(slug(f"{r.get('city','')}-{r.get('state','')}"))
               or bare.get(slug(r.get("city", ""))))
        if not cid:
            if r.get("city"):
                unknown.add(f"{r.get('city')} ({r.get('state')})")
            continue
        acc[p][cid].append(v)
        used.add(r.get("station", ""))
        raw = r.get("station") or ""
        sid = by_name.get(_norm(raw)) or by_base.get(_without_agency(raw))
        if sid:
            per_station[p][sid] = round(v, 2 if p == "CO" else 1)
        elif r.get("station"):
            unmatched_stations.add(r["station"])
        if r.get("last_update"):
            stamps.append(r["last_update"])

    pollutants = {}
    for p, byc in acc.items():
        dp = 2 if p == "CO" else 1          # CO sits near 1 mg/m³, so keep two
        pollutants[p] = {cid: round(sum(vs) / len(vs), dp) for cid, vs in byc.items()}

    # the feed stamps every row with its own refresh time; the newest is the snapshot
    updated = None
    if stamps:
        parsed = []
        for s in stamps:
            try:
                parsed.append(datetime.strptime(s, "%d-%m-%Y %H:%M:%S"))
            except ValueError:
                pass
        if parsed:
            updated = max(parsed).replace(tzinfo=IST).isoformat()

    return (pollutants, dict(per_station), updated, sorted(unknown),
            len(used), sorted(unmatched_stations))


def main():
    ap = argparse.ArgumentParser()
    # GitHub hands an unset secret through as "", so the usual default does not
    # fire and we would send an empty api-key and be turned away.
    ap.add_argument("--key", default=(os.environ.get("DATA_GOV_IN_KEY") or "").strip()
                    or SAMPLE_KEY)
    ap.add_argument("--deadline", type=float, default=600.0,
                    help="seconds to spend paging before giving up")
    ap.add_argument("--snapshot-dir", default=os.path.join(".aq-snapshots"))
    ap.add_argument("--page", type=int, default=100)
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--pause", type=float, default=0.4,
                    help="seconds to wait between pages, jittered; 0 to page flat out")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, "docs", "projects", "air-quality", "data")
    cities = json.load(open(os.path.join(data_dir, "cities.json"), encoding="utf-8"))

    if args.key == SAMPLE_KEY:
        # It works, which is the danger: it caps pages at ten rows and publishes
        # the same numbers, so a deleted secret would look like a healthy hour
        # for ever. Say so where a log will catch it.
        print("::warning::no DATA_GOV_IN_KEY; falling back to the public sample "
              "key, which returns ten rows a page. Set the secret.", flush=True)
    rows, total = fetch_all(args.key, args.page, args.pause, args.timeout,
                            args.deadline)
    if not rows:
        sys.exit("no records returned")
    print(f"  fetched {len(rows)} of {total} rows")

    stations = json.load(open(os.path.join(data_dir, "stations.json"), encoding="utf-8"))
    (pollutants, per_station, updated, unknown,
     n_stations, unmatched_st) = aggregate(rows, cities, stations)
    if not pollutants:
        sys.exit("no usable pollutant readings in the response")

    payload = {
        "updated": updated,
        "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Central Pollution Control Board, via data.gov.in",
        "stations": n_stations,
        "pollutants": pollutants,
        "byStation": per_station,
    }
    out = os.path.join(data_dir, "latest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))

    for p in sorted(pollutants):
        print(f"    {p:<6s} {len(pollutants[p]):3d} cities")
    print(f"  {n_stations} stations, updated {updated}")
    matched = len({sid for p in per_station for sid in per_station[p]})
    print(f"  {matched} monitors matched by name, {len(unmatched_st)} unmatched")
    if unmatched_st:
        print("    e.g. " + "; ".join(unmatched_st[:3]))
    if unknown:
        print(f"  {len(unknown)} cities in the feed are not in cities.json "
              f"(rebuild geography): {', '.join(unknown[:5])}")
    print(f"  -> {os.path.relpath(out, root)} ({os.path.getsize(out)/1024:.0f} KB)")

    # raw snapshot, for the archive step to fold into the Parquet history
    snap_dir = os.path.join(root, args.snapshot_dir)
    os.makedirs(snap_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snap = os.path.join(snap_dir, f"aq-{stamp}.csv")
    cols = ["country", "state", "city", "station", "last_update", "latitude",
            "longitude", "pollutant_id", "min_value", "max_value", "avg_value"]
    with open(snap, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  -> {os.path.relpath(snap, root)} ({os.path.getsize(snap)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
