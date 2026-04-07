#!/usr/bin/env bash

set -euo pipefail

WORKSPACE_ROOT="${HOME}/catkin_ws"

log() {
  printf '[save_neo_workshop_map] %s\n' "$*"
}

die() {
  printf '[save_neo_workshop_map] ERROR: %s\n' "$*" >&2
  exit 1
}

[[ -f "${WORKSPACE_ROOT}/devel/setup.bash" ]] || die "Missing ${WORKSPACE_ROOT}/devel/setup.bash. Build the workspace first."

source /opt/ros/noetic/setup.bash
source "${WORKSPACE_ROOT}/devel/setup.bash"

localization_root="$(rospack find rb1_base_localization)"
map_dir="${localization_root}/maps/neo_workshop"
final_prefix="${map_dir}/neo_workshop"
temp_prefix="${map_dir}/neo_workshop_tmp"
temp_yaml="${temp_prefix}.yaml"
temp_pgm="${temp_prefix}.pgm"
final_yaml="${final_prefix}.yaml"
final_pgm="${final_prefix}.pgm"

mkdir -p "${map_dir}"
rm -f "${temp_yaml}" "${temp_pgm}"

log "Saving /robot/map to temporary basename ${temp_prefix}"
rosrun map_server map_saver -f "${temp_prefix}" map:=/robot/map

[[ -s "${temp_yaml}" ]] || die "Temporary yaml was not created or is empty: ${temp_yaml}"
[[ -s "${temp_pgm}" ]] || die "Temporary pgm was not created or is empty: ${temp_pgm}"

mv -f "${temp_yaml}" "${final_yaml}"
mv -f "${temp_pgm}" "${final_pgm}"

log "Promoted saved map to:"
printf '%s\n' "${final_yaml}" "${final_pgm}"
