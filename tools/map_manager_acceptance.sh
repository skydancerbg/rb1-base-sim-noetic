#!/usr/bin/env bash
# Acceptance test for the map manager (plan step 2.1; referenced by W/tests/backend/test_mapping.py).
#
# Runs ON the sim VM against http://127.0.0.1:8090. It performs a REAL mapping session: start, rotate the
# robot in place for 15 s, stop. A session overwrites the facility map (D-21), so the four map files are
# copied to $BACKUP_DIR first and put back by an EXIT trap, even when an assertion fails or the script is
# interrupted; the trap then re-runs the localisation restore against the original map, seeded with the
# pose the robot had when the script began.
#
# Assertions (PASS/FAIL per line, non-zero exit on any FAIL):
#   a  start answers 200 within 30 s; stop answers 200 within 60 s
#   b  no move_base goal is ACTIVE (status 1) after the start
#   c  after the stop, a /robot/amcl_pose NEWER than a forced update arrives within 15 s
#   d  after the stop exactly one localiser publishes the map->odom transform: AMCL is up and gmapping is gone
#   e  (--strict) the AMCL pose after the stop is within 0.2 m of the pose read just before the stop
#
# Known failures on the code as of 2.1, listed in XFAIL_CHECKS so they print XFAIL and do not fail the
# run; step 2.2 fixes them and removes the entries:
#   c  -- the manager reports "restored" when the map server is back, not when AMCL has produced a pose;
#         AMCL is silent until it is moved or asked and was not seeded (D-21, F-009).
#   e  -- the manager restores AMCL at (0,0,0), not at the SLAM pose (F-009).
#
# Usage:  tools/map_manager_acceptance.sh [--strict]
set -u

STRICT=0
for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=1 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

XFAIL_CHECKS="${XFAIL_CHECKS-c e}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-${HOME}/catkin_ws}"
MANAGER="${MAP_MANAGER_URL:-http://127.0.0.1:8090}"
BACKUP_DIR="${BACKUP_DIR:-${HOME}/backups/2.1/map}"
TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set +u
source /opt/ros/noetic/setup.bash
source "${WORKSPACE_ROOT}/devel/setup.bash"
set -u
export LC_ALL=C   # decimal points: curl and awk must agree on "6.9", not "6,9"
export ROS_MASTER_URI="${ROS_MASTER_URI:-http://10.25.25.123:11311}"
export ROS_IP="${ROS_IP:-10.25.25.123}"

MAP_DIR="$(rospack find rb1_base_localization)/maps/neo_workshop"
MAP_FILES=(neo_workshop.yaml neo_workshop.pgm neo_workshop.previous.yaml neo_workshop.previous.pgm)
FAILS=0
SEED=""

say() { printf '[acceptance] %s\n' "$*"; }

check() {  # check <id> <description> <true|false>
  local id="$1" what="$2" ok="$3"
  if [[ "$ok" == true ]]; then
    if [[ " $XFAIL_CHECKS " == *" $id "* ]]; then say "XPASS ($id) $what  -- remove $id from XFAIL_CHECKS"; else say "PASS  ($id) $what"; fi
  elif [[ " $XFAIL_CHECKS " == *" $id "* ]]; then
    say "XFAIL ($id) $what  -- expected until the step that fixes it"
  else
    say "FAIL  ($id) $what"; FAILS=$((FAILS + 1))
  fi
}

json_field() { python3 -c "import json,sys; print(json.loads(sys.argv[1])[sys.argv[2]])" "$1" "$2" 2>/dev/null; }
service_present() { rosservice list 2>/dev/null | grep -qx "$1"; }
wait_service() {  # wait_service <name> <present|absent> <seconds>
  local end=$((SECONDS + $3))
  while (( SECONDS < end )); do
    if [[ "$2" == present ]] && service_present "$1"; then return 0; fi
    if [[ "$2" == absent ]] && ! service_present "$1"; then return 0; fi
    sleep 1
  done
  return 1
}
manager_active() { curl -s -m 5 "${MANAGER}/session" | python3 -c "import json,sys; print(json.load(sys.stdin)['state']['active'])" 2>/dev/null; }

relaunch_localisation() {
  # Replace whatever localisation is running with a fresh one against the map files now on disk.
  pkill -INT -f "roslaunch rb1_base_gazebo localization_restore" 2>/dev/null
  sleep 3
  rosnode kill /robot/amcl /robot/robot_map_server >/dev/null 2>&1
  sleep 3
  echo y | rosnode cleanup >/dev/null 2>&1
  wait_service /robot/static_map absent 20 || say "warning: the map server is still registered"
  local args=()
  if [[ -n "$SEED" ]]; then
    args=("x_init_pose:=$(json_field "$SEED" x)" "y_init_pose:=$(json_field "$SEED" y)" "init_yaw:=$(json_field "$SEED" yaw)")
  fi
  (cd "$WORKSPACE_ROOT" && setsid nohup roslaunch rb1_base_gazebo localization_restore.launch "${args[@]}" \
      > "${HOME}/acceptance_restore.log" 2>&1 < /dev/null &)
  wait_service /robot/static_map present 45 || say "warning: the map server did not come back"
  sleep 5
  rosservice call /robot/request_nomotion_update >/dev/null 2>&1
}

