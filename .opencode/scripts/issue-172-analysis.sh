#!/usr/bin/env bash
# Helper script for bacluc-agent/agent-todo#172 — flaky e2e analysis
# Self-check: verifies cadence and lists recent failures
set -euo pipefail

echo "=== Issue 172 cadence check ==="
last_analysis=$(gh issue view 172 -R bacluc-agent/agent-todo --json comments --jq '.comments[] | select(.body | contains("Analysis iteration")) | .createdAt' | sort | tail -n1)
echo "Last analysis: $last_analysis"

echo "=== Recent e2e failures (ecamp/ecamp3) ==="
gh run list --repo ecamp/ecamp3 --workflow e2e-tests.yml --status failure --limit 10 --json databaseId,createdAt,displayTitle,url | head -n 20
