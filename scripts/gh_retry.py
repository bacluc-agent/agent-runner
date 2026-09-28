#!/usr/bin/env python3
"""gh_retry.py — rate-limit-aware `gh` wrapper (Python port of scripts/gh-retry.sh).

    python3 scripts/gh_retry.py preflight <what> [bucket ...]
    python3 scripts/gh_retry.py retry [gh-args ...]

All diagnostics go to stderr so the wrapped command's stdout stays clean for
--jq pipelines and $(). `preflight` is a free quota probe that always exits 0
(stand-down = ::error:: + exit 0). `retry` passes gh's stdout through untouched,
replays gh's captured stderr, prints one `GitHub API quota after gh ...` line
per attempt, backs off on rate-limit responses (sleep-until-reset when a bucket
is empty and the reset is near, exponential backoff otherwise) and always exits
with gh's exit status from the last attempt.
"""

import argparse
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

JQ = (
    "[.resources.core.remaining,.resources.core.limit,.resources.core.reset,"
    ".resources.search.remaining,.resources.search.limit,.resources.search.reset,"
    ".resources.graphql.remaining,.resources.graphql.limit,.resources.graphql.reset]"
    " | @tsv"
)
RATE_LIMIT_RE = re.compile(r"rate limit|HTTP 429|abuse detection", re.IGNORECASE)
BUCKETS = ("core", "search", "graphql")


def env_int(name, default):
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return default


def fmt_ts(value):
    try:
        if re.fullmatch(r"[0-9]+", value):
            return datetime.fromtimestamp(int(value), timezone.utc).strftime("%H:%M:%SZ")
    except Exception:
        pass
    return "?"


def seconds_until(value):
    if re.fullmatch(r"[0-9]+", value):
        return int(value) - int(time.time())
    return -1


