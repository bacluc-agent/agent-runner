#!/usr/bin/env bash
set -Eeuo pipefail
: "${NONO_PROFILE:?NONO_PROFILE is not set; run scripts/install-nono.sh first}"
exec nono run --profile "$NONO_PROFILE" --allow-cwd \
  --allow "$HOME/.local/share/opencode" \
  --allow "$HOME/.local/state/opencode" \
  --allow "${TMPDIR:-/tmp}/opencode-db" \
  --read "$HOME/.config" \
  --read "${RUNNER_TEMP:?}" \
  -- opencode "$@"
