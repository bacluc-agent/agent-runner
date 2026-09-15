#!/usr/bin/env bash
# Trigger corresponding workflows when .github/ files change and capture URLs.
set -Eeuo pipefail

prompt="${1:-Test the .github workflow changes on this branch}"

RUNNER_TEMP="${RUNNER_TEMP:-/tmp}"
mkdir -p "$RUNNER_TEMP"
BRANCH="${BRANCH:-${GITHUB_REF_NAME:-main}}"
TRIGGER_REF="${TRIGGER_REF:-${BRANCH:-${GITHUB_REF_NAME:-main}}}"
TRIGGER_PROMPT="${TRIGGER_PROMPT:-${prompt:-Test .github workflow trigger for issue #${ISSUE_NUMBER:-201}}}"
BRANCH="$TRIGGER_REF"
prompt="$TRIGGER_PROMPT"

# Map changed .github/ paths to workflow file names
map_file_to_workflow_file() {
  local file="$1"
  case "$file" in
    .github/workflows/ci.yml) echo "ci.yml" ;;
    .github/workflows/hourly-issue.yml) echo "hourly-issue.yml" ;;
    .github/workflows/opencode.yml) echo "opencode.yml" ;;
    .github/workflows/refine-issues.yml) echo "refine-issues.yml" ;;
    .github/workflows/refresh-chatgpt-auth.yml) echo "refresh-chatgpt-auth.yml" ;;
    .github/workflows/renew-interaction-limits.yml) echo "renew-interaction-limits.yml" ;;
    .github/workflows/review-fixes.yml) echo "review-fixes.yml" ;;
    .github/actions/*) echo "opencode.yml" ;;  # actions used by opencode workflow
    .github/AGENTS.md|.github/*.md) echo "opencode.yml" ;;
    AGENTS.md) echo "opencode.yml" ;;
    *) echo "opencode.yml" ;;
  esac
}

# Detect changed .github/ files in the current branch vs main
changed_files=""
if git rev-parse --verify HEAD >/dev/null 2>&1; then
  base_ref=""
  for ref in main origin/main; do
    if git rev-parse --verify "$ref" >/dev/null 2>&1; then
      base_ref="$ref"
      break
    fi
  done
  if [[ -n "$base_ref" ]]; then
    changed_files=$(git diff --name-only "$base_ref...HEAD" 2>/dev/null | grep -E '^(\.github/|AGENTS\.md)' || true)
  fi
  if [[ -z "$base_ref" ]]; then
    if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
      base_ref="HEAD~1"
      changed_files=$(git diff --name-only "$base_ref...HEAD" 2>/dev/null | grep -E '^(\.github/|AGENTS\.md)' || true)
    fi
  fi
fi

# Also check unstaged/staged changes
if [[ -z "$changed_files" ]]; then
  changed_files=$(git diff --name-only --cached 2>/dev/null | grep -E '^(\.github/|AGENTS\.md)' || true)
fi
if [[ -z "$changed_files" ]]; then
  changed_files=$(git ls-files --others --exclude-standard 2>/dev/null | grep -E '^(\.github/|AGENTS\.md)' || true)
fi

run_urls=""
if [[ -n "$changed_files" ]]; then
  printf 'Changed .github/ files detected:\n%s\n' "$changed_files"
  # Map changed files to workflow files, dedupe so each workflow triggers once
  workflow_files=""
  while IFS= read -r file; do
    [[ -n "$file" ]] || continue
    workflow_file=$(map_file_to_workflow_file "$file")
    if [[ -z "$workflow_file" ]]; then printf 'Skipping %s (no workflow_dispatch)\n' "$file"; continue; fi
    workflow_files="${workflow_files}${workflow_file}"$'\n'
  done <<< "$changed_files"
  workflow_files=$(printf '%s\n' "$workflow_files" | sed '/^$/d' | sort -u)

  while IFS= read -r workflow_file; do
    [[ -n "$workflow_file" ]] || continue
    workflow_name="${workflow_file%.yml}"
    if [[ ! -f ".github/workflows/$workflow_file" ]]; then
      printf 'Workflow file %s not found, skipping\n' "$workflow_file"
      continue
    fi
    printf 'Triggering workflow %s (%s)\n' "$workflow_name" "$workflow_file"
    extra_args=()
    if grep -q 'skip_workflow_trigger' ".github/workflows/$workflow_file" 2>/dev/null; then
      extra_args+=(--field skip_workflow_trigger=true)
    fi
    if [[ "$workflow_file" == "opencode.yml" ]]; then
      extra_args+=(--field prompt="$TRIGGER_PROMPT")
    fi
    url=$(gh workflow run "$workflow_file" --repo "${GITHUB_REPOSITORY}" --ref "$TRIGGER_REF" "${extra_args[@]}" 2>&1 | grep -oE 'https://github.com/[^/]+/[^/]+/actions/runs/[0-9]+' | head -1 || true)
    if [[ -z "$url" ]]; then
      for _ in 1 2 3; do
        sleep 5
        url=$(gh run list --workflow="$workflow_file" --repo "${GITHUB_REPOSITORY}" --branch "$TRIGGER_REF" --limit 5 --json databaseId,url -q ".[] | select(.databaseId != ${GITHUB_RUN_ID:-0}) | .url" 2>/dev/null | head -1 || true)
        [[ -n "$url" ]] && break
      done
    fi
    if [[ -n "$url" ]]; then
      printf 'Workflow %s triggered: %s\n' "$workflow_name" "$url"
      run_urls="${run_urls}${workflow_name}: ${url}"$'\n'
    fi
  done <<< "$workflow_files"
fi

# Output URLs for downstream steps
if [[ -n "$run_urls" ]]; then
  printf 'Triggered workflow URLs:\n%s\n' "$run_urls"
  # Write to a file that can be read by other steps
  tmp_dir="${RUNNER_TEMP:-/tmp}"
  printf '%s' "$run_urls" > "$tmp_dir"/workflow-run-urls.txt
fi
