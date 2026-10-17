#!/usr/bin/env bash
set -Eeuo pipefail
: "${NONO_PROFILE:?NONO_PROFILE is not set; run scripts/install-nono.sh first}"
nono run --profile "$NONO_PROFILE" --allow-cwd \
  --allow "$HOME/.local/share/opencode" \
  --allow "$HOME/.local/state/opencode" \
  --allow "$HOME/.npm" \
  --allow "${TMPDIR:-/tmp}/opencode-db" \
  --allow "$HOME/.config/opencode" \
  --read "${RUNNER_TEMP:?}/gh-cli-wrapper" \
  --read-file "${RUNNER_TEMP:?}"/git-credentials-*.config \
  -- opencode "$@" 2> >(tee -a "$RUNNER_TEMP/nono-proxy.log" >&2)
