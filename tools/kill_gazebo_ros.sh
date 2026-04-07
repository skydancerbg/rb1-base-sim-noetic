#!/usr/bin/env bash

set -euo pipefail

log() {
  printf '[kill_gazebo_ros] %s\n' "$*"
}

kill_pattern() {
  local label="$1"
  local pattern="$2"
  if pgrep -fa "${pattern}" >/dev/null 2>&1; then
    log "Stopping ${label}"
    pkill -f "${pattern}" || true
  else
    log "No ${label} processes found"
  fi
}

kill_pattern "gzserver" "gzserver"
kill_pattern "gzclient" "gzclient"
kill_pattern "rviz" "rviz"
kill_pattern "rosmaster" "rosmaster"
kill_pattern "rosout" "rosout"

log "Done"
