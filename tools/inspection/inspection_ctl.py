#!/usr/bin/env python3
"""State-controllable inspection objects in the running Gazebo world (plan step P5.6).

One wall panel hangs in front of the robot's inspection spot, with one object per detection method:
an indicator lamp (green / red / off), a dial gauge (needle at a settable angle) and a digital display
(one of two readings). Each object has a "norm" and an "anomaly" state:

    set_state.sh <lamp|dial|display> <norm|anomaly>      (see also: status, ensure, remove)

Everything is a static Gazebo model without collision, spawned into the running simulation through
the gazebo_ros services, so nothing is added to the world file, nothing needs a restart, and nothing
below 1.0 m exists for the laser (scan plane 0.187 m) or the costmap to see. A state is an absolute
pose of a model, never a toggle, so the same argument always gives the same world.

How a state is made visible:
  lamp     three spheres share one place; the one for the state sits there, the others are parked
           under the floor (z = -3).
  dial     one needle model rolled about the panel normal; norm = 40, anomaly = 100 degrees clockwise
           from straight up as the camera sees it.
  display  two models with a different reading ("42.7" / "49.9") share one place; the other is parked.

The panel position is a measured constant (ANCHOR): the robot at test spot "a", 1.0 m from the board,
which puts the board at the camera's height (1.2 m). Change it with --anchor X,Y if the spot changes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import rospy
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import DeleteModel, GetModelState, SetModelState, SpawnModel
from geometry_msgs.msg import Point, Pose, Quaternion

HERE = os.path.dirname(os.path.realpath(__file__))
MATERIALS = os.path.join(HERE, "materials")

#: Where the robot is parked for inspection (Gazebo world frame: x, y, heading in degrees). The
#: simulated robot creeps a little while idle (odometry reads about 0.3 mm/s), so a long session
#: drifts off the panel; `park` puts it back exactly, with zero velocity.
HOME = (-1.185, 0.524, 0.0)
#: Gazebo world coordinates of the board's centre: 1.0 m straight ahead of HOME, at the camera's height.
ANCHOR = (HOME[0] + 1.0, HOME[1])
HEIGHT = 1.2
BOARD_DEPTH = 0.06
PARKED_Z = -3.0

#: Where each part sits, as (forward offset from the board centre toward the robot, sideways offset
#: with the viewer's left positive, height). Parts stand just in front of the board's face.
FACE = -(BOARD_DEPTH / 2.0)
LAYOUT = {
    "lamp": (FACE - 0.025, 0.30, HEIGHT + 0.10),
    "dial": (FACE - 0.006, 0.0, HEIGHT),
    "needle": (FACE - 0.014, 0.0, HEIGHT),
    "display": (FACE - 0.006, -0.30, HEIGHT),
}

NEEDLE_NORM, NEEDLE_ANOMALY = 40.0, 100.0

# --- the models ----------------------------------------------------------------------------------


def _sdf(name: str, visual: str) -> str:
    return f"""<?xml version="1.0"?>
