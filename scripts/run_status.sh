#!/usr/bin/env bash
# Classify the run status for the run-result comment.
# Usage: run_status.sh <coordinator_outcome> <coordinator_status> <coordinator_tee_status> <fatal_reason> <timeout_minutes>
# Outputs the STATUS line to stdout.

set -Eeuo pipefail

coordinator_outcome="${1:-}"
coordinator_status="${2:-}"
coordinator_tee_status="${3:-}"
fatal_reason="${4:-}"
timeout_minutes="${5:-120}"

# coordinator_outcome is a step outcome: success, failure, cancelled, skipped
# coordinator_status is the actual exit code from opencode (from steps.coordinator.outputs.coordinator_status)
# coordinator_tee_status is the tee exit code (from steps.coordinator.outputs.coordinator_tee_status)

if [[ -n "$fatal_reason" ]]; then
  echo "❌ fatal error: $fatal_reason"
  exit 0
fi

if [[ "$coordinator_outcome" == "success" ]]; then
  echo "✅ completed"
  exit 0
fi

# Step was cancelled or skipped before coordinator finished
if [[ "$coordinator_outcome" == "cancelled" || "$coordinator_outcome" == "skipped" ]]; then
  echo "⚠️ cancelled before the coordinator finished"
  exit 0
fi

# coordinator_outcome is "failure" - use the actual exit code
# coordinator_status holds the real exit code (124 for timeout, other non-zero for errors)
exit_code="${coordinator_status:-${coordinator_tee_status:-unknown}}"

if [[ "$exit_code" == "124" ]]; then
  echo "⏱️ timed out after ${timeout_minutes}m (coordinator killed by timeout)"
  exit 0
fi

if [[ "$exit_code" != "unknown" && "$exit_code" != "0" ]]; then
  echo "⚠️ failed (coordinator exit $exit_code)"
  exit 0
fi

# Fallback - should not happen but handle gracefully
echo "⚠️ failed (coordinator exit $coordinator_outcome)"
exit 0
