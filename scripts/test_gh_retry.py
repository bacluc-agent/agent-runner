"""Tests for scripts/gh-retry.sh (the rate-limit-aware gh wrapper)."""

import os
import re
import subprocess
import textwrap
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

RETRY_DRIVER = textwrap.dedent(
    """\
    set -Eeuo pipefail
    sleep() { printf 'sleep %s\\n' "$1" >> "$TRACE"; }
    source scripts/gh-retry.sh
    if gh_retry pr list -R acme/widgets; then
      printf 'rc=0\\n'
    else
      printf 'rc=%s\\n' "$?"
    fi
    printf 'DONE\\n'
    """
)

PREFLIGHT_DRIVER = textwrap.dedent(
    """\
    set -Eeuo pipefail
    source scripts/gh-retry.sh
    gh_preflight "issue selection" core graphql
    printf 'AFTER\\n'
    """
)

STUB_GH = textwrap.dedent(
    """\
    #!/usr/bin/env bash
    if [[ "${1:-}" == api && "${2:-}" == rate_limit ]]; then
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


def run(tmp_path, mode, buckets, driver):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(STUB_GH)
    gh.chmod(0o755)
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    (stub_dir / "ratelimit.tsv").write_text(
        "\t".join(str(value) for value in buckets) + "\n"
    )
    trace = tmp_path / "trace"
    trace.write_text("")
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["STUB_DIR"] = str(stub_dir)
    env["STUB_MODE"] = mode
    env["TRACE"] = str(trace)
    proc = subprocess.run(
        ["bash", "-c", driver],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    sleeps = [
        int(match.group(1))
        for line in trace.read_text().splitlines()
        if (match := re.fullmatch(r"sleep (\d+)", line))
    ]
    return proc, sleeps


def test_rate_limit_retries_with_exponential_backoff_then_succeeds(tmp_path):
    buckets = healthy()
    proc, sleeps = run(tmp_path, "rate-limit-twice", buckets, RETRY_DRIVER)
    assert proc.returncode == 0
    assert proc.stdout.startswith("OK:pr list -R acme/widgets")
    assert "rc=0" in proc.stdout
    assert "DONE" in proc.stdout
    assert len(sleeps) == 2
    assert 10 <= sleeps[0] <= 14, sleeps
    assert 20 <= sleeps[1] <= 24, sleeps
    assert "(attempt 1/4)" in proc.stderr
    assert "(attempt 2/4)" in proc.stderr
    assert "giving up" not in proc.stderr
    assert (
        "GitHub API quota after gh pr list -R acme/widgets: core=" in proc.stderr
    )
    assert "HTTP 403: API rate limit exceeded" in proc.stderr


def test_gives_up_loudly_after_max_attempts(tmp_path):
    buckets = healthy()
    proc, sleeps = run(tmp_path, "rate-limit-forever", buckets, RETRY_DRIVER)
    assert proc.returncode == 0
    assert "rc=1" in proc.stdout
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
    proc, sleeps = run(tmp_path, "rate-limit-forever", exhausted, RETRY_DRIVER)
    assert proc.returncode == 0
    assert "rc=1" in proc.stdout
    assert sleeps == []
    assert "not retrying" in proc.stderr
    assert "resets at" in proc.stderr


def test_exhausted_core_with_near_reset_sleeps_until_reset(tmp_path):
    buckets = healthy()
    now = int(time.time())
    exhausted = (0, 5000, now + 30, *buckets[3:6], *buckets[6:])
    proc, sleeps = run(tmp_path, "rate-limit-once", exhausted, RETRY_DRIVER)
    assert proc.returncode == 0
    assert "rc=0" in proc.stdout
    assert len(sleeps) == 1
    assert 28 <= sleeps[0] <= 36, sleeps
    assert "until the core reset" in proc.stderr


def test_non_rate_limit_failure_is_not_retried(tmp_path):
    buckets = healthy()
    proc, sleeps = run(tmp_path, "not-rate-limit", buckets, RETRY_DRIVER)
    assert proc.returncode == 0
    assert "rc=1" in proc.stdout
    assert sleeps == []
    assert "HTTP 404: Not Found" in proc.stderr
    assert "(attempt " not in proc.stderr
    assert "giving up" not in proc.stderr


def test_preflight_stands_down_loudly_when_quota_is_exhausted(tmp_path):
    buckets = healthy()
    now = int(time.time())
    exhausted = (0, 5000, now + 3600, *buckets[3:6], *buckets[6:])
    proc, sleeps = run(tmp_path, "ok", exhausted, PREFLIGHT_DRIVER)
    assert proc.returncode == 0
    assert "GitHub API quota: core=0/5000" in proc.stderr
    assert "::error::GitHub API core quota exhausted" in proc.stderr
    assert "standing down: skipping issue selection this run" in proc.stderr
    assert "AFTER" not in proc.stdout + proc.stderr


def test_preflight_proceeds_when_quota_is_available(tmp_path):
    buckets = healthy()
    proc, sleeps = run(tmp_path, "ok", buckets, PREFLIGHT_DRIVER)
    assert proc.returncode == 0
    assert "core=4000/5000" in proc.stderr
    assert "standing down" not in proc.stderr
    assert "AFTER" in proc.stdout


def test_preflight_ignores_buckets_the_step_does_not_use(tmp_path):
    buckets = healthy()
    now = int(time.time())
    search_empty = (*buckets[0:3], 0, 30, now + 3600, *buckets[6:])
    proc, sleeps = run(tmp_path, "ok", search_empty, PREFLIGHT_DRIVER)
    assert proc.returncode == 0
    assert "AFTER" in proc.stdout
    assert "standing down" not in proc.stderr
