#!/usr/bin/env bash
# Trigger corresponding workflows when .github/ files change and capture URLs.
set -Eeuo pipefail

RUNNER_TEMP="${RUNNER_TEMP:-/tmp}"
mkdir -p "$RUNNER_TEMP"

printf '::add-mask::%s\n' "${GITHUB_TOKEN:-}"

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
    changed_files=$(git diff --name-only "$base_ref" HEAD 2>/dev/null | grep '^\.github/' || true)
  elif git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
    changed_files=$(git diff --name-only HEAD~1 HEAD 2>/dev/null | grep '^\.github/' || true)
  fi
fi

# Also check unstaged/staged changes
if [[ -z "$changed_files" ]]; then
  changed_files=$(git diff --name-only --cached 2>/dev/null | grep '^\.github/' || true)
fi
if [[ -z "$changed_files" ]]; then
  changed_files=$(git ls-files --others --exclude-standard 2>/dev/null | grep '^\.github/' || true)
fi

# Trigger each unique mapped workflow once and capture its run URL
run_urls=""
if [[ -n "$changed_files" ]]; then
  printf 'Changed .github/ files detected:\n%s\n' "$changed_files"
  workflow_files=$(printf '%s\n' "$changed_files" | while IFS= read -r file; do
    [[ -n "$file" ]] || continue
    map_file_to_workflow_file "$file"
  done | sort -u)
  while IFS= read -r workflow_file; do
    [[ -n "$workflow_file" ]] || continue
    if [[ ! -f ".github/workflows/$workflow_file" ]]; then
      printf 'Workflow file %s not found, skipping\n' "$workflow_file"
      continue
    fi
    workflow_name="${workflow_file%.yml}"
    printf 'Triggering workflow %s (%s)\n' "$workflow_name" "$workflow_file"
    if [[ "$workflow_file" == "opencode.yml" ]]; then
      gh workflow run opencode.yml --repo "${GITHUB_REPOSITORY}" --ref "${GITHUB_REF_NAME:-main}" --field prompt="Test .github workflow trigger for issue #201" || true
    else
      gh workflow run "$workflow_file" --repo "${GITHUB_REPOSITORY}" --ref "${GITHUB_REF_NAME:-main}" || true
    fi
    # gh workflow run prints nothing on success, so poll for the run URL
    url=""
    for _ in $(seq 1 6); do
      sleep 5
      run_json=$(gh run list --workflow="$workflow_file" --branch="${GITHUB_REF_NAME:-main}" --json databaseId,url --limit 1 2>/dev/null || true)
      database_id=$(printf '%s' "$run_json" | jq -r '.[0].databaseId // empty' 2>/dev/null || true)
      if [[ -n "$database_id" && "$database_id" != "${GITHUB_RUN_ID:-}" ]]; then
        url="https://github.com/${GITHUB_REPOSITORY}/actions/runs/${database_id}"
        break
      fi
    done
    if [[ -n "$url" ]]; then
      printf 'Workflow %s triggered: %s\n' "$workflow_name" "$url"
      run_urls="${run_urls}${workflow_name}: ${url}"$'\n'
    else
      printf 'Workflow %s triggered but run URL not found yet\n' "$workflow_name"
    fi
  done <<< "$workflow_files"
fi

# Output URLs for downstream steps
if [[ -n "$run_urls" ]]; then
  printf 'Triggered workflow URLs:\n%s' "$run_urls"
  printf '%s' "$run_urls" > "$RUNNER_TEMP"/workflow-run-urls.txt
fi