#!/usr/bin/env bash
set -Eeuo pipefail

backend="$(command -v gh)" || { printf '%s\n' 'gh guard: real gh backend not found' >&2; exit 1; }
guard_dir="${RUNNER_TEMP:?}/gh-guard"
backend="$(realpath "$backend")"
if [[ ! -x "$backend" || "$backend" == "$(realpath -m "$guard_dir/gh")" ]]; then
  printf '%s\n' 'gh guard: missing or recursive backend' >&2
  exit 1
fi
mkdir -p "$guard_dir"
cp "$(dirname "${BASH_SOURCE[0]}")/gh_guard.py" "$guard_dir/gh"
chmod 755 "$guard_dir/gh"
printf '%s\n' "$backend" > "$guard_dir/real-gh"
printf '%s\n' "$guard_dir" >> "${GITHUB_PATH:?}"
