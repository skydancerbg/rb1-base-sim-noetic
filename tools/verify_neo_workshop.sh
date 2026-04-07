#!/usr/bin/env bash

set -euo pipefail

WORKSPACE_ROOT="${HOME}/catkin_ws"
MAP_YAML="${WORKSPACE_ROOT}/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.yaml"
MAP_PGM="${WORKSPACE_ROOT}/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.pgm"

pass() {
  printf 'PASS: %s\n' "$*"
}

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

need_devel() {
  [[ -f "${WORKSPACE_ROOT}/devel/setup.bash" ]] || fail "Missing ${WORKSPACE_ROOT}/devel/setup.bash"
}

ros_eval() {
  local cmd="$1"
  bash -lc "source /opt/ros/noetic/setup.bash && source ${WORKSPACE_ROOT}/devel/setup.bash && ${cmd}"
}

check_env() {
  command -v bash >/dev/null 2>&1 || fail "bash not found"
  command -v roscore >/dev/null 2>&1 || fail "roscore not found"
  command -v catkin_make >/dev/null 2>&1 || fail "catkin_make not found"
  need_devel
  ros_eval "rospack find rb1_base_gazebo >/dev/null"
  pass "rb1_base_gazebo visible"
  ros_eval "rospack find rb1_base_localization >/dev/null"
  pass "rb1_base_localization visible"
  [[ -x "${WORKSPACE_ROOT}/src/rb1_base_sim/rb1_base_gazebo/scripts/neo_workshop_auto_map.py" ]] || fail "neo_workshop_auto_map.py is not executable"
  pass "neo_workshop_auto_map.py executable"
}

check_mapping_runtime() {
  need_devel
  ros_eval "rosnode list | grep -Fx /robot/slam_gmapping >/dev/null" || fail "/robot/slam_gmapping not running"
  pass "mapping node /robot/slam_gmapping running"
  ros_eval "rostopic list | grep -Fx /robot/front_laser/scan >/dev/null" || fail "/robot/front_laser/scan not present"
  pass "mapping topic /robot/front_laser/scan present"
  ros_eval "rostopic list | grep -Fx /robot/map >/dev/null" || fail "/robot/map not present"
  pass "mapping topic /robot/map present"
  ros_eval "rostopic list | grep -Fx /robot/robotnik_base_control/cmd_vel >/dev/null" || fail "/robot/robotnik_base_control/cmd_vel not present"
  pass "mapping topic /robot/robotnik_base_control/cmd_vel present"
}

check_map_files() {
  [[ -f "${MAP_YAML}" ]] || fail "Missing ${MAP_YAML}"
  pass "Found neo_workshop.yaml"
  [[ -f "${MAP_PGM}" ]] || fail "Missing ${MAP_PGM}"
  pass "Found neo_workshop.pgm"
}

check_navigation_runtime() {
  need_devel
  ros_eval "rosnode list | grep -Fx /robot/robot_map_server >/dev/null" || fail "/robot/robot_map_server not running"
  pass "navigation node /robot/robot_map_server running"
  ros_eval "rosnode list | grep -Fx /robot/amcl >/dev/null" || fail "/robot/amcl not running"
  pass "navigation node /robot/amcl running"
  ros_eval "rosnode list | grep -Fx /robot/move_base >/dev/null" || fail "/robot/move_base not running"
  pass "navigation node /robot/move_base running"
  ros_eval "rostopic list | grep -Fx /robot/map >/dev/null" || fail "/robot/map not present"
  pass "navigation topic /robot/map present"
  ros_eval "rostopic list | grep -Fx /robot/particlecloud >/dev/null" || fail "/robot/particlecloud not present"
  pass "navigation topic /robot/particlecloud present"
  ros_eval "rostopic list | grep -Fx /robot/move_base/cmd_vel >/dev/null" || fail "/robot/move_base/cmd_vel not present"
  pass "navigation topic /robot/move_base/cmd_vel present"
}

subcommand="${1:-}"

case "${subcommand}" in
  env)
    check_env
    ;;
  mapping)
    check_env
    check_mapping_runtime
    ;;
  map-files)
    check_map_files
    ;;
  navigation)
    check_env
    check_map_files
    check_navigation_runtime
    ;;
  all)
    check_env
    check_map_files
    check_mapping_runtime
    check_navigation_runtime
    ;;
  *)
    cat >&2 <<'EOF'
Usage: tools/verify_neo_workshop.sh <subcommand>

Subcommands:
  env         Verify workspace environment and package visibility
  mapping     Verify mapping runtime nodes/topics
  map-files   Verify saved neo_workshop map files
  navigation  Verify navigation runtime nodes/topics
  all         Run all verification checks
EOF
    exit 1
    ;;
esac
