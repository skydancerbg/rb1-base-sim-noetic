#!/usr/bin/env bash

set -euo pipefail

WORKSPACE_ROOT="${HOME}/catkin_ws"
MAP_YAML="${WORKSPACE_ROOT}/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.yaml"
MAP_PGM="${WORKSPACE_ROOT}/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.pgm"
SAVE_MAP_SCRIPT="${WORKSPACE_ROOT}/src/tools/save_neo_workshop_map.sh"

log() {
  printf '[neo_workshop] %s\n' "$*"
}

die() {
  printf '[neo_workshop] ERROR: %s\n' "$*" >&2
  exit 1
}

need_devel() {
  [[ -f "${WORKSPACE_ROOT}/devel/setup.bash" ]] || die "Missing ${WORKSPACE_ROOT}/devel/setup.bash. Run '$0 build' first."
}

need_ros_pkg() {
  local pkg="$1"
  local install_hint="$2"
  bash -lc "source /opt/ros/noetic/setup.bash && source ${WORKSPACE_ROOT}/devel/setup.bash && rospack find ${pkg}" >/dev/null 2>&1 \
    || die "Missing ROS package '${pkg}'. ${install_hint}"
}

# Gazebo camera sensors need a rendering context. This VM is headless, so unless a
# display exists OGRE is never initialised, every camera sensor fails to be created
# ("Unable to create CameraSensor. Rendering is disabled.") and no image topic is ever
# published -- silently, because navigation and the laser keep working.
# See robco-control-center/docs/inspection_camera_spec.md (plan step P0.6).
XVFB_DISPLAY="${XVFB_DISPLAY:-:99}"

display_up() {
  local d="${1#:}"
  d="${d%%.*}"
  [[ -S "/tmp/.X11-unix/X${d}" ]]
}

ensure_display() {
  if [[ -n "${DISPLAY:-}" ]] && display_up "${DISPLAY}"; then
    log "Using existing display ${DISPLAY}"
    return
  fi
  if display_up "${XVFB_DISPLAY}"; then
    export DISPLAY="${XVFB_DISPLAY}"
    ROBCO_VIRTUAL_DISPLAY=1
    log "Using virtual framebuffer ${DISPLAY} (xvfb.service)"
    return
  fi
  command -v Xvfb >/dev/null 2>&1     || die "No display available and Xvfb is not installed. Install it with: sudo apt install xvfb"
  log "No display found; starting Xvfb on ${XVFB_DISPLAY}"
  Xvfb "${XVFB_DISPLAY}" -screen 0 1280x1024x24 +extension GLX +extension RENDER -noreset     >"/tmp/xvfb${XVFB_DISPLAY}.log" 2>&1 &
  sleep 3
  display_up "${XVFB_DISPLAY}" || die "Failed to start Xvfb on ${XVFB_DISPLAY}"
  export DISPLAY="${XVFB_DISPLAY}"
  ROBCO_VIRTUAL_DISPLAY=1
  log "Started Xvfb on ${DISPLAY}"
}

# On a virtual framebuffer nobody can see RViz, and it costs CPU that the software
# renderer needs for the camera sensors, so default it off there. Override with
# LAUNCH_RVIZ=true|false.
rviz_arg() {
  # stdout of this function is consumed by command substitution, so keep the log off it
  ensure_display >&2
  local want="${LAUNCH_RVIZ:-auto}"
  if [[ "${want}" == "auto" ]]; then
    if [[ "${ROBCO_VIRTUAL_DISPLAY:-0}" == "1" ]]; then want="false"; else want="true"; fi
  fi
  printf launch_rviz:=%s "${want}"
}

run_ros_cmd() {
  local cmd="$1"
  ensure_display
  DISPLAY="${DISPLAY}" bash -lc "source /opt/ros/noetic/setup.bash && source ${WORKSPACE_ROOT}/devel/setup.bash && ${cmd}"
}

subcommand="${1:-}"

case "${subcommand}" in
  build)
    log "Building workspace with catkin_make from ${WORKSPACE_ROOT}"
    bash -lc "cd ${WORKSPACE_ROOT} && source /opt/ros/noetic/setup.bash && catkin_make"
    log "Build completed"
    ;;
  mapping)
    need_devel
    log "Launching neo_workshop mapping"
    run_ros_cmd "cd ${WORKSPACE_ROOT} && roslaunch rb1_base_gazebo rb1_neo_workshop_mapping.launch $(rviz_arg)"
    ;;
  frontier-mapping)
    need_devel
    need_ros_pkg "explore_lite" "Install it with: sudo apt update && sudo apt install ros-noetic-explore-lite"
    log "Launching neo_workshop frontier exploration mapping"
    run_ros_cmd "cd ${WORKSPACE_ROOT} && roslaunch rb1_base_gazebo rb1_neo_workshop_frontier_mapping.launch $(rviz_arg)"
    ;;
  automap)
    need_devel
    log "Running neo_workshop auto-mapping script with managed stop after a successful save"
    run_ros_cmd "export NEO_WORKSHOP_STOP_AFTER_SAVE=1 && rosrun rb1_base_gazebo neo_workshop_auto_map.py"
    ;;
  frontier-save)
    need_devel
    [[ -x "${SAVE_MAP_SCRIPT}" ]] || die "Missing executable map-save helper: ${SAVE_MAP_SCRIPT}"
    log "Saving the current frontier-mapping result into the active neo_workshop map files"
    bash -lc "cd ${WORKSPACE_ROOT}/src && ./tools/save_neo_workshop_map.sh"
    ;;
  navigation)
    need_devel
    [[ -f "${MAP_YAML}" ]] || die "Missing map yaml: ${MAP_YAML}"
    [[ -f "${MAP_PGM}" ]] || die "Missing map pgm: ${MAP_PGM}"
    log "Launching neo_workshop navigation with saved map"
    run_ros_cmd "cd ${WORKSPACE_ROOT} && roslaunch rb1_base_gazebo rb1_neo_workshop_navigation.launch $(rviz_arg)"
    ;;
  demo)
    need_devel
    log "Launching original demo navigation"
    run_ros_cmd "cd ${WORKSPACE_ROOT} && roslaunch rb1_base_gazebo rb1navindemoworl.launch"
    ;;
  check-map)
    log "Checking saved neo_workshop map files"
    [[ -f "${MAP_YAML}" ]] || die "Missing ${MAP_YAML}"
    [[ -f "${MAP_PGM}" ]] || die "Missing ${MAP_PGM}"
    ls -lh "${MAP_YAML}" "${MAP_PGM}"
    log "Map files are present"
    ;;
  *)
    cat >&2 <<'EOF'
Usage: tools/run_neo_workshop.sh <subcommand>

Subcommands:
  build       Build the catkin workspace with catkin_make
  mapping     Launch rb1_neo_workshop_mapping.launch
  frontier-mapping  Launch rb1_neo_workshop_frontier_mapping.launch
  automap     Run neo_workshop_auto_map.py
  frontier-save  Save /robot/map into neo_workshop.yaml and neo_workshop.pgm
  navigation  Launch rb1_neo_workshop_navigation.launch
  demo        Launch rb1navindemoworl.launch
  check-map   Check neo_workshop.yaml and neo_workshop.pgm
EOF
    exit 1
    ;;
esac
