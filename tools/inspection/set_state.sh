#!/usr/bin/env bash
# Put an inspection object into one of its states (plan step P5.6).
#
#   ssh sim ~/inspection/set_state.sh <lamp|dial|display> <norm|anomaly>
#   ssh sim ~/inspection/set_state.sh all <norm|anomaly>
#   ssh sim ~/inspection/set_state.sh status        # read the panel back from the world
#   ssh sim ~/inspection/set_state.sh ensure        # spawn the panel if the world lacks it
#   ssh sim ~/inspection/set_state.sh park          # robot to the inspection spot, zero velocity
#   ssh sim ~/inspection/set_state.sh remove
#
# Same argument, same world state: a state is an absolute pose, never a toggle. Each change is logged
# with a timestamp to ~/inspection/state.log. The panel is spawned into the running simulation on
# first use (and after a simulation restart, which forgets it); nothing is added to the world file.
set -euo pipefail

HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
export ROS_MASTER_URI="${ROS_MASTER_URI:-http://10.25.25.123:11311}"
# ROS's setup script reads variables it has not set; it is not written for `set -u`.
set +u
# shellcheck disable=SC1091
source /opt/ros/noetic/setup.bash
set -u

if [ "$#" -lt 1 ]; then
  sed -n '2,12p' "$0" >&2
  exit 64
fi

case "$1" in
  all|status|ensure|remove|park) args=("$@") ;;
  *) args=(set "$@") ;;
esac

out="$(python3 "${HERE}/inspection_ctl.py" "${args[@]}")"
echo "$out"
case "${args[0]}" in
  set|all|ensure|remove|park)
    printf '%s %s -> %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${args[*]}" "$out" >> "${HERE}/state.log"
    ;;
esac
