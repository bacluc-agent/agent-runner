#!/usr/bin/env python3
"""Tests for run_status.sh classification logic."""

import subprocess
import sys


def run_status(*args):
    """Run the run_status.sh script and return stdout stripped."""
    result = subprocess.run(
        ["./scripts/run_status.sh", *args],
        capture_output=True,
        text=True,
        cwd="/home/runner/work/agent-runner/agent-runner",
    )
    return result.stdout.strip(), result.returncode


class TestRunStatus:
    def test_exit_0_success(self):
        out, code = run_status("success", "0", "0", "", "120")
        assert code == 0
        assert out == "✅ completed"

    def test_fatal_reason_takes_priority(self):
        out, code = run_status("failure", "1", "0", "balance", "120")
        assert code == 0
        assert out == "❌ fatal error: balance"

    def test_fatal_reason_with_success_outcome(self):
        # Fatal reason should win even if outcome says success (defensive)
        out, code = run_status("success", "0", "0", "auth", "120")
        assert code == 0
        assert out == "❌ fatal error: auth"

    def test_timeout_exit_124(self):
        out, code = run_status("failure", "124", "0", "", "120")
        assert code == 0
        assert out == "⏱️ timed out after 120m (coordinator killed by timeout)"

    def test_timeout_with_custom_timeout_minutes(self):
        out, code = run_status("failure", "124", "0", "", "30")
        assert code == 0
        assert out == "⏱️ timed out after 30m (coordinator killed by timeout)"

    def test_other_nonzero_exit(self):
        out, code = run_status("failure", "1", "0", "", "120")
        assert code == 0
        assert out == "⚠️ failed (coordinator exit 1)"

    def test_other_nonzero_exit_130(self):
        out, code = run_status("failure", "130", "0", "", "120")
        assert code == 0
        assert out == "⚠️ failed (coordinator exit 130)"

    def test_cancelled_before_coordinator_finished(self):
        out, code = run_status("cancelled", "0", "0", "", "120")
        assert code == 0
        assert out == "⚠️ cancelled before the coordinator finished"

    def test_skipped_before_coordinator_finished(self):
        out, code = run_status("skipped", "0", "0", "", "120")
        assert code == 0
        assert out == "⚠️ cancelled before the coordinator finished"

    def test_failure_with_unknown_exit_code_fallback(self):
        # When coordinator_status is empty but outcome is failure
        out, code = run_status("failure", "", "0", "", "120")
        assert code == 0
        assert out == "⚠️ failed (coordinator exit failure)"

    def test_failure_with_tee_status_fallback(self):
        # When coordinator_status empty but tee_status has value
        out, code = run_status("failure", "", "2", "", "120")
        assert code == 0
        assert out == "⚠️ failed (coordinator exit 2)"


if __name__ == "__main__":
    # Run with pytest if available, otherwise run manually
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))