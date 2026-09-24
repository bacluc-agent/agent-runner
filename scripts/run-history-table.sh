#!/usr/bin/env bash
# Reusable script: fetch bacluc-agent/agent-runner GitHub Actions runs created
# since the last table's coverage window, build a markdown table (run, time,
# selected issue, model, PR, merged), and post/update a comment on the standing
# issue. Idempotent: updates the existing bot table comment for this window.
# Never closes the standing issue.

set -Eeuo pipefail

REPO="${RUN_HISTORY_REPO:-bacluc-agent/agent-runner}"
ISSUE_NUMBER="${RUN_HISTORY_ISSUE:-219}"
ISSUE_REPO="${RUN_HISTORY_ISSUE_REPO:-bacluc-agent/agent-todo}"
DRY_RUN="${RUN_HISTORY_DRY_RUN:-}"
WINDOW_START="${RUN_HISTORY_WINDOW_START:-}"
PR_REPOS="bacluc-agent/agent-runner bacluc-agent/agent-todo bacluc/provision-machines bacluc-agent/ecamp3 ecamp/ecamp3"

md_esc() {
  printf '%s' "$1" | sed 's/|/\\|/g; s/\n/ /g; s/\r//g' | tr -d '\t'
}

# Find the last bot table comment; prints TSV: id, generated, since, prev_ids.
find_last_table_comment() {
  local comments
  comments=$(gh api --paginate "repos/${ISSUE_REPO}/issues/${ISSUE_NUMBER}/comments?per_page=100" 2>/dev/null || echo '[]')
  local last
  last=$(echo "$comments" | jq -r '[.[] | select(.user.login == "bacluc-agent" and (.body | contains("### Last 24h runs")))] | last | .id // empty' 2>/dev/null || true)
  if [[ -z "$last" ]]; then
    return 1
  fi
  local body generated since prev
  body=$(echo "$comments" | jq -r --arg id "$last" '.[] | select(.id == ($id|tonumber)) | .body')
  generated=$(printf '%s' "$body" | grep -oE 'generated [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z' | head -n1 | sed 's/generated //' || true)
  since=$(printf '%s' "$body" | grep -oE 'since [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z' | head -n1 | sed 's/since //' || true)
  prev=$(printf '%s' "$body" | grep -oE 'previous tables: [0-9, ]+' | head -n1 | sed 's/previous tables: //' || true)
  printf '%s\t%s\t%s\t%s\n' "$last" "$generated" "$since" "$prev"
}

# Fetch runs created at/after window_start (newest first), paginated.
fetch_runs_since() {
  local window_start="$1"
  local page=1
  local all_runs="[]"
  while true; do
    local resp count keep oldest
    resp=$(gh api "repos/${REPO}/actions/runs?per_page=100&page=${page}" --jq '.workflow_runs // []' 2>/dev/null || echo '[]')
    count=$(echo "$resp" | jq 'length')
    if (( count == 0 )); then
      break
    fi
    keep=$(echo "$resp" | jq --arg ws "$window_start" '[.[] | select(.created_at >= $ws)]')
    all_runs=$(echo "$all_runs" "$keep" | jq -s 'add')
    oldest=$(echo "$resp" | jq -r '.[-1].created_at')
    if [[ "$oldest" < "$window_start" ]]; then
      break
    fi
    page=$((page + 1))
  done
  echo "$all_runs"
}