cleanup() {
  trap - EXIT
  say "cleanup: closing a session left open, putting the map back, restoring localisation"
  if [[ "$(manager_active)" == True ]]; then curl -s -m 90 -X POST "${MANAGER}/session/stop" >/dev/null; fi
  rostopic pub -1 /robot/web_teleop/cmd_vel geometry_msgs/Twist '{}' >/dev/null 2>&1
  for f in "${MAP_FILES[@]}"; do
    if [[ -f "${BACKUP_DIR}/${f}" ]]; then cp -p "${BACKUP_DIR}/${f}" "${MAP_DIR}/${f}"; fi
  done
  relaunch_localisation
  if (cd "${WORKSPACE_ROOT}/src" && git status --porcelain -- rb1_base_common/rb1_base_localization/maps | grep -q .); then
    say "WARNING: the tracked map differs from the repository after the restore"
  else
    say "map files unchanged against the repository"
  fi
}

# --- preparation ----------------------------------------------------------------------------------
mkdir -p "$BACKUP_DIR"
for f in "${MAP_FILES[@]}"; do
  if [[ -f "${MAP_DIR}/${f}" ]]; then cp -p "${MAP_DIR}/${f}" "${BACKUP_DIR}/${f}"; fi
done
say "map files backed up to ${BACKUP_DIR}"
trap cleanup EXIT

[[ "$(manager_active)" == False ]] || { say "a mapping session is already active; refusing to start"; exit 2; }
SEED="$(python3 "${TOOLS}/map_pose_now.py" 2>/dev/null || true)"
say "pose before: ${SEED:-unavailable}"

# --- a: start -------------------------------------------------------------------------------------
read -r code secs < <(curl -s -m 40 -o /tmp/acc_start.json -w '%{http_code} %{time_total}\n' -X POST "${MANAGER}/session/start")
say "start -> ${code} in ${secs}s"
check a "start answered 200 within 30 s" "$([[ "$code" == 200 ]] && awk -v s="$secs" 'BEGIN{exit !(s<30)}' && echo true || echo false)"

# --- b: no ACTIVE goal ----------------------------------------------------------------------------
status="$(timeout -s INT 5 rostopic echo -n1 /robot/move_base/status 2>/dev/null)"
check b "no move_base goal is ACTIVE after the start" "$(grep -qE '^\s+status: 1$' <<<"$status" && echo false || echo true)"

# --- drive: rotate in place, angular only ---------------------------------------------------------
say "rotating in place for 15 s"
timeout -s INT 15 rostopic pub -r 10 /robot/web_teleop/cmd_vel geometry_msgs/Twist '{angular: {z: 0.3}}' >/dev/null 2>&1
rostopic pub -1 /robot/web_teleop/cmd_vel geometry_msgs/Twist '{}' >/dev/null 2>&1
sleep 2
BEFORE_STOP="$(python3 "${TOOLS}/map_pose_now.py" 2>/dev/null || true)"
say "pose just before the stop: ${BEFORE_STOP:-unavailable}"

# --- a: stop --------------------------------------------------------------------------------------
read -r code secs < <(curl -s -m 100 -o /tmp/acc_stop.json -w '%{http_code} %{time_total}\n' -X POST "${MANAGER}/session/stop")
say "stop -> ${code} in ${secs}s"
check a "stop answered 200 within 60 s" "$([[ "$code" == 200 ]] && awk -v s="$secs" 'BEGIN{exit !(s<60)}' && echo true || echo false)"

# --- c: a real pose after the stop ----------------------------------------------------------------
AFTER="$(python3 "${TOOLS}/map_pose_now.py" --amcl-after --timeout 15 2>/dev/null || true)"
say "pose from AMCL after a forced update: ${AFTER:-none}"
check c "a fresh /robot/amcl_pose (newer than a forced update) arrived within 15 s" "$([[ -n "$AFTER" ]] && echo true || echo false)"
if [[ -z "$AFTER" ]]; then
  # Diagnostic only: is it a delay or a silence? Ask again after the localiser has had time to settle.
  sleep 20
  LATE="$(python3 "${TOOLS}/map_pose_now.py" --amcl-after --timeout 15 2>/dev/null || true)"
  say "diagnostic, 20 s later: ${LATE:-still none}"
fi

# --- d: exactly one localiser ---------------------------------------------------------------------
nodes="$(rosnode list 2>/dev/null)"
amcl_up=false; gmapping_gone=false
grep -qx /robot/amcl <<<"$nodes" && amcl_up=true
grep -qx /robot/slam_gmapping <<<"$nodes" || gmapping_gone=true
check d "AMCL is up and gmapping is gone (one map->odom publisher)" "$([[ $amcl_up == true && $gmapping_gone == true ]] && echo true || echo false)"

# --- e: where AMCL put the robot ------------------------------------------------------------------
if (( STRICT )); then
  verdict=false
  if [[ -n "$AFTER" && -n "$BEFORE_STOP" ]]; then
    dist="$(python3 - "$AFTER" "$BEFORE_STOP" <<'PY'
import json, math, sys
a, b = json.loads(sys.argv[1]), json.loads(sys.argv[2])
print(math.hypot(a["x"] - b["x"], a["y"] - b["y"]))
PY
)"
    say "AMCL is ${dist} m from the pose read just before the stop"
    awk -v d="$dist" 'BEGIN{exit !(d<0.2)}' && verdict=true
  fi
  check e "AMCL after the stop is within 0.2 m of the SLAM pose before it" "$verdict"
fi

say "$([[ $FAILS -eq 0 ]] && echo 'RESULT: all assertions passed' || echo "RESULT: ${FAILS} assertion(s) failed")"
exit $(( FAILS > 0 ))
