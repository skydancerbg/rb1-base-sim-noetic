#!/usr/bin/env bash
# Switch the simulated world between the dissertation's three lighting regimes (plan step P5.6).
#
#   ssh sim ~/lighting/set_regime.sh <nominal|dimmed|side>
#   ssh sim ~/lighting/set_regime.sh status        # the regime last set, and when
#
#   nominal   the world file's own lighting: sun diffuse 0.8, ambient 0.4, sun direction -0.5 0.5 -1
#   dimmed    low light: sun diffuse 0.2, ambient 0.1 (same direction)
#   side      the sun and ambient turned right down (diffuse 0.05, ambient 0.08) and one point light
#             placed to the left of the inspection panel and in front of it, at the panel's height:
#             the panel face is lit at an oblique angle, bright on the left and falling off to the
#             right, as light from a side window or a lamp on the wall would
#
# Done with Gazebo transport messages to the running server (light/modify for the sun, scene for the
# ambient, factory/light for the side lamp), so nothing restarts and the world file is untouched. The
# values are absolute, so the same regime always gives the same lighting, and `nominal` restores the
# starting state exactly (the camera frame is identical to the one before any change, checked). Each
# change is logged with a UTC timestamp to ~/lighting/regime.log.
#
# The side lamp is positioned for the inspection panel of ~/inspection (robot parked at its spot);
# it is removed again by every other regime. Wait 2 s after a change before capturing evidence.
set -euo pipefail

HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
export DISPLAY="${DISPLAY:-:99}"
export ROS_MASTER_URI="${ROS_MASTER_URI:-http://10.25.25.123:11311}"
set +u
# shellcheck disable=SC1091
source /opt/ros/noetic/setup.bash
set -u

SIDE_LAMP=regime_side_lamp
#: Gazebo world coordinates: 0.5 m in front of the panel plane, 0.9 m to the viewer's left of its
#: centre, at the camera's height.
SIDE_LAMP_X=-0.7
SIDE_LAMP_Y=1.42
SIDE_LAMP_Z=1.2

if [ "$#" -ne 1 ]; then
  sed -n '2,7p' "$0" >&2
  exit 64
fi

if [ "$1" = "status" ]; then
  cat "${HERE}/current_regime" 2>/dev/null || echo "unknown (not set since the simulation started)"
  exit 0
fi

side_lamp_present() {
  rosservice call /gazebo/get_light_properties "{light_name: ${SIDE_LAMP}}" 2>/dev/null | grep -q "success: True"
}

case "$1" in
  nominal) diffuse=0.8;  ambient=0.4;  dir="x: -0.5 y: 0.5 z: -1"; lamp=off ;;
  dimmed)  diffuse=0.2;  ambient=0.1;  dir="x: -0.5 y: 0.5 z: -1"; lamp=off ;;
  side)    diffuse=0.05; ambient=0.08; dir="x: -0.5 y: 0.5 z: -1"; lamp=on ;;
  *) echo "unknown regime '$1' (nominal, dimmed, side)" >&2; exit 64 ;;
esac

gz topic -p /gazebo/default/scene -m "name: \"default\" ambient {r: ${ambient} g: ${ambient} b: ${ambient} a: 1}"
gz topic -p /gazebo/default/light/modify -m "name: \"sun\" diffuse {r: ${diffuse} g: ${diffuse} b: ${diffuse} a: 1} direction {${dir}}"

if [ "$lamp" = on ]; then
  if ! side_lamp_present; then
    gz topic -p /gazebo/default/factory/light -m "name: \"${SIDE_LAMP}\" type: POINT pose {position {x: ${SIDE_LAMP_X} y: ${SIDE_LAMP_Y} z: ${SIDE_LAMP_Z}} orientation {x: 0 y: 0 z: 0 w: 1}} diffuse {r: 1 g: 1 b: 1 a: 1} specular {r: 0.1 g: 0.1 b: 0.1 a: 1} attenuation_constant: 0.4 attenuation_linear: 0.25 attenuation_quadratic: 0.15 range: 8 cast_shadows: false"
    sleep 0.5
  fi
elif side_lamp_present; then
  rosservice call /gazebo/delete_light "{light_name: ${SIDE_LAMP}}" >/dev/null
fi

stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s %s\n' "$1" "$stamp" > "${HERE}/current_regime"
printf '%s regime=%s diffuse=%s ambient=%s side_lamp=%s\n' "$stamp" "$1" "$diffuse" "$ambient" "$lamp" >> "${HERE}/regime.log"
echo "regime=$1 at ${stamp}"
