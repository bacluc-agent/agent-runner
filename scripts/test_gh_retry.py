"""Tests for scripts/gh_retry.py (the rate-limit-aware gh wrapper)."""

import os
import re
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

STUB_GH = textwrap.dedent(
    """\
    #!/usr/bin/env bash
    if [[ "${1:-}" == api && "${2:-}" == rate_limit ]]; then
      if [[ "$STUB_MODE" == "probe-fail" ]]; then
        exit 1
      fi
      cat "$STUB_DIR/ratelimit.tsv"
      exit 0
    fi
    count=0
    if [[ -f "$STUB_DIR/count" ]]; then
      count="$(cat "$STUB_DIR/count")"
    fi
    count=$((count + 1))
    printf '%s\\n' "$count" > "$STUB_DIR/count"
    rate_limited='HTTP 403: API rate limit exceeded for user ID 1'
    case "$STUB_MODE" in
      ok)
        printf 'OK:%s\\n' "$*"
        ;;
      not-rate-limit)
        printf 'HTTP 404: Not Found\\n' >&2
        exit 1
        ;;
      rate-limit-once)
        if ((count == 1)); then
          printf '%s\\n' "$rate_limited" >&2
          exit 1
        fi
        printf 'OK:%s\\n' "$*"
        ;;
      rate-limit-twice)
        if ((count <= 2)); then
          printf '%s\\n' "$rate_limited" >&2
          exit 1
        fi
        printf 'OK:%s\\n' "$*"
        ;;
      rate-limit-forever)
        printf '%s\\n' "$rate_limited" >&2
        exit 1
        ;;
      abuse-detection)
        printf 'HTTP 403: abuse detection — please wait before retrying\\n' >&2
        exit 7
        ;;
      *)
        printf 'unknown STUB_MODE: %s\\n' "$STUB_MODE" >&2
        exit 2
        ;;
    esac
    """
)


def healthy(delay=3600):
    """(core, search, graphql) buckets, each as (remaining, limit, reset_epoch)."""
    now = int(time.time())
    return (4000, 5000, now + delay, 28, 30, now + 60, 4000, 5000, now + delay)


def make_env(tmp_path, mode, buckets=None, write_ratelimit=True):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(STUB_GH)
    gh.chmod(0o755)
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    if write_ratelimit and buckets is not None:
        (stub_dir / "ratelimit.tsv").write_text(
            "\t".join(str(value) for value in buckets) + "\n"
        )
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["STUB_DIR"] = str(stub_dir)
    env["STUB_MODE"] = mode
    return env


def run_cli(args, env):
    return subprocess.run(
        ["python3", "scripts/gh_retry.py", *args],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )


def run_retry(tmp_path, mode, buckets, extra_env=None):
    env = make_env(tmp_path, mode, buckets)
    if extra_env:
        env.update(extra_env)
    return run_cli(["retry", "pr", "list", "-R", "acme/widgets"], env)


def run_preflight(tmp_path, mode, buckets, extra_env=None, write_ratelimit=True):
    env = make_env(tmp_path, mode, buckets, write_ratelimit=write_ratelimit)
    if extra_env:
        env.update(extra_env)
    return run_cli(["preflight", "issue selection", "core", "graphql"], env)


def parse_sleeps(stderr):
    return [int(match.group(1)) for match in re.finditer(r"sleeping (\d+)s", stderr)]


def test_rate_limit_retries_with_exponential_backoff_then_succeeds(tmp_path):
    proc = run_retry(tmp_path, "rate-limit-twice", healthy())
    assert proc.returncode == 0
    assert proc.stdout.startswith("OK:pr list -R acme/widgets")
    assert "GitHub API quota after gh pr list -R acme/widgets: core=" in proc.stderr
    sleeps = parse_sleeps(proc.stderr)
    assert len(sleeps) == 2
    assert 10 <= sleeps[0] <= 14, sleeps
    assert 20 <= sleeps[1] <= 24, sleeps
    assert "(attempt 1/4)" in proc.stderr
    assert "(attempt 2/4)" in proc.stderr
    assert "giving up" not in proc.stderr
    assert "HTTP 403: API rate limit exceeded" in proc.stderr


def test_gives_up_loudly_after_max_attempts(tmp_path):
    proc = run_retry(tmp_path, "rate-limit-forever", healthy())
    assert proc.returncode == 1
    sleeps = parse_sleeps(proc.stderr)
    assert len(sleeps) == 3
    assert 40 <= sleeps[2] <= 44, sleeps
    assert (
        "::error::GitHub API rate limit: giving up on gh pr list -R acme/widgets"
        " after 4/4 attempts" in proc.stderr
    )
    assert "core=4000/5000" in proc.stderr
    assert "search=28/30" in proc.stderr


def test_exhausted_core_with_distant_reset_gives_up_without_sleeping(tmp_path):
    buckets = healthy()
    now = int(time.time())
    exhausted = (0, 5000, now + 3600, *buckets[3:6], *buckets[6:])
    proc = run_retry(tmp_path, "rate-limit-forever", exhausted)
    assert proc.returncode == 1
    assert parse_sleeps(proc.stderr) == []
    assert "not retrying" in proc.stderr
    assert "resets at" in proc.stderr


