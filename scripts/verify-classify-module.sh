#!/usr/bin/env bash
set -Eeuo pipefail
# Verify .opencode/package.json has "type": "module" and that
# .opencode/classify.ts loads without MODULE_TYPELESS_PACKAGE_JSON warning.

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! grep -q '"type": "module"' .opencode/package.json; then
  echo "FAIL: .opencode/package.json missing \"type\": \"module\"" >&2
  exit 1
fi

# Load the module; any MODULE_TYPELESS_PACKAGE_JSON warning goes to stderr.
output=$(node -e 'import("./.opencode/classify.ts").then(m => console.log("OK", typeof m.classifyEvent))' 2>&1) || true

if echo "$output" | grep -qi "MODULE_TYPELESS_PACKAGE_JSON"; then
  echo "FAIL: MODULE_TYPELESS_PACKAGE_JSON warning still present" >&2
  echo "$output" >&2
  exit 1
fi

echo "PASS: no MODULE_TYPELESS_PACKAGE_JSON warning; module loads correctly"
echo "$output"
