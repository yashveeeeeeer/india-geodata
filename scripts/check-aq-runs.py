#!/usr/bin/env python3
"""Ask GitHub whether the hourly workflow is still being run.

Every other check here infers "the pipeline is alive" from how old the
published data is. That reading cannot tell two very different faults apart —
the source refusing to answer, and the schedule not firing at all — and it is
blind to the second by construction. When GitHub stops dispatching a scheduled
workflow, or disables it outright, the data merely ages, and the stale-data
issue goes on blaming a feed that nothing ever asked for.

So ask the Actions API instead. It answers two questions:

  the state   whether the workflow is still active, and if not, why GitHub
              turned it off. A field with the answer in it: no threshold, no
              inference, no clock.
  the runs    whether scheduled runs are still starting, and whether the ones
              that start are finishing.

Between them they separate the causes. Runs are starting and succeeding, but
the data is old: the fetch is coming back empty, so look at data.gov.in and at
DATA_GOV_IN_KEY. Runs are not starting at all: look at GitHub, not at the data.

The quiet window is measured rather than guessed. In the sample so far — a
day and a bit, so read it as indicative — the gaps between scheduled starts of
the hourly workflow were 2.1 to 5.5 hours, a cron of '20 * * * *' that GitHub
honours perhaps a third of the time. Starts are a tighter signal than publishes,
which a run that fetches nothing does not produce, and the default of 24 hours
sits at more than four times the widest gap seen. It can
afford to be loose, because the check that catches the failure everyone is
actually afraid of is the state field, which is not a clock at all.

Prints a line per check. Exits 0 when the schedule is alive and its runs are
succeeding, 1 when something is wrong and a person should hear about it, and 2
when the API could not be read, which says nothing either way. Meant for a
scheduled workflow that opens an issue on 1 and lets the run go red on 2, so a
GitHub outage does not open issues about this repository.

Usage:
    python scripts/check-aq-runs.py [--repo owner/name]
                                    [--workflow aq-hourly.yml]
                                    [--quiet-hours 24] [--failures 3]
"""

import argparse
import itertools
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

ATTEMPTS = 3            # a 5xx from GitHub is usually gone by the next breath
BACKOFF = 3.0           # seconds, doubled each time


class Unreadable(Exception):
    """The API could not be read. Says nothing about the pipeline."""


class Missing(Exception):
    """The API answered, and the workflow is not there."""


def token():
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(name)
        if value:
            return value
    raise Unreadable("no GH_TOKEN in the environment")


