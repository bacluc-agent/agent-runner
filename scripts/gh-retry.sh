#!/usr/bin/env bash
# gh-retry.sh — rate-limit-aware `gh` wrapper for the workflow steps.
#
#   source scripts/gh-retry.sh
#   gh_preflight "<what a stand-down skips>" core [search] [graphql]   # free probe; may exit 0
#   gh_retry <gh-args...>     # same args, same exit status as `gh <gh-args...>`
#
# gh_retry passes stdout through untouched, always replays gh's captured stderr
# and emits one `GitHub API quota after gh ...` line per attempt, so the
# remaining quota is visible after every call (the free /rate_limit endpoint
# answers even while other calls return 403). On a rate-limit response it backs
# off — sleep-until-reset when a bucket is empty and the reset is near,
# exponential backoff otherwise — and gives up loudly. All diagnostics go to
# stderr so the wrapped command's stdout stays clean for --jq pipelines and $().

# 4 attempts = 1 + 3 retries (the issue asks for 3-5 attempts).
GH_RETRY_MAX_ATTEMPTS="${GH_RETRY_MAX_ATTEMPTS:-4}"
# Longest wait a step sits through; a reset further out cannot be waited for in
# a 22-120 min step, so the call fails loudly instead.
GH_RETRY_MAX_SLEEP="${GH_RETRY_MAX_SLEEP:-300}"
# Exponential backoff base: 10s, 20s, 40s (+0-4s jitter, capped at 60s).
GH_RETRY_BACKOFF_BASE="${GH_RETRY_BACKOFF_BASE:-10}"

# _gh_rl -> "core_r core_l core_x search_r search_l search_x gql_r gql_l gql_x"
_gh_rl() {
  gh api rate_limit --jq \
    '[.resources.core.remaining,.resources.core.limit,.resources.core.reset,.resources.search.remaining,.resources.search.limit,.resources.search.reset,.resources.graphql.remaining,.resources.graphql.limit,.resources.graphql.reset] | @tsv' \
    2> /dev/null || printf 'unknown\tunknown\tunknown\tunknown\tunknown\tunknown\tunknown\tunknown\tunknown'
}

# _gh_ts <epoch> -> "23:00:00Z" (UTC) or "?" when unknown
_gh_ts() {
  if [[ "$1" =~ ^[0-9]+$ ]]; then
    date -u -d "@$1" +%H:%M:%SZ
  else
    printf '?'
  fi
}

# _gh_in <epoch> -> seconds until that epoch, or -1 when unknown
_gh_in() {
  if [[ "$1" =~ ^[0-9]+$ ]]; then
    printf '%s' "$(($1 - $(date +%s)))"
  else
    printf '%s' -1
  fi
}