def test_exhausted_core_with_near_reset_sleeps_until_reset(tmp_path):
    buckets = healthy()
    now = int(time.time())
    exhausted = (0, 5000, now + 30, *buckets[3:6], *buckets[6:])
    proc = run_retry(tmp_path, "rate-limit-once", exhausted)
    assert proc.returncode == 0
    sleeps = parse_sleeps(proc.stderr)
    assert len(sleeps) == 1
    assert 28 <= sleeps[0] <= 36, sleeps
    assert "until the core reset" in proc.stderr


def test_non_rate_limit_failure_is_not_retried(tmp_path):
    proc = run_retry(tmp_path, "not-rate-limit", healthy())
    assert proc.returncode == 1
    assert parse_sleeps(proc.stderr) == []
    assert "HTTP 404: Not Found" in proc.stderr
    assert "(attempt " not in proc.stderr
    assert "giving up" not in proc.stderr


def test_preflight_stands_down_loudly_when_quota_is_exhausted(tmp_path):
    buckets = healthy()
    now = int(time.time())
    exhausted = (0, 5000, now + 3600, *buckets[3:6], *buckets[6:])
    proc = run_preflight(tmp_path, "ok", exhausted)
    assert proc.returncode == 0
    assert "GitHub API quota: core=0/5000" in proc.stderr
    assert "::error::GitHub API core quota exhausted" in proc.stderr
    assert "standing down: skipping issue selection this run" in proc.stderr


def test_preflight_proceeds_when_quota_is_available(tmp_path):
    proc = run_preflight(tmp_path, "ok", healthy())
    assert proc.returncode == 0
    assert "core=4000/5000" in proc.stderr
    assert "standing down" not in proc.stderr


def test_preflight_ignores_buckets_the_step_does_not_use(tmp_path):
    buckets = healthy()
    now = int(time.time())
    search_empty = (*buckets[0:3], 0, 30, now + 3600, *buckets[6:])
    proc = run_preflight(tmp_path, "ok", search_empty)
    assert proc.returncode == 0
    assert "standing down" not in proc.stderr


def test_probe_failure_warns_and_exits_0(tmp_path):
    proc = run_preflight(tmp_path, "probe-fail", healthy())
    assert proc.returncode == 0
    assert (
        "GitHub API quota: core=unknown/unknown (reset ?)"
        " search=unknown/unknown (reset ?)"
        " graphql=unknown/unknown (reset ?)" in proc.stderr
    )
    assert (
        "::warning::GitHub API quota unknown (rate_limit probe failed);"
        " continuing and relying on per-call retries" in proc.stderr
    )


def test_empty_stdout_probe_shows_empty_values(tmp_path):
    proc = run_preflight(tmp_path, "ok", None, write_ratelimit=False)
    assert proc.returncode == 0
    assert (
        "GitHub API quota: core=/ (reset ?) search=/ (reset ?)"
        " graphql=/ (reset ?)" in proc.stderr
    )


def test_gh_not_found_exits_127(tmp_path):
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    env = dict(os.environ)
    env["PATH"] = str(empty_bin)
    proc = subprocess.run(
        [sys.executable, "scripts/gh_retry.py", "retry", "pr", "list"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 127
    assert "gh: command not found" in proc.stderr


def test_abuse_detection_matches_and_propagates_rc(tmp_path):
    proc = run_retry(tmp_path, "abuse-detection", healthy())
    assert proc.returncode == 7
    assert "abuse detection" in proc.stderr
    sleeps = parse_sleeps(proc.stderr)
    assert len(sleeps) == 3
    assert "giving up on gh pr list -R acme/widgets after 4/4 attempts" in proc.stderr


def test_custom_env_vars_override_defaults(tmp_path):
    proc = run_retry(
        tmp_path,
        "rate-limit-forever",
        healthy(),
        extra_env={
            "GH_RETRY_MAX_ATTEMPTS": "2",
            "GH_RETRY_MAX_SLEEP": "600",
            "GH_RETRY_BACKOFF_BASE": "5",
        },
    )
    assert proc.returncode == 1
    sleeps = parse_sleeps(proc.stderr)
    # MAX_ATTEMPTS=2 -> 2 total executions (1 + 1 retry); the giving-up check
    # fires on attempt 2 before any sleep, so exactly one backoff (base 5).
    assert len(sleeps) == 1
    assert 5 <= sleeps[0] <= 9, sleeps
    assert "after 2/2 attempts" in proc.stderr


def test_quota_line_format_exact(tmp_path):
    buckets = (4000, 5000, 4102444800, 28, 30, 4102455600, 4000, 5000, 4102444800)
    proc = run_preflight(tmp_path, "ok", buckets)
    assert proc.returncode == 0

    def ts(epoch):
        return datetime.fromtimestamp(epoch, timezone.utc).strftime("%H:%M:%SZ")

    expected = (
        f"GitHub API quota: core=4000/5000 (reset {ts(4102444800)})"
        f" search=28/30 (reset {ts(4102455600)})"
        f" graphql=4000/5000 (reset {ts(4102444800)})"
    )
    assert expected in proc.stderr
