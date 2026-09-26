#!/usr/bin/env python3
"""Classify the run-result comment status from the coordinator's real exit codes."""
import os
import sys


def classify(outcome: str, status: str, tee: str, fatal: str) -> str:
    if outcome == "success":
        return "✅ completed"
    if fatal:
        return f"❌ fatal error: {fatal}"
    if status == "0":
        return f"✅ completed (log capture failed, tee exit {tee})"
    if outcome in ("cancelled", "skipped"):
        return "⚠️ cancelled before the coordinator finished"
    if status == "124":
        return "⏱️ timed out (coordinator exit 124)"
    if status:
        return f"⚠️ failed (coordinator exit {status})"
    return f"⚠️ failed (coordinator exit {outcome})"


def main() -> int:
    outcome = os.environ.get("COORDINATOR_OUTCOME", "")
    status = os.environ.get("COORDINATOR_STATUS", "")
    tee = os.environ.get("COORDINATOR_TEE_STATUS", "")
    fatal = os.environ.get("FATAL_REASON", "")
    result = classify(outcome, status, tee, fatal)
    # One grep-able line per run: which branch was taken and from which inputs.
    print(
        f"run_status: outcome={outcome!r} status={status!r} tee={tee!r} fatal={fatal!r} -> {result}",
        file=sys.stderr,
    )
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
