#!/usr/bin/env bash
set -Eeuo pipefail
: "${NONO_PROFILE:?NONO_PROFILE is not set; run scripts/install-nono.sh first}"
exec nono run --profile "$NONO_PROFILE" --allow-cwd -- opencode "$@"
