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

# Keep one previous generation. Saving replaces the facility map in place - that is what makes a
# finished SLAM session take effect - so without this, one accidental stop overwrites a map that
# may have taken an afternoon to drive. Not a history; just "where is the map from before".
if [[ -s "${final_yaml}" && -s "${final_pgm}" ]]; then
  cp -f "${final_yaml}" "${map_dir}/neo_workshop.previous.yaml"
  cp -f "${final_pgm}" "${map_dir}/neo_workshop.previous.pgm"
  sed -i "s|^image:.*|image: neo_workshop.previous.pgm|" "${map_dir}/neo_workshop.previous.yaml"
  log "Previous map kept as neo_workshop.previous.yaml/.pgm"
fi

log "Saving /robot/map to temporary basename ${temp_prefix}"
rosrun map_server map_saver -f "${temp_prefix}" map:=/robot/map

[[ -s "${temp_yaml}" ]] || die "Temporary yaml was not created or is empty: ${temp_yaml}"
[[ -s "${temp_pgm}" ]] || die "Temporary pgm was not created or is empty: ${temp_pgm}"

mv -f "${temp_yaml}" "${final_yaml}"
mv -f "${temp_pgm}" "${final_pgm}"

# map_saver writes the prefix it was given into the yaml, so after the rename above the yaml still
# points at neo_workshop_tmp.pgm and map_server refuses to start ("failed to open image file").
# Rewrite the image field to the plain basename - plain rather than absolute, so the map directory
# stays movable, which is how the map tracked in this repository was already written.
log "Pointing the yaml at $(basename "${final_pgm}") (rewrite the image field)"
sed -i "s|^image:.*|image: $(basename "${final_pgm}")|" "${final_yaml}"

grep -q "^image: $(basename "${final_pgm}")$" "${final_yaml}" \
  || die "The yaml still does not name ${final_pgm}; refusing to leave an unloadable map behind."

log "Promoted saved map to:"
printf '%s\n' "${final_yaml}" "${final_pgm}"