# Concatenated, ANSI-stripped job logs for a run (timestamped lines preferred).
job_log() {
  local run_id="$1"
  local jobs job_id jl ts attempt
  jobs=$(gh api "repos/${REPO}/actions/runs/${run_id}/jobs" --jq '.jobs[] | .id' 2>/dev/null || true)
  for job_id in $jobs; do
    jl=""
    for attempt in 1 2 3 4 5; do
      if jl=$(gh api --allow-escape-sequences "repos/${REPO}/actions/jobs/${job_id}/logs" 2>/dev/null); then
        break
      fi
      jl=""
      sleep 5
    done
    jl=$(printf '%s' "$jl" | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g')
    ts=$(printf '%s' "$jl" | grep -E '^[0-9]{4}-[0-9]{4}' || true)
    if [[ -n "$ts" ]]; then
      jl="$ts"
    fi
    printf '%s\n' "$jl"
  done
}

extract_issue() {
  local log="$1"
  printf '%s' "$log" | grep -E 'Implement \**?[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[0-9]+' | grep -v 'does not exist' | head -n1 | sed -E 's/.*Implement \**([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+#[0-9]+).*/\1/' || true
}

extract_models() {
  local log="$1"
  local sel coord
  sel=$(printf '%s' "$log" | grep -oE 'Issue selection model: [A-Za-z0-9][A-Za-z0-9._/-]*' | head -n1 | sed 's/Issue selection model: //' || true)
  coord=$(printf '%s' "$log" | grep -oE 'Chosen model is [A-Za-z0-9][A-Za-z0-9._/-]*' | head -n1 | sed 's/Chosen model is //' || true)
  if [[ -n "$sel" && -n "$coord" && "$sel" != "$coord" ]]; then
    printf '%s / %s\n' "$sel" "$coord"
  elif [[ -n "$sel" ]]; then
    printf '%s\n' "$sel"
  elif [[ -n "$coord" ]]; then
    printf '%s\n' "$coord"
  fi
}

extract_failure() {
  local log="$1"
  printf '%s' "$log" | grep -oE '##\[error\]fatal provider error \([^)]*\) from model [A-Za-z0-9][A-Za-z0-9._/-]*' | head -n1 || true
}

extract_noop() {
  local log="$1"
  printf '%s' "$log" | grep -oE 'No (unrefined|unclaimed) open issues; nothing to do\.\s*$' | head -n1 || true
}

# Fallback: model from the run's own progress comment on the issue.
model_from_progress_comment() {
  local run_id="$1"
  local comments
  comments=$(gh api --paginate "repos/${ISSUE_REPO}/issues/${ISSUE_NUMBER}/comments?per_page=100" 2>/dev/null || echo '[]')
  echo "$comments" | jq -r --arg run_id "$run_id" '[.[] | select(.body | contains("runs/" + $run_id)) | .body] | last' 2>/dev/null | grep -oE 'model: [A-Za-z0-9][A-Za-z0-9._/-]*' | head -n1 | sed 's/model: //' || true
}

# Find the PR for a run: runId-scoped matches first, then issue branch prefix.
find_pr() {
  local issue_num="$1" run_id="$2" run_created="$3"
  local repo prs match
  for repo in $PR_REPOS; do
    prs=$(gh pr list -R "$repo" --state all --limit 200 --json number,headRefName,state,mergedAt,title,createdAt 2>/dev/null || echo '[]')
    match=$(printf '%s' "$prs" | jq -r --arg run_id "$run_id" --arg issue_num "$issue_num" --arg created "$run_created" --arg repo "$repo" '
      .[] | select(
        (.headRefName == ("agent-run/" + $issue_num + "-" + $run_id)) or
        (.title | contains($run_id)) or
        (.headRefName | contains($run_id)) or
        ((.headRefName | startswith("issue-" + $issue_num + "-")) and (.createdAt >= $created))
      ) | {number, state, mergedAt, repo: $repo}
    ' | head -n1)
    if [[ -n "$match" ]]; then
      printf '%s\n' "$match"
      return 0
    fi
  done
  return 1
}

build_table() {
  local runs_json="$1" window_start="$2" last_id="$3" prev_ids="$4"
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '### Last 24h runs (generated %s, since %s)\n' "$now" "$window_start"
  if [[ -n "$last_id" ]]; then
    printf 'Non-overlapping continuation of %s (previous tables: %s)\n' "$last_id" "$prev_ids"
  fi
  printf '\n| Run | Time (UTC) | Selected Issue | Model | PR | Merged? |\n'
  printf '|---|---|---|---|---|---|\n'

  local ids id
  mapfile -t ids < <(echo "$runs_json" | jq -r '.[].id')
  local rows=() notes=()
  local issue_gaps=0 model_gaps=0 pr_gaps=0
  for id in "${ids[@]}"; do
    local run created status event branch name
    run=$(echo "$runs_json" | jq -c --arg id "$id" '.[] | select(.id == ($id|tonumber))')
    created=$(echo "$run" | jq -r '.created_at // ""')
    status=$(echo "$run" | jq -r '.status // ""')
    event=$(echo "$run" | jq -r '.event // ""')
    branch=$(echo "$run" | jq -r '.head_branch // ""')
    name=$(echo "$run" | jq -r '.name // ""')

    local time_cell
    time_cell=$(date -u -d "$created" +"%Y-%m-%d %H:%M" 2>/dev/null || echo "$created")

    local log issue model noop failure standing
    log=$(job_log "$id")
    issue=$(extract_issue "$log")
    model=$(extract_models "$log")
    if [[ -z "$model" ]]; then
      model=$(model_from_progress_comment "$id")
    fi
    noop=$(extract_noop "$log")
    failure=$(extract_failure "$log")
    standing=""
    if printf '%s' "$log" | grep -qE 'Standing (Issue|Task)'; then
      standing="1"
    elif [[ -n "$issue" ]]; then
      local issue_owner issue_repo issue_num title
      issue_owner=$(printf '%s' "$issue" | cut -d/ -f1)
      issue_repo=$(printf '%s' "$issue" | cut -d/ -f2 | cut -d# -f1)
      issue_num=$(printf '%s' "$issue" | sed -E 's/.*#([0-9]+).*/\1/')
      title=$(gh issue view "$issue_num" -R "${issue_owner}/${issue_repo}" --json title --jq '.title' 2>/dev/null || true)
      if printf '%s' "$title" | grep -qE '^Standing'; then
        standing="1"
      fi
    fi

    local issue_cell="—" model_cell="unknown" pr_cell="no PR" merged_cell="—"
    if [[ -n "$issue" ]]; then
      local owner repo issue_num
      owner=$(printf '%s' "$issue" | cut -d/ -f1)
      repo=$(printf '%s' "$issue" | cut -d/ -f2 | cut -d# -f1)
      issue_num=$(printf '%s' "$issue" | sed -E 's/.*#([0-9]+).*/\1/')
      issue_cell="[${issue}](https://github.com/${owner}/${repo}/issues/${issue_num})"
    else
      issue_gaps=$((issue_gaps + 1))
    fi
    if [[ -n "$model" ]]; then
      model_cell="$model"
    else
      model_gaps=$((model_gaps + 1))
    fi

    local pr=""
    if [[ -n "$issue" ]]; then
      local issue_num
      issue_num=$(printf '%s' "$issue" | sed -E 's/.*#([0-9]+).*/\1/')
      if pr=$(find_pr "$issue_num" "$id" "$created"); then
        local pr_num pr_state pr_merged pr_repo
        pr_num=$(echo "$pr" | jq -r '.number')
        pr_state=$(echo "$pr" | jq -r '.state')
        pr_merged=$(echo "$pr" | jq -r '.mergedAt // ""')
        pr_repo=$(echo "$pr" | jq -r '.repo')
        pr_cell="[#${pr_num}](https://github.com/${pr_repo}/pull/${pr_num})"
        if [[ -n "$pr_merged" && "$pr_merged" != "null" ]]; then
          merged_cell="yes $(date -u -d "$pr_merged" +%Y-%m-%d 2>/dev/null || echo "$pr_merged")"
        elif [[ "$pr_state" == "OPEN" ]]; then
          merged_cell="no"
        elif [[ "$pr_state" == "CLOSED" ]]; then
          merged_cell="closed"
        fi
      else
        pr_gaps=$((pr_gaps + 1))
      fi
    else
      pr_gaps=$((pr_gaps + 1))
    fi

    rows+=("| [${id}](https://github.com/${REPO}/actions/runs/${id}) | ${time_cell} | $(md_esc "$issue_cell") | $(md_esc "$model_cell") | ${pr_cell} | ${merged_cell} |")

    local inprog="is in progress"
    if [[ -n "${GITHUB_RUN_ID:-}" && "$id" == "$GITHUB_RUN_ID" ]]; then
      inprog="is the current in-progress run (this table)"
    fi
    local note=""
    if [[ -n "$noop" ]]; then
      note="- ${id} (${name}) was a no-op (\`${noop}\`), so no issue was selected and no model was used — \`—\`/\`unknown\` are correct per the legend."
    elif [[ -n "$failure" ]]; then
      note="- ${id} (${name}) failed with \`${failure}\`; it was working on ${issue:-the selected issue}."
    elif [[ "$status" == "in_progress" ]]; then
      if [[ -n "$issue" ]]; then
        if [[ "$standing" == "1" ]]; then
          note="- ${id} (${name}) ${inprog}; working on the standing task ${issue} (comment-only, no PR by design)."
        else
          note="- ${id} (${name}) ${inprog}; working on ${issue}, PR not yet created."
        fi
      else
        note="- ${id} (${name}) ${inprog}; logs not yet available."
      fi
    elif [[ -n "$issue" ]]; then
      if [[ -n "$pr" ]]; then
        note="- ${id} (${name}) implemented ${issue}; PR [#${pr_num}](https://github.com/${pr_repo}/pull/${pr_num}) ${pr_state}."
      elif [[ "$standing" == "1" ]]; then
        note="- ${id} (${name}) worked on the standing task ${issue} (comment-only, no PR by design)."
      else
        note="- ${id} (${name}) worked on ${issue}; PR search across ${PR_REPOS} found no PR."
      fi
    else
      note="- ${id} (${name}) is a CI/validation run (event ${event}, branch ${branch}); no agent selection, so issue \`—\`, model \`unknown\`, PR \`no PR\`."
    fi
    notes+=("$note")
  done

  local row
  for row in "${rows[@]}"; do
    printf '%s\n' "$row"
  done
  printf '\nNotes:\n'
  local note
  for note in "${notes[@]}"; do
    printf '%s\n' "$note"
  done
  printf -- '- Fallbacks: issue `—` %d rows, model `unknown` %d rows, PR `no PR` %d rows — PR search across %s for `agent-run/<issue>-<runId>` head refs, run IDs in PR titles/head refs, and `issue-<n>-` branch prefixes found no PRs.\n' "$issue_gaps" "$model_gaps" "$pr_gaps" "${PR_REPOS// /, }"
}

post_or_update() {
  local body="$1" window_start="$2"
  if [[ -n "${DRY_RUN}" ]]; then
    printf '%s\n' "$body"
    printf '[DRY_RUN] Would post/update comment on %s#%s\n' "$ISSUE_REPO" "$ISSUE_NUMBER" >&2
    return 0
  fi
  local comments existing
  comments=$(gh api --paginate "repos/${ISSUE_REPO}/issues/${ISSUE_NUMBER}/comments?per_page=100" 2>/dev/null || echo '[]')
  existing=$(echo "$comments" | jq -r --arg ws "$window_start" '[.[] | select(.user.login == "bacluc-agent" and (.body | contains("since " + $ws)))] | last | .id // empty' 2>/dev/null || true)
  if [[ -n "$existing" ]]; then
    gh api -X PATCH "repos/${ISSUE_REPO}/issues/comments/${existing}" -f body="$body" >/dev/null
    printf 'Updated comment %s on %s#%s\n' "$existing" "$ISSUE_REPO" "$ISSUE_NUMBER" >&2
  else
    gh issue comment "$ISSUE_NUMBER" -R "$ISSUE_REPO" --body "$body" >/dev/null
    printf 'Posted new comment on %s#%s\n' "$ISSUE_REPO" "$ISSUE_NUMBER" >&2
  fi
}

main() {
  local last_info last_id prev_ids window_start
  last_id=""
  prev_ids=""
  if last_info=$(find_last_table_comment); then
    last_id=$(echo "$last_info" | cut -f1)
    local last_generated last_since
    last_generated=$(echo "$last_info" | cut -f2)
    last_since=$(echo "$last_info" | cut -f3)
    prev_ids=$(echo "$last_info" | cut -f4)
    window_start="${WINDOW_START:-${last_generated:-${last_since:-$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)}}}"
    if [[ -n "$prev_ids" ]]; then
      prev_ids="${prev_ids}, ${last_id}"
    else
      prev_ids="$last_id"
    fi
  else
    window_start="${WINDOW_START:-$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)}"
  fi
  printf 'Window start: %s\n' "$window_start" >&2

  local runs_json count
  runs_json=$(fetch_runs_since "$window_start")
  count=$(echo "$runs_json" | jq 'length')
  printf 'Found %d runs since %s.\n' "$count" "$window_start" >&2

  local body
  body=$(build_table "$runs_json" "$window_start" "$last_id" "$prev_ids")
  post_or_update "$body" "$window_start"
  printf 'Done.\n' >&2
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi