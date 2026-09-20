#!/usr/bin/env bash
# Reusable script: fetch bacluc-agent/agent-runner GitHub Actions runs,
# build a markdown table, and post/update a comment on the standing issue.
# Idempotent: updates existing bot comment for this run window instead of spamming.
# Never closes the standing issue.

set -Eeuo pipefail

# Configurable via environment; defaults match the standing issue.
REPO="${RUN_HISTORY_REPO:-bacluc-agent/agent-runner}"
ISSUE_NUMBER="${RUN_HISTORY_ISSUE:-219}"
ISSUE_REPO="${RUN_HISTORY_ISSUE_REPO:-bacluc-agent/agent-todo}"
LIMIT="${RUN_HISTORY_LIMIT:-30}"
DRY_RUN="${RUN_HISTORY_DRY_RUN:-}"

# Markdown escaping for table cells
md_esc() {
  printf '%s' "$1" | sed 's/|/\\|/g; s/\n/ /g; s/\r//g' | tr -d '\t'
}

# Duration in minutes (rounded)
duration_min() {
  local start="$1" end="$2"
  if [[ -z "$start" || "$start" == "null" ]]; then
    echo "—"
    return
  fi
  local start_epoch end_epoch
  start_epoch=$(date -d "$start" +%s 2>/dev/null || echo 0)
  if [[ -z "$end" || "$end" == "null" ]]; then
    end_epoch=$(date +%s)
  else
    end_epoch=$(date -d "$end" +%s 2>/dev/null || echo 0)
  fi
  if (( start_epoch <= 0 || end_epoch <= 0 )); then
    echo "—"
    return
  fi
  local diff=$((end_epoch - start_epoch))
  if (( diff < 60 )); then
    echo "${diff}s"
  else
    echo "$((diff / 60))m"
  fi
}

# Fetch paginated runs via gh api (max 3 pages to stay fast)
fetch_runs() {
  local page=1
  local max_pages=3
  local all_runs="[]"
  while (( page <= max_pages )); do
    local resp
    resp=$(gh api "repos/${REPO}/actions/runs?per_page=${LIMIT}&page=${page}" --jq '.workflow_runs // []' 2>/dev/null || echo '[]')
    local count
    count=$(echo "$resp" | jq 'length')
    if (( count == 0 )); then
      break
    fi
    all_runs=$(echo "$all_runs" "$resp" | jq -s 'add')
    if (( count < LIMIT )); then
      break
    fi
    page=$((page + 1))
  done
  echo "$all_runs"
}

# Build markdown table from JSON array of runs
build_table() {
  local runs_json="$1"
  local count
  count=$(echo "$runs_json" | jq 'length')
  if (( count == 0 )); then
    echo "No runs found for ${REPO}."
    return
  fi

  printf '### Last %d runs from `%s` (updated %s)\n\n' "$count" "$REPO" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '| Run ID | Workflow | Status / Conclusion | Branch | Event | Created (UTC) | Updated (UTC) | Duration | Actor |\n'
  printf '|---|---|---|---|---|---|---|---|---|\n'

  echo "$runs_json" | jq -r '.[] | [
    .id,
    .name,
    (.status // "—"),
    (.conclusion // "—"),
    (.head_branch // "—"),
    (.event // "—"),
    (.created_at // "—"),
    (.updated_at // "—"),
    (.run_started_at // .created_at // "—"),
    (.actor.login // "—")
  ] | @tsv' | while IFS=$'\t' read -r id name status conclusion branch event created updated started actor; do
    local link="https://github.com/${REPO}/actions/runs/${id}"
    local status_cell
    if [[ -n "$conclusion" && "$conclusion" != "null" && "$conclusion" != "—" ]]; then
      status_cell="${status} / ${conclusion}"
    else
      status_cell="$status"
    fi
    local dur
    dur=$(duration_min "$started" "$updated")
    printf '| [%s](%s) | %s | %s | %s | %s | %s | %s | %s | %s |\n' \
      "$(md_esc "$id")" "$link" \
      "$(md_esc "$name")" \
      "$(md_esc "$status_cell")" \
      "$(md_esc "$branch")" \
      "$(md_esc "$event")" \
      "$(md_esc "$created")" \
      "$(md_esc "$updated")" \
      "$(md_esc "$dur")" \
      "$(md_esc "$actor")"
  done
  printf '\n_Sorted newest-first; truncated at %d runs. Never closes issue #%s._\n' "$LIMIT" "$ISSUE_NUMBER"
}

# Find existing bot comment on the issue (by body marker)
find_bot_comment() {
  local issue_repo="$1" issue_num="$2"
  gh issue view "$issue_num" -R "$issue_repo" --json comments --jq '.comments[] | select(.author.login == "bacluc-agent") | .id' 2>/dev/null | head -n1 || true
}

# Post or update comment
post_or_update() {
  local body="$1"
  if [[ -n "${DRY_RUN}" ]]; then
    printf '%s\n' "$body"
    printf '[DRY_RUN] Would post/update comment on %s/%s#%s\n' "$ISSUE_REPO" "$REPO" "$ISSUE_NUMBER" >&2
    return 0
  fi

  local bot_comment_id
  bot_comment_id=$(find_bot_comment "$ISSUE_REPO" "$ISSUE_NUMBER")
  if [[ -n "$bot_comment_id" ]]; then
    gh api -X PATCH "repos/${ISSUE_REPO}/issues/comments/${bot_comment_id}" -f body="$body" 2>/dev/null || {
      printf 'Failed to update comment %s; creating new.\n' "$bot_comment_id" >&2
      gh issue comment "$ISSUE_NUMBER" -R "$ISSUE_REPO" --body "$body" 2>/dev/null || printf 'Failed to post comment.\n' >&2
    }
  else
    gh issue comment "$ISSUE_NUMBER" -R "$ISSUE_REPO" --body "$body" 2>/dev/null || printf 'Failed to post comment.\n' >&2
  fi
}

main() {
  printf 'Fetching runs from %s (limit %d)...\n' "$REPO" "$LIMIT" >&2
  local runs_json
  runs_json=$(fetch_runs)
  local count
  count=$(echo "$runs_json" | jq 'length')
  printf 'Found %d runs.\n' "$count" >&2

  local table_body
  table_body=$(build_table "$runs_json")

  # Add a header identifying this as the bot's standing-issue table
  local full_body
  full_body="Standing run-history table for [${REPO}](https://github.com/${REPO}) — issue #${ISSUE_NUMBER} (never close).\n\n${table_body}"

  post_or_update "$full_body"
  printf 'Done.\n' >&2
}

main "$@"
