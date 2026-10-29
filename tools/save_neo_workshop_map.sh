#!/usr/bin/env bash

set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-${HOME}/catkin_ws}"

log() {
  printf '[save_neo_workshop_map] %s\n' "$*"
}

die() {
  printf '[save_neo_workshop_map] ERROR: %s\n' "$*" >&2
  exit 1
}

[[ -f "${WORKSPACE_ROOT}/devel/setup.bash" ]] || die "Missing ${WORKSPACE_ROOT}/devel/setup.bash. Build the workspace first."

# ROS setup scripts read variables that may be unset; under `set -u` that aborts this script at the
# `source` line, as it already did once (the map manager has the same `set +u` for the same reason).
set +u
source /opt/ros/noetic/setup.bash
source "${WORKSPACE_ROOT}/devel/setup.bash"
set -u

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

# map_saver writes the prefix it was given into the yaml, so the temporary yaml names
# neo_workshop_tmp.pgm and map_server would refuse it ("failed to open image file"). Fix the image field
# in the TEMPORARY yaml and check it BEFORE anything is promoted, so a failure here leaves the facility
# map exactly as it was. The field is the plain basename, not an absolute path, so the map directory
# stays movable, which is how the map tracked in this repository was already written.
sed -i "s|^image:.*|image: $(basename "${final_pgm}")|" "${temp_yaml}"
grep -q "^image: $(basename "${final_pgm}")$" "${temp_yaml}"   || die "The temporary yaml does not name $(basename "${final_pgm}"); nothing was promoted."

# Promote the image first and the yaml second: a yaml that names a pgm is only ever visible once that
# pgm is in place, so a reader (or an interrupted run) never finds a yaml pointing at a missing image.
mv -f "${temp_pgm}" "${final_pgm}"
mv -f "${temp_yaml}" "${final_yaml}"

log "Promoted saved map to:"
printf '%s\n' "${final_yaml}" "${final_pgm}"
