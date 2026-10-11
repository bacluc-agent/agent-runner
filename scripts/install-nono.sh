#!/usr/bin/env bash
set -Eeuo pipefail

# renovate: datasource=github-releases depName=nolabs-ai/nono
NONO_VERSION=0.79.0
NONO_INSTALLER_SHA256=09eef94110d34387ddc72a9fec57654de900a516e69321aa729923a96ce47c44
NONO_INSTALL_DIR="$RUNNER_TEMP/nono/bin"
NONO_INSTALLER="$RUNNER_TEMP/nono-install.sh"
export NONO_INSTALL_DIR

curl -fsSL https://nono.sh/install.sh -o "$NONO_INSTALLER"
printf '%s  %s\n' "$NONO_INSTALLER_SHA256" "$NONO_INSTALLER" | sha256sum --check --status
NONO_VERSION="v$NONO_VERSION" NONO_INSTALL_DIR="$NONO_INSTALL_DIR" sh "$NONO_INSTALLER"
rm -f "$NONO_INSTALLER"
nono="$NONO_INSTALL_DIR/nono"
"$nono" --version
mkdir -p "$HOME/.local/share/opencode/log"
mkdir -p "${TMPDIR:-/tmp}/opencode-db"

python3 - "$GITHUB_ACTION_PATH/nono-profile.json" "$RUNNER_TEMP/agent-runner-nono-profile.json" "$RUNNER_TEMP" << 'PY'
import json
import os
import subprocess
import sys

source, destination, runner_temp = sys.argv[1:]
with open(source, encoding="utf-8") as profile_file:
    profile = json.load(profile_file)

config = subprocess.run(
    ["git", "config", "--local", "--null", "--get-regexp", r"^includeIf\..*\.path$"],
    check=False,
    capture_output=True,
    text=True,
)
for entry in config.stdout.split("\0"):
    if "\n" not in entry:
        continue
    _, path = entry.split("\n", 1)
    if (
        os.path.dirname(os.path.realpath(path)) == os.path.realpath(runner_temp)
        and os.path.basename(path).startswith("git-credentials-")
        and path.endswith(".config")
        and os.path.isfile(path)
    ):
        profile["filesystem"]["read_file"].append(path)

with open(destination, "w", encoding="utf-8") as profile_file:
    json.dump(profile, profile_file)
    profile_file.write("\n")
PY
chmod 644 "$RUNNER_TEMP/agent-runner-nono-profile.json"
printf '%s\n' "$NONO_INSTALL_DIR" >> "$GITHUB_PATH"
printf 'NONO_PROFILE=%s\n' "$RUNNER_TEMP/agent-runner-nono-profile.json" >> "$GITHUB_ENV"