def get(path):
    """One GET against the Actions API, retried over the brief failures."""
    base = os.environ.get("GITHUB_API_URL") or "https://api.github.com"
    request = urllib.request.Request(
        f"{base.rstrip('/')}/{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {token()}",
            "User-Agent": "india-geodata-run-watchdog",
        },
    )
    body = None
    for attempt in range(ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Missing(path)
            # A spent rate limit is neither transient nor our fault, and
            # retrying it just spends the remaining seconds. Name it and stop.
            spent = e.headers.get("x-ratelimit-remaining") == "0"
            if e.code in (403, 429) and spent:
                reset = e.headers.get("x-ratelimit-reset")
                when = stamp(reset) if reset else "some point"
                raise Unreadable(f"rate limited until {when}")
            if e.code < 500:
                raise Unreadable(f"HTTP {e.code} for {path}")
            if attempt == ATTEMPTS - 1:
                raise Unreadable(f"HTTP {e.code} for {path}, {ATTEMPTS} times over")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == ATTEMPTS - 1:
                raise Unreadable(f"cannot reach the API: {e}")
        time.sleep(BACKOFF * (2 ** attempt))

    try:
        doc = json.loads(body)
    except ValueError as e:
        raise Unreadable(f"the response to {path} is not JSON: {e}")
    if not isinstance(doc, dict):
        raise Unreadable(f"the response to {path} is not an object")
    return doc


def stamp(epoch):
    try:
        return datetime.fromtimestamp(int(epoch), timezone.utc).isoformat()
    except (TypeError, ValueError):
        return str(epoch)


def when(text):
    """A GitHub timestamp, or None if it is not one."""
    if not isinstance(text, str):
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def started(run):
    """When a run began. run_started_at is the honest one — created_at moves
    when a run is re-run — but not every run carries it."""
    return when(run.get("run_started_at")) or when(run.get("created_at"))


WHY = {
    "disabled_inactivity":
        "GitHub turned it off after a stretch with no repository activity",
    "disabled_manually":
        "somebody turned it off, in the Actions tab or through the API",
    "disabled_fork":
        "this is a fork, and forks do not run scheduled workflows",
    "deleted":
        "the workflow is gone",
}


def check_state(workflow):
    """Whether GitHub still intends to run this at all.

    This is the whole point of the script. Nothing that reads the published
    data can see this: a disabled schedule and a dead source age the files at
    exactly the same rate."""
    state = workflow.get("state")
    name = workflow.get("name") or workflow.get("path") or "the workflow"
    if not state:
        print(f"UNREADABLE schedule: {name} has no state field")
        return 2
    if state != "active":
        print(f"DISABLED schedule: {name} is {state} — {WHY.get(state, 'GitHub does not say why')}")
        return 1
    return 0


def check_runs(runs, workflow, quiet_hours, failures):
    """Whether scheduled runs are still starting, and still finishing well.

    Only scheduled runs count. A hand-pressed workflow_dispatch proves that
    somebody was watching, not that the schedule is alive, and letting one
    stand in for the other is how a dead cron stays hidden for a month."""
    now = datetime.now(timezone.utc)
    dated = sorted((r for r in runs if started(r)), key=started, reverse=True)
    if runs and not dated:
        return 2, "UNREADABLE runs: no run carries a start time this can read"

    if not dated:
        # Nothing yet. On a workflow GitHub only learned about this morning
        # that is ordinary, so say so rather than raising an alarm about it.
        born = when(workflow.get("created_at"))
        if born and (now - born) < timedelta(hours=quiet_hours):
            age = (now - born).total_seconds() / 3600
            return 0, f"NEW schedule: added {age:.1f}h ago, no scheduled run yet"
        since = f"added {born.isoformat()}" if born else "of unknown age"
        return 1, f"SILENT schedule: not one scheduled run has ever started, {since}"

    newest = dated[0]
    quiet = (now - started(newest)).total_seconds() / 3600
    if quiet > quiet_hours:
        return 1, (f"SILENT schedule: the last scheduled run started "
                   f"{started(newest).isoformat()}, {quiet:.1f}h ago, past the "
                   f"{quiet_hours:g}h this schedule is allowed to go quiet")

    # Running, then. Are the runs any good? This is a count, not a clock: one
    # failure is a bad hour, a run of them is a broken job. Since the hourly
    # workflow stopped going red over a refused fetch, a failure here means the
    # machinery around the fetch broke, which no amount of waiting will mend.
    done = [r for r in dated if r.get("status") == "completed"]
    # cancelled/skipped/stale runs are not the job failing — the hourly
    # workflow's own concurrency group cancels a superseded pending run — so
    # they are neither counted nor allowed to break a run of failures.
    NOISE = {"cancelled", "skipped", "stale"}
    judged = [r for r in done if (r.get("conclusion") or "") not in NOISE]

    bad = list(itertools.takewhile(lambda r: r.get("conclusion") != "success", judged))
    window = judged[:max(2 * failures, 6)]
    won = sum(1 for r in window if r.get("conclusion") == "success")
    streak = len(bad) >= failures
    thin = len(window) >= failures and won * 2 < len(window)   # under half succeeding
    if streak or thin:
        if streak:
            reason = (f"the last {len(bad)} in a row ended "
                      + ", ".join(str(r.get("conclusion") or "no conclusion") for r in bad))
            where = bad[0].get("html_url") or ""
        else:
            reason = f"only {won} of the last {len(window)} succeeded"
            where = next((r.get("html_url") for r in window
                          if r.get("conclusion") != "success"), "")
        tail = f" — {where}" if where else ""
        return 1, (f"FAILING runs: {reason}; the schedule is firing but the job is "
                   f"not finishing{tail}")

    won_all = sum(1 for r in judged if r.get("conclusion") == "success")
    return 0, (f"RUNNING schedule: last scheduled run {started(newest).isoformat()}, "
               f"{quiet:.1f}h ago; {won_all} of the last {len(judged)} judged runs succeeded")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"),
                    help="owner/name; defaults to GITHUB_REPOSITORY")
    ap.add_argument("--workflow", default="aq-hourly.yml",
                    help="the workflow file to watch")
    ap.add_argument("--quiet-hours", type=float, default=24.0,
                    help="how long the schedule may go without starting a run")
    ap.add_argument("--failures", type=int, default=3,
                    help="how many failed runs in a row before it is reported")
    args = ap.parse_args()

    if not args.repo:
        print("UNREADABLE schedule: no repository given and no GITHUB_REPOSITORY")
        return 2

    try:
        workflow = get(f"repos/{args.repo}/actions/workflows/{args.workflow}")
    except Missing:
        # A 404 here means the workflow is gone — or that the token cannot see
        # this repo at all (revoked, SSO lapsed, actions:read dropped), which
        # 404s identically. Ask whether the repo itself is visible: if it is,
        # the workflow really is missing and a person should hear about it; if
        # it is not, the fault is our access, and that is a red run, not an
        # issue blaming a workflow that may be running fine.
        try:
            get(f"repos/{args.repo}")
        except (Missing, Unreadable):
            print(f"UNREADABLE schedule: cannot see {args.repo} at all — a token "
                  f"or access problem, not necessarily the workflow")
            return 2
        print(f"MISSING schedule: {args.repo} has no workflow {args.workflow}")
        return 1
    except Unreadable as e:
        print(f"UNREADABLE schedule: {e}")
        return 2

    worst = check_state(workflow)
    if worst:
        # A disabled workflow has no recent runs by definition. Listing them
        # would only add a second line saying the same thing in a vaguer way.
        return worst

    try:
        doc = get(f"repos/{args.repo}/actions/workflows/{args.workflow}"
                  f"/runs?event=schedule&per_page=50")
    except (Missing, Unreadable) as e:
        print(f"UNREADABLE runs: {e}")
        return 2

    runs = doc.get("workflow_runs")
    if not isinstance(runs, list):
        print("UNREADABLE runs: the response carries no list of runs")
        return 2

    code, line = check_runs(runs, workflow, args.quiet_hours, args.failures)
    print(line)
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                       # noqa: BLE001 — see below
        # A traceback leaves Python's own exit code of 1, which the workflow
        # reads as "the pipeline has stopped" and would open an issue about,
        # with the traceback as the body. A broken watchdog is a 2.
        print(f"UNREADABLE schedule: this check fell over: {e!r}")
        sys.exit(2)