# gh_retry <gh-args...> — run gh, back off on rate limits, propagate the status.
gh_retry() {
  local attempt=1 rc=0 err f delay ex='' ex_x=-1 ins=-1 until_note=''
  local core_r core_l core_x search_r search_l search_x gql_r gql_l gql_x
  err="$(mktemp)"
  while :; do
    rc=0
    gh "$@" 2> "$err" || rc=$?
    if [[ -s "$err" ]]; then
      cat "$err" >&2
    fi
    f="$(_gh_rl)"
    read -r core_r core_l core_x search_r search_l search_x gql_r gql_l gql_x <<< "$f"
    printf 'GitHub API quota after gh %s: core=%s/%s (reset %s) search=%s/%s (reset %s) graphql=%s/%s (reset %s)\n' \
      "$*" "$core_r" "$core_l" "$(_gh_ts "$core_x")" \
      "$search_r" "$search_l" "$(_gh_ts "$search_x")" \
      "$gql_r" "$gql_l" "$(_gh_ts "$gql_x")" >&2
    if ((rc == 0)); then
      rm -f "$err"
      return 0
    fi
    if ! grep -Eiq 'rate limit|HTTP 429|abuse detection' "$err"; then
      rm -f "$err"
      return "$rc"
    fi
    if [[ "$core_r" == 0 ]]; then
      ex='core'
      ex_x="$core_x"
      ins="$(_gh_in "$core_x")"
    elif [[ "$search_r" == 0 ]]; then
      ex='search'
      ex_x="$search_x"
      ins="$(_gh_in "$search_x")"
    elif [[ "$gql_r" == 0 ]]; then
      ex='graphql'
      ex_x="$gql_x"
      ins="$(_gh_in "$gql_x")"
    fi
    if [[ -n "$ex" ]] && ((ins < 0 || ins > GH_RETRY_MAX_SLEEP)); then
      printf '::error::GitHub API rate limit: gh %s failed; %s remaining=0, resets at %s (%ss away > %ss); not retrying — the calling step'"'"'s guard decides what to skip\n' \
        "$*" "$ex" "$(_gh_ts "$ex_x")" "$ins" "$GH_RETRY_MAX_SLEEP" >&2
      rm -f "$err"
      return "$rc"
    fi
    if ((attempt >= GH_RETRY_MAX_ATTEMPTS)); then
      printf '::error::GitHub API rate limit: giving up on gh %s after %d/%d attempts (core=%s/%s reset %s, search=%s/%s reset %s, graphql=%s/%s reset %s); the calling step'"'"'s guard decides what to skip\n' \
        "$*" "$attempt" "$GH_RETRY_MAX_ATTEMPTS" \
        "$core_r" "$core_l" "$(_gh_ts "$core_x")" \
        "$search_r" "$search_l" "$(_gh_ts "$search_x")" \
        "$gql_r" "$gql_l" "$(_gh_ts "$gql_x")" >&2
      rm -f "$err"
      return "$rc"
    fi
    if [[ -n "$ex" ]]; then
      delay=$((ins + RANDOM % 5 + 1))
      until_note=" until the ${ex} reset"
    else
      delay=$((GH_RETRY_BACKOFF_BASE * 2 ** (attempt - 1) + RANDOM % 5))
      if ((delay > 60)); then
        delay=60
      fi
      until_note=''
    fi
    printf '::warning::GitHub API rate limit on gh %s (attempt %d/%d): sleeping %ss%s\n' \
      "$*" "$attempt" "$GH_RETRY_MAX_ATTEMPTS" "$delay" "$until_note" >&2
    sleep "$delay"
    attempt=$((attempt + 1))
  done
}

# gh_preflight <what-a-stand-down-skips> <bucket>... — free quota probe; call it
# bare at step top level. Prints the quota (all three buckets), then stands down
# loudly (::error:: + exit 0) when one of the REQUESTED buckets is empty and its
# reset is further away than GH_RETRY_MAX_SLEEP; a nearer reset is waited out by
# the first gh_retry, so the step proceeds.
gh_preflight() {
  local what="$1" f spec name rem x ins
  local core_r core_l core_x search_r search_l search_x gql_r gql_l gql_x
  shift
  f="$(_gh_rl)"
  read -r core_r core_l core_x search_r search_l search_x gql_r gql_l gql_x <<< "$f"
  printf 'GitHub API quota: core=%s/%s (reset %s) search=%s/%s (reset %s) graphql=%s/%s (reset %s)\n' \
    "$core_r" "$core_l" "$(_gh_ts "$core_x")" \
    "$search_r" "$search_l" "$(_gh_ts "$search_x")" \
    "$gql_r" "$gql_l" "$(_gh_ts "$gql_x")" >&2
  if [[ "$core_r" == unknown ]]; then
    printf '::warning::GitHub API quota unknown (rate_limit probe failed); continuing and relying on per-call retries\n' >&2
    return 0
  fi
  for spec in "core $core_r $core_x" "search $search_r $search_x" "graphql $gql_r $gql_x"; do
    read -r name rem x <<< "$spec"
    case " $* " in
      *" $name "*) ;;
      *) continue ;;
    esac
    if [[ "$rem" == 0 ]]; then
      ins="$(_gh_in "$x")"
      if ((ins < 0)); then
        continue
      fi
      if ((ins > GH_RETRY_MAX_SLEEP)); then
        printf '::error::GitHub API %s quota exhausted (remaining=0, resets at %s in %ss > %ss); standing down: skipping %s this run\n' \
          "$name" "$(_gh_ts "$x")" "$ins" "$GH_RETRY_MAX_SLEEP" "$what" >&2
        exit 0
      fi
      printf 'GitHub API %s quota empty but resets in %ss — waiting it out on the first rate-limited call\n' "$name" "$ins" >&2
    fi
  done
}

printf 'gh-retry.sh sourced: max attempts=%s, backoff base=%ss (10/20/40 + jitter, cap 60s), sleep-until-reset cap=%ss\n' \
  "$GH_RETRY_MAX_ATTEMPTS" "$GH_RETRY_BACKOFF_BASE" "$GH_RETRY_MAX_SLEEP" >&2