<sdf version="1.6"><model name="{name}"><static>true</static><link name="link">{visual}</link></model></sdf>"""


def _material(ambient, diffuse, emissive=(0, 0, 0)) -> str:
    a, d, e = (" ".join(str(v) for v in c) + " 1" for c in (ambient, diffuse, emissive))
    return f"<material><ambient>{a}</ambient><diffuse>{d}</diffuse><emissive>{e}</emissive></material>"


def _script(name: str) -> str:
    return (
        "<material><script>"
        f"<uri>file://{MATERIALS}/scripts</uri><uri>file://{MATERIALS}/textures</uri><name>{name}</name>"
        "</script></material>"
    )


LAMP_COLOURS = {
    "green": ((0.0, 0.25, 0.05), (0.0, 0.9, 0.2), (0.0, 0.9, 0.2)),
    "red": ((0.3, 0.02, 0.02), (0.95, 0.05, 0.05), (0.95, 0.05, 0.05)),
    "off": ((0.12, 0.14, 0.12), (0.18, 0.2, 0.18), (0.0, 0.0, 0.0)),
}


def model_sdf(name: str) -> str:
    if name == "inspection_board":
        return _sdf(
            name,
            f'<visual name="v"><geometry><box><size>{BOARD_DEPTH} 0.9 0.45</size></box></geometry>'
            + _material((0.45, 0.45, 0.48), (0.55, 0.55, 0.58))
            + "</visual>",
        )
    if name.startswith("inspection_lamp_"):
        ambient, diffuse, emissive = LAMP_COLOURS[name.rsplit("_", 1)[1]]
        return _sdf(
            name,
            '<visual name="v"><geometry><sphere><radius>0.03</radius></sphere></geometry>'
            + _material(ambient, diffuse, emissive)
            + "</visual>",
        )
    if name == "inspection_dial":
        return _sdf(
            name,
            '<visual name="v"><pose>0 0 0 0 1.5708 0</pose><geometry><cylinder><radius>0.09</radius>'
            "<length>0.008</length></cylinder></geometry>"
            + _material((0.85, 0.85, 0.82), (0.92, 0.92, 0.9), (0.25, 0.25, 0.24))
            + "</visual>",
        )
    if name == "inspection_needle":
        return _sdf(
            name,
            '<visual name="v"><pose>0 0 0.0375 0 0 0</pose><geometry><box><size>0.003 0.006 0.075</size></box>'
            "</geometry>" + _material((0.04, 0.04, 0.05), (0.05, 0.05, 0.07)) + "</visual>",
        )
    if name in ("inspection_display_norm", "inspection_display_anomaly"):
        script = "Inspection/DisplayNorm" if name.endswith("norm") else "Inspection/DisplayAnomaly"
        return _sdf(
            name,
            '<visual name="v"><geometry><box><size>0.004 0.26 0.10</size></box></geometry>' + _script(script) + "</visual>",
        )
    raise KeyError(name)


MODELS = [
    "inspection_board",
    "inspection_lamp_green",
    "inspection_lamp_red",
    "inspection_lamp_off",
    "inspection_dial",
    "inspection_needle",
    "inspection_display_norm",
    "inspection_display_anomaly",
]


# --- poses ---------------------------------------------------------------------------------------


def roll(angle_degrees: float) -> Quaternion:
    """Rotation about the panel normal (world x): the needle's tip then points `angle` clockwise from
    straight up for a viewer looking along +x."""
    half = math.radians(angle_degrees) / 2.0
    return Quaternion(x=math.sin(half), y=0.0, z=0.0, w=math.cos(half))


def place(part: str, anchor, *, parked: bool = False, angle: float = 0.0) -> Pose:
    forward, side, height = LAYOUT[part]
    pose = Pose(
        position=Point(x=anchor[0] + forward, y=anchor[1] + side, z=PARKED_Z if parked else height),
        orientation=roll(angle),
    )
    return pose


def board_pose(anchor) -> Pose:
    return Pose(position=Point(x=anchor[0], y=anchor[1], z=HEIGHT), orientation=Quaternion(w=1.0))


def target_poses(anchor, lamp: str, needle: float, display: str) -> dict[str, Pose]:
    """Every model's pose for one complete state of the panel."""
    poses = {"inspection_board": board_pose(anchor), "inspection_dial": place("dial", anchor)}
    for colour in LAMP_COLOURS:
        poses[f"inspection_lamp_{colour}"] = place("lamp", anchor, parked=colour != lamp)
    poses["inspection_needle"] = place("needle", anchor, angle=needle)
    for reading in ("norm", "anomaly"):
        poses[f"inspection_display_{reading}"] = place("display", anchor, parked=reading != display)
    return poses


# --- the world -----------------------------------------------------------------------------------


class World:
    def __init__(self) -> None:
        rospy.init_node("inspection_ctl", anonymous=True, disable_signals=True)
        for service in ("/gazebo/get_model_state", "/gazebo/set_model_state", "/gazebo/spawn_sdf_model", "/gazebo/delete_model"):
            rospy.wait_for_service(service, timeout=15)
        self._get = rospy.ServiceProxy("/gazebo/get_model_state", GetModelState)
        self._set = rospy.ServiceProxy("/gazebo/set_model_state", SetModelState)
        self._spawn = rospy.ServiceProxy("/gazebo/spawn_sdf_model", SpawnModel)
        self._delete = rospy.ServiceProxy("/gazebo/delete_model", DeleteModel)

    def exists(self, name: str) -> bool:
        return bool(self._get(name, "world").success)

    def pose(self, name: str) -> Pose | None:
        reply = self._get(name, "world")
        return reply.pose if reply.success else None

    def ensure(self, anchor) -> list[str]:
        """Spawn every missing model, parked, so a half-present panel is completed, not duplicated."""
        spawned = []
        for name in MODELS:
            if self.exists(name):
                continue
            pose = board_pose(anchor) if name == "inspection_board" else Pose(position=Point(x=anchor[0], y=anchor[1], z=PARKED_Z), orientation=Quaternion(w=1.0))
            reply = self._spawn(name, model_sdf(name), "", pose, "world")
            if not reply.success:
                raise RuntimeError(f"could not spawn {name}: {reply.status_message}")
            spawned.append(name)
        return spawned

    def apply(self, poses: dict[str, Pose]) -> None:
        for name, pose in poses.items():
            state = ModelState(model_name=name, pose=pose, reference_frame="world")
            reply = self._set(state)
            if not reply.success:
                raise RuntimeError(f"could not move {name}: {reply.status_message}")

    def park(self) -> None:
        """Put the robot at HOME with no velocity. AMCL must be re-seeded afterwards (it still believes
        the old pose); the regression tooling's reseed script does that."""
        half = math.radians(HOME[2]) / 2.0
        pose = Pose(position=Point(x=HOME[0], y=HOME[1], z=0.0), orientation=Quaternion(z=math.sin(half), w=math.cos(half)))
        reply = self._set(ModelState(model_name="robot", pose=pose, reference_frame="world"))
        if not reply.success:
            raise RuntimeError(f"could not move the robot: {reply.status_message}")

    def remove(self) -> list[str]:
        gone = []
        for name in MODELS:
            if self.exists(name):
                self._delete(name)
                gone.append(name)
        return gone

    def read(self) -> dict | None:
        """The panel's present state, read back from the world (not from a file)."""
        if not all(self.exists(m) for m in MODELS):
            return None
        lamp = next((c for c in LAMP_COLOURS if self.pose(f"inspection_lamp_{c}").position.z > 0), None)
        display = next((r for r in ("norm", "anomaly") if self.pose(f"inspection_display_{r}").position.z > 0), None)
        q = self.pose("inspection_needle").orientation
        angle = math.degrees(2.0 * math.atan2(q.x, q.w)) % 360.0
        return {"lamp": lamp, "dial": round(angle, 1), "display": {"norm": "42.7", "anomaly": "49.9"}.get(display, None)}


