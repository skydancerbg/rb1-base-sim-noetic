#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="${HOME}/catkin_ws/src"
RUNNER="${REPO_ROOT}/tools/run_neo_workshop.sh"
KILLER="${REPO_ROOT}/tools/kill_gazebo_ros.sh"
VERIFY="${REPO_ROOT}/tools/verify_neo_workshop.sh"

log() {
  printf '[neo_workshop_gui] %s\n' "$*"
}

die() {
  printf '[neo_workshop_gui] ERROR: %s\n' "$*" >&2
  exit 1
}

need_terminal() {
  command -v gnome-terminal >/dev/null 2>&1 || die "gnome-terminal is not installed or not in PATH"
}

need_file() {
  local path="$1"
  [[ -x "${path}" ]] || die "Required executable not found: ${path}"
}

open_terminal() {
  local title="$1"
  local command="$2"
  log "Opening terminal: ${title}"
  gnome-terminal --title="${title}" -- bash -lc "${command}; exec bash"
}

usage() {
  cat <<'EOF'
Usage: ./tools/neo_workshop_gui.sh <subcommand>

Subcommands:
  map    Open mapping, automap, and map-file verification terminals
  frontier  Open frontier-based mapping terminal
  nav    Open navigation and navigation verification terminals
  stop   Run kill_gazebo_ros.sh in the current terminal
  help   Show this help
EOF
}

need_terminal
need_file "${RUNNER}"
need_file "${KILLER}"
need_file "${VERIFY}"

subcommand="${1:-help}"

case "${subcommand}" in
  map)
    open_terminal \
      "neo_workshop mapping" \
      "cd ${REPO_ROOT} && ./tools/kill_gazebo_ros.sh && ./tools/run_neo_workshop.sh mapping"
    log "Waiting 5 seconds before starting automap"
    sleep 5
    open_terminal \
      "neo_workshop automap" \
      "cd ${REPO_ROOT} && ./tools/run_neo_workshop.sh automap"
    log "Waiting 2 seconds before checking saved map files"
    sleep 2
    open_terminal \
      "neo_workshop map-files" \
      "cd ${REPO_ROOT} && ./tools/verify_neo_workshop.sh map-files"
    ;;
  frontier)
    open_terminal \
      "neo_workshop frontier mapping" \
      "cd ${REPO_ROOT} && ./tools/kill_gazebo_ros.sh && ./tools/run_neo_workshop.sh frontier-mapping"
    log "When frontier exploration finishes, save the map from another terminal with ./tools/run_neo_workshop.sh frontier-save"
    ;;
  nav)
    open_terminal \
      "neo_workshop navigation" \
      "cd ${REPO_ROOT} && ./tools/kill_gazebo_ros.sh && ./tools/run_neo_workshop.sh navigation"
    log "Waiting 5 seconds before starting navigation verification"
    sleep 5
    open_terminal \
      "neo_workshop nav-verify" \
      "cd ${REPO_ROOT} && ./tools/verify_neo_workshop.sh navigation"
    ;;
  stop)
    log "Stopping stale Gazebo and ROS GUI processes"
    cd "${REPO_ROOT}"
    ./tools/kill_gazebo_ros.sh
    ;;
  help)
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
