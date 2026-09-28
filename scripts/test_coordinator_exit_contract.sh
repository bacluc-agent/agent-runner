#!/usr/bin/env bash
set -Eeuo pipefail

coordinator_exit() {
  local coordinator_status=$1
  local coordinator_tee_status=$2
  if ((coordinator_status != 0)); then
    return "$coordinator_status"
  fi
  return 0
}

coordinator_exit 0 1
[[ $? -eq 0 ]]

if coordinator_exit 124 0; then
  exit 1
else
  [[ $? -eq 124 ]]
fi

if coordinator_exit 7 1; then
  exit 1
else
  [[ $? -eq 7 ]]
fi
