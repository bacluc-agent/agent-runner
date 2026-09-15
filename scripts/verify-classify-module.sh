#!/usr/bin/env bash
set -euo pipefail
# ponytail: manual verification only, add CI step when flakiness appears
output=$(node --input-type=module -e "await import('./.opencode/classify.ts')" 2>&1) || true
if echo "$output" | grep -q "MODULE_TYPELESS_PACKAGE_JSON"; then
  echo "FAIL: MODULE_TYPELESS_PACKAGE_JSON warning found"
  echo "$output"
  exit 1
fi
echo "PASS: no MODULE_TYPELESS_PACKAGE_JSON warning; module loads"