def probe_quota():
    """9-tuple (core_r, core_l, core_x, search_r, search_l, search_x, gql_r, gql_l, gql_x)."""
    try:
        proc = subprocess.run(
            ["gh", "api", "rate_limit", "--jq", JQ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return ("unknown",) * 9
    out = proc.stdout.decode("utf-8", "replace")
    if proc.returncode != 0 and not out.strip():
        return ("unknown",) * 9
    lines = out.splitlines()
    first = lines[0] if lines else ""
    return tuple((first.split() + [""] * 9)[:9])


def _err(message):
    print(message, file=sys.stderr)


def _quota_line(prefix, core_r, core_l, core_x, search_r, search_l, search_x, gql_r, gql_l, gql_x):
    return (
        f"{prefix} core={core_r}/{core_l} (reset {fmt_ts(core_x)})"
        f" search={search_r}/{search_l} (reset {fmt_ts(search_x)})"
        f" graphql={gql_r}/{gql_l} (reset {fmt_ts(gql_x)})"
    )


def cmd_preflight(what, buckets):
    max_sleep = env_int("GH_RETRY_MAX_SLEEP", 300)
    core_r, core_l, core_x, search_r, search_l, search_x, gql_r, gql_l, gql_x = probe_quota()
    _err(_quota_line("GitHub API quota:", core_r, core_l, core_x, search_r, search_l, search_x, gql_r, gql_l, gql_x))
    if core_r == "unknown":
        _err("::warning::GitHub API quota unknown (rate_limit probe failed); continuing and relying on per-call retries")
        return 0
    requested = f" {' '.join(buckets)} "
    for name, remaining, reset in (
        ("core", core_r, core_x),
        ("search", search_r, search_x),
        ("graphql", gql_r, gql_x),
    ):
        if f" {name} " not in requested:
            continue
        if remaining == "0":
            ins = seconds_until(reset)
            if ins < 0:
                continue
            if ins > max_sleep:
                _err(
                    f"::error::GitHub API {name} quota exhausted (remaining=0, "
                    f"resets at {fmt_ts(reset)} in {ins}s > {max_sleep}s); "
                    f"standing down: skipping {what} this run"
                )
                return 0
            _err(
                f"GitHub API {name} quota empty but resets in {ins}s — "
                f"waiting it out on the first rate-limited call"
            )
    return 0


def cmd_retry(gh_args):
    max_attempts = env_int("GH_RETRY_MAX_ATTEMPTS", 4)
    max_sleep = env_int("GH_RETRY_MAX_SLEEP", 300)
    base = env_int("GH_RETRY_BACKOFF_BASE", 10)
    args_str = " ".join(gh_args)
    attempt = 1
    while True:
        try:
            proc = subprocess.run(["gh", *gh_args], stderr=subprocess.PIPE)
            rc = proc.returncode
            err = proc.stderr
        except FileNotFoundError:
            rc = 127
            err = b"gh: command not found\n"
        if err:
            sys.stderr.buffer.write(err)
            sys.stderr.buffer.flush()
        core_r, core_l, core_x, search_r, search_l, search_x, gql_r, gql_l, gql_x = probe_quota()
        _err(_quota_line(f"GitHub API quota after gh {args_str}:", core_r, core_l, core_x, search_r, search_l, search_x, gql_r, gql_l, gql_x))
        if rc == 0:
            return 0
        if not RATE_LIMIT_RE.search(err.decode("utf-8", "replace")):
            return rc
        ex = ""
        ex_x = ""
        ins = -1
        for name, remaining, reset in (
            ("core", core_r, core_x),
            ("search", search_r, search_x),
            ("graphql", gql_r, gql_x),
        ):
            if remaining == "0":
                ex = name
                ex_x = reset
                ins = seconds_until(reset)
                break
        if ex and (ins < 0 or ins > max_sleep):
            _err(
                f"::error::GitHub API rate limit: gh {args_str} failed; {ex} remaining=0, "
                f"resets at {fmt_ts(ex_x)} ({ins}s away > {max_sleep}s); not retrying — "
                f"the calling step's guard decides what to skip"
            )
            return rc
        if attempt >= max_attempts:
            _err(
                f"::error::GitHub API rate limit: giving up on gh {args_str} after "
                f"{attempt}/{max_attempts} attempts (core={core_r}/{core_l} reset {fmt_ts(core_x)}, "
                f"search={search_r}/{search_l} reset {fmt_ts(search_x)}, "
                f"graphql={gql_r}/{gql_l} reset {fmt_ts(gql_x)}); "
                f"the calling step's guard decides what to skip"
            )
            return rc
        if ex:
            delay = ins + random.randint(1, 5)
            until_note = f" until the {ex} reset"
        else:
            delay = base * 2 ** (attempt - 1) + random.randint(0, 4)
            if delay > 60:
                delay = 60
            until_note = ""
        _err(
            f"::warning::GitHub API rate limit on gh {args_str} (attempt {attempt}/{max_attempts}): "
            f"sleeping {delay}s{until_note}"
        )
        time.sleep(delay)
        attempt += 1


def main(argv):
    parser = argparse.ArgumentParser(
        prog="gh_retry.py",
        description="Rate-limit-aware gh wrapper: preflight quota probe and retrying gh calls.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="{preflight,retry}")
    pre = sub.add_parser("preflight", help="Free quota probe; stands down loudly when a requested bucket is exhausted.")
    pre.add_argument("what", help="What a stand-down skips (e.g. 'issue selection').")
    pre.add_argument("buckets", nargs="*", help="Buckets the step uses: core, search, graphql.")
    ret = sub.add_parser("retry", help="Run gh, back off on rate limits, propagate the exit status.")
    ret.add_argument("gh_args", nargs=argparse.REMAINDER, help="Arguments passed through to gh.")
    args = parser.parse_args(argv)
    if args.command == "preflight":
        return cmd_preflight(args.what, args.buckets)
    return cmd_retry(args.gh_args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
