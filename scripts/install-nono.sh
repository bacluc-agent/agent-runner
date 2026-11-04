#!/usr/bin/env bash
set -Eeuo pipefail

# renovate: datasource=github-releases depName=nolabs-ai/nono
NONO_VERSION=0.80.0
NONO_INSTALL_DIR="$RUNNER_TEMP/nono/bin"
export NONO_INSTALL_DIR

curl -fsSL https://nono.sh/install.sh | NONO_VERSION="v$NONO_VERSION" NONO_INSTALL_DIR="$NONO_INSTALL_DIR" sh
nono="$NONO_INSTALL_DIR/nono"
"$nono" --version
mkdir -p "$HOME/.local/share/opencode/log"
mkdir -p "$HOME/.config/gh"
mkdir -p "${TMPDIR:-/tmp}/opencode-db"

printf '%s\n' "$NONO_INSTALL_DIR" >> "$GITHUB_PATH"
printf 'NONO_PROFILE=%s\n' "$GITHUB_ACTION_PATH/nono-profile.json" >> "$GITHUB_ENV"
