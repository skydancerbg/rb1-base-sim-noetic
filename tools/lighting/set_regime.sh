#!/usr/bin/env bash
# Switch the simulated world between the dissertation's three lighting regimes (plan step P5.6).
#
#   ssh sim ~/lighting/set_regime.sh <nominal|dimmed|side>
#   ssh sim ~/lighting/set_regime.sh status        # the regime last set, and when
#
#   nominal   the world file's own lighting: sun diffuse 0.8, ambient 0.4, sun direction -0.5 0.5 -1
#   dimmed    50 % of the nominal intensity (dissertation §4.2.2): sun diffuse 0.4, ambient 0.2,
#             same direction
#   side      "a directed source at an angle, creating glare and shadows" (§4.2.2): the sun and ambient
#             turned right down (diffuse 0.05, ambient 0.08) and one SPOT light placed to the left of
#             the inspection panel and in front of it, at the panel's height, aimed at the panel's
#             centre from the side, with a strong specular term (glare) and shadows switched on for
#             the scene and the lamp; every other regime switches scene shadows off again, as the
#             world file has them
#
# Aligned with the dissertation text on 09.11.2026 (D-50): dimmed was 0.2/0.1 (25 %), and the side
# lamp was a point light without shadows.
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
#: Aim: from the lamp to the panel centre (inspection ANCHOR -0.185, 0.524 at height 1.2).
SIDE_LAMP_DIR="x: 0.515 y: -0.896 z: 0"

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
  nominal) diffuse=0.8;  ambient=0.4;  dir="x: -0.5 y: 0.5 z: -1"; lamp=off; shadows=false ;;
  dimmed)  diffuse=0.4;  ambient=0.2;  dir="x: -0.5 y: 0.5 z: -1"; lamp=off; shadows=false ;;
  side)    diffuse=0.05; ambient=0.08; dir="x: -0.5 y: 0.5 z: -1"; lamp=on;  shadows=true ;;
  *) echo "unknown regime '$1' (nominal, dimmed, side)" >&2; exit 64 ;;
esac

gz topic -p /gazebo/default/scene -m "name: \"default\" ambient {r: ${ambient} g: ${ambient} b: ${ambient} a: 1} shadows: ${shadows}"
gz topic -p /gazebo/default/light/modify -m "name: \"sun\" diffuse {r: ${diffuse} g: ${diffuse} b: ${diffuse} a: 1} direction {${dir}}"

if [ "$lamp" = on ]; then
  if ! side_lamp_present; then
    gz topic -p /gazebo/default/factory/light -m "name: \"${SIDE_LAMP}\" type: SPOT pose {position {x: ${SIDE_LAMP_X} y: ${SIDE_LAMP_Y} z: ${SIDE_LAMP_Z}} orientation {x: 0 y: 0 z: 0 w: 1}} direction {${SIDE_LAMP_DIR}} diffuse {r: 1 g: 1 b: 1 a: 1} specular {r: 0.9 g: 0.9 b: 0.9 a: 1} attenuation_constant: 0.4 attenuation_linear: 0.25 attenuation_quadratic: 0.15 range: 8 spot_inner_angle: 0.35 spot_outer_angle: 0.7 spot_falloff: 1 cast_shadows: true"
    sleep 0.5
  fi
elif side_lamp_present; then
  rosservice call /gazebo/delete_light "{light_name: ${SIDE_LAMP}}" >/dev/null
fi

stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s %s\n' "$1" "$stamp" > "${HERE}/current_regime"
printf '%s regime=%s diffuse=%s ambient=%s side_lamp=%s shadows=%s\n' "$stamp" "$1" "$diffuse" "$ambient" "$lamp" "$shadows" >> "${HERE}/regime.log"
echo "regime=$1 at ${stamp}"
