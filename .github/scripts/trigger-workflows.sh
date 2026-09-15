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
  fi
  if [[ -z "$base_ref" ]]; then
    if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
      base_ref="HEAD~1"
      changed_files=$(git diff --name-only "$base_ref" HEAD 2>/dev/null | grep '^\.github/' || true)
    fi
  fi
fi

# Also check unstaged/staged changes
if [[ -z "$changed_files" ]]; then
  changed_files=$(git diff --name-only --cached 2>/dev/null | grep '^\.github/' || true)
fi
if [[ -z "$changed_files" ]]; then
  changed_files=$(git ls-files --others --exclude-standard 2>/dev/null | grep '^\.github/' || true)
fi

run_urls=""
if [[ -n "$changed_files" ]]; then
  printf 'Changed .github/ files detected:\n%s\n' "$changed_files"
  while IFS= read -r file; do
    [[ -n "$file" ]] || continue
    workflow_file=$(map_file_to_workflow_file "$file")
    workflow_name="${workflow_file%.yml}"
    if [[ ! -f ".github/workflows/$workflow_file" ]]; then
      printf 'Workflow file %s not found, skipping\n' "$workflow_file"
      continue
    fi
    printf 'Triggering workflow %s (%s) for changed file %s\n' "$workflow_name" "$workflow_file" "$file"
    # Trigger workflow_dispatch and capture URL
    if [[ "$workflow_file" == "opencode.yml" ]]; then
      url=""
      if command -v jq >/dev/null 2>&1; then
        url=$(gh workflow run opencode.yml --repo "${GITHUB_REPOSITORY}" --ref "${GITHUB_REF_NAME:-main}" --field prompt="Test .github workflow trigger for issue #201" 2>/dev/null | jq -r '.html_url // empty' || true)
      else
        url=$(gh workflow run opencode.yml --repo "${GITHUB_REPOSITORY}" --ref "${GITHUB_REF_NAME:-main}" --field prompt="Test .github workflow trigger for issue #201" 2>/dev/null | grep -oE 'https://github.com/[^/]+/[^/]+/actions/runs/[0-9]+' || true)
      fi
    else
      url=""
      if command -v jq >/dev/null 2>&1; then
        url=$(gh workflow run "$workflow_file" --repo "${GITHUB_REPOSITORY}" --ref "${GITHUB_REF_NAME:-main}" 2>/dev/null | jq -r '.html_url // empty' || true)
      else
        url=$(gh workflow run "$workflow_file" --repo "${GITHUB_REPOSITORY}" --ref "${GITHUB_REF_NAME:-main}" 2>/dev/null | grep -oE 'https://github.com/[^/]+/[^/]+/actions/runs/[0-9]+' || true)
      fi
    fi
    if [[ -n "$url" ]]; then
      printf 'Workflow %s triggered: %s\n' "$workflow_name" "$url"
      run_urls="${run_urls}${workflow_name}: ${url}\n"
    else
      # Try API approach
      if [[ "$workflow_file" == "opencode.yml" ]]; then
        api_response=$(gh api -i repos/"${GITHUB_REPOSITORY}"/actions/workflows/opencode.yml/dispatches \
          -X POST -F ref="${GITHUB_REF_NAME:-main}" -F inputs='{"prompt":"Test .github workflow trigger for issue #201"}' 2>/dev/null || true)
      else
        api_response=$(gh api -i repos/"${GITHUB_REPOSITORY}"/actions/workflows/"${workflow_file}"/dispatches \
          -X POST -F ref="${GITHUB_REF_NAME:-main}" 2>/dev/null || true)
      fi
      # Handle 204 (empty body) as success; parse html_url from body if present
      api_status=$(printf '%s\n' "$api_response" | head -n1 | grep -oE 'HTTP/[0-9.]+ [0-9]+' | awk '{print $2}' || true)
      api_body=$(printf '%s\n' "$api_response" | tail -n +2 || true)
      if [[ "$api_status" == "204" ]]; then
        api_url="https://github.com/${GITHUB_REPOSITORY}/actions/runs"
      else
        api_url=$(printf '%s\n' "$api_body" | jq -r '.html_url // empty' || true)
      fi
      if [[ -n "$api_url" ]]; then
        printf 'Workflow %s triggered (API): %s\n' "$workflow_name" "$api_url"
        run_urls="${run_urls}${workflow_name}: ${api_url}\n"
      fi
    fi
  done <<< "$changed_files"
fi

# Output URLs for downstream steps
RUNNER_TEMP="${RUNNER_TEMP:-/tmp}"
if [[ -n "$run_urls" ]]; then
  printf 'Triggered workflow URLs:\n%s\n' "$run_urls"
  # Write to a file that can be read by other steps
  tmp_dir="${RUNNER_TEMP:-/tmp}"
  printf '%s' "$run_urls" > "$tmp_dir"/workflow-run-urls.txt
fi