# --- states --------------------------------------------------------------------------------------

STATES = {
    "lamp": {"norm": "green", "anomaly": "red", "off": "off"},
    "display": {"norm": "norm", "anomaly": "anomaly"},
}


def current(world: World) -> tuple[str, float, str]:
    """(lamp colour, needle angle, display reading) as the world has them now, with norm defaults."""
    state = world.read()
    if state is None:
        return "green", NEEDLE_NORM, "norm"
    display = "anomaly" if state["display"] == "49.9" else "norm"
    return state["lamp"] or "green", state["dial"], display


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--anchor", default=f"{ANCHOR[0]},{ANCHOR[1]}", help="world X,Y of the board centre")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("set", help="put one object into a state")
    one.add_argument("object", choices=["lamp", "dial", "display"])
    one.add_argument("state", help="norm | anomaly (lamp also: off; dial also: angle=<degrees>)")
    sub.add_parser("all", help="put every object into the same named state: norm or anomaly").add_argument("state", choices=["norm", "anomaly"])
    sub.add_parser("status", help="print the panel's present state as JSON")
    sub.add_parser("park", help="put the robot at the inspection spot (exact pose, zero velocity)")
    sub.add_parser("ensure", help="spawn the panel if it is missing (idempotent)")
    sub.add_parser("remove", help="delete the panel from the world")
    args = parser.parse_args(argv)
    anchor = tuple(float(v) for v in args.anchor.split(","))

    world = World()
    if args.command == "remove":
        print(json.dumps({"removed": world.remove()}))
        return 0
    if args.command == "park":
        world.park()
        print(json.dumps({"parked": {"x": HOME[0], "y": HOME[1], "yaw_degrees": HOME[2]}}))
        return 0
    if args.command == "status":  # reading must not change the world: no panel is not an error
        print(json.dumps({"spawned": [], "state": world.read()}))
        return 0
    spawned = world.ensure(anchor)
    if spawned and args.command != "ensure":
        time.sleep(0.5)  # a model just spawned is not always settable in the same instant
    lamp, needle, display = current(world)
    if spawned:  # a fresh panel starts in its norm state
        lamp, needle, display = "green", NEEDLE_NORM, "norm"

    if args.command == "set":
        if args.object == "lamp":
            if args.state not in STATES["lamp"]:
                parser.error("lamp states: norm, anomaly, off")
            lamp = STATES["lamp"][args.state]
        elif args.object == "dial":
            if args.state == "norm":
                needle = NEEDLE_NORM
            elif args.state == "anomaly":
                needle = NEEDLE_ANOMALY
            elif args.state.startswith("angle="):
                needle = float(args.state.split("=", 1)[1]) % 360.0
            else:
                parser.error("dial states: norm, anomaly, angle=<degrees>")
        else:
            if args.state not in STATES["display"]:
                parser.error("display states: norm, anomaly")
            display = STATES["display"][args.state]
    elif args.command == "all":
        lamp, needle, display = (STATES["lamp"][args.state], NEEDLE_NORM if args.state == "norm" else NEEDLE_ANOMALY, args.state)
    if args.command in ("set", "all", "ensure"):
        world.apply(target_poses(anchor, lamp, needle, display))
    print(json.dumps({"spawned": spawned, "state": world.read()}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except rospy.ROSException as exc:
        print(f"error: Gazebo's services are not available ({exc})", file=sys.stderr)
        raise SystemExit(2)
