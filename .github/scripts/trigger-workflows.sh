#!/usr/bin/env bash
# Trigger corresponding workflows when .github/ files change and capture URLs.
set -Eeuo pipefail

printf '::add-mask::%s\n' "${GITHUB_TOKEN:-}"

# Map changed .github/ paths to workflow files
map_file_to_workflow() {
  local file="$1"
  case "$file" in
    .github/workflows/ci.yml) echo "ci" ;;
    .github/workflows/hourly-issue.yml) echo "hourly-issue" ;;
    .github/workflows/opencode.yml) echo "opencode" ;;
    .github/workflows/refine-issues.yml) echo "refine-issues" ;;
    .github/workflows/refresh-chatgpt-auth.yml) echo "refresh-chatgpt-auth" ;;
    .github/workflows/renew-interaction-limits.yml) echo "renew-interaction-limits" ;;
    .github/workflows/review-fixes.yml) echo "review-fixes" ;;
    .github/actions/*) echo "opencode" ;;  # actions used by opencode workflow
    .github/AGENTS.md|.github/*.md) echo "opencode" ;;
    *) echo "opencode" ;;
  esac
}

# Detect changed .github/ files in the current branch vs main
changed_files=""
if git rev-parse --verify HEAD >/dev/null 2>&1 && git rev-parse --verify main >/dev/null 2>&1; then
  changed_files=$(git diff --name-only main HEAD 2>/dev/null | grep '^\.github/' || true)
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
    workflow=$(map_file_to_workflow "$file")
    printf 'Triggering workflow %s for changed file %s\n' "$workflow" "$file"
    # Trigger workflow_dispatch and capture URL
    url=$(gh workflow run "$workflow" --repo "${GITHUB_REPOSITORY}" 2>/dev/null | grep -oE 'https://github.com/[^/]+/[^/]+/actions/runs/[0-9]+' || true)
    if [[ -n "$url" ]]; then
      printf 'Workflow %s triggered: %s\n' "$workflow" "$url"
      run_urls="${run_urls}${workflow}: ${url}\n"
    else
      # Try API approach
      api_url=$(gh api repos/"${GITHUB_REPOSITORY}"/actions/workflows/"${workflow}".yml/dispatches \
        -X POST -F ref="${GITHUB_REF_NAME:-main}" 2>/dev/null | jq -r '.html_url // empty' || true)
      if [[ -n "$api_url" ]]; then
        printf 'Workflow %s triggered (API): %s\n' "$workflow" "$api_url"
        run_urls="${run_urls}${workflow}: ${api_url}\n"
      fi
    fi
  done <<< "$changed_files"
fi

# Output URLs for downstream steps
if [[ -n "$run_urls" ]]; then
  printf 'Triggered workflow URLs:\n%s\n' "$run_urls"
  # Write to a file that can be read by other steps
  printf '%s' "$run_urls" > "$RUNNER_TEMP"/workflow-run-urls.txt
fi
