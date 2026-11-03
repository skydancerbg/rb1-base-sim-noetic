#!/usr/bin/env python3
"""Verify the P5.6 acceptance on the running simulation, and save the evidence frames.

    ~/inspection/verify_p56.py [--evidence DIR]        # on the sim VM; takes about two minutes

Checks, against the camera's own frames (web_video_server snapshot of /robot/usb_cam/image_raw):
  1. each lighting regime gives a visibly different frame (mean absolute difference from nominal),
     and nominal restored matches nominal as closely as two frames of an unchanged scene do;
  2. each object visibly changes between its states, inside its own region, by clearly more than the
     frame-to-frame noise there, and changing it changes no other object's state (read back);
  3. a state is reproducible: the same argument twice gives the same read-back state and a frame as
     close to the first as two frames of an unchanged scene are.

What "the same frame" can mean here: the simulated robot creeps and turns a little while idle (about
0.1 degree per second), so two frames of an unchanged scene are not bit-identical even when the robot
is parked from this process at a fixed delay before each. The script measures that floor (two frames of
the same state) and judges every difference against it, instead of pretending it is zero.
Exit status 0 if everything holds, 1 if anything does not.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

from PIL import Image, ImageChops, ImageFilter, ImageStat

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
LIGHTING = os.path.join(os.path.dirname(HERE), "lighting", "set_regime.sh")
STATE = os.path.join(HERE, "set_state.sh")
URL = "http://127.0.0.1:8080/snapshot?topic=/robot/usb_cam/image_raw"

#: Pixel boxes (left, top, right, bottom) of each object in the 1280 x 720 frame, robot parked. The dial
#: and display boxes sit inside their rims: a rim is a sharp edge, and a one-pixel shift of the frame
#: would show up there as "change" although nothing moved.
BOX = {"lamp": (343, 230, 433, 320), "dial": (584, 303, 694, 413), "display": (788, 328, 980, 390)}
#: Smoothing (pixels) for the within-object comparisons; see `diff`.
BLUR = 3.0
RENDER_SETTLE = 1.5  # a light or state change reaches the camera within about a second
PARK_SETTLE = 2.0
_world = None


def run(script: str, *args: str) -> str:
    return subprocess.run([script, *args], check=True, capture_output=True, text=True).stdout.strip()


def state() -> dict:
    return json.loads(run(STATE, "status"))["state"]


def frame() -> Image.Image:
    """A frame with the robot parked from this process a fixed time earlier."""
    global _world
    if _world is None:
        from inspection_ctl import World  # imported late: it needs the ROS environment

        _world = World()
    time.sleep(RENDER_SETTLE)
    _world.park()
    time.sleep(PARK_SETTLE)
    with urllib.request.urlopen(URL, timeout=10) as reply:
        return Image.open(io.BytesIO(reply.read())).convert("RGB")


def diff(a: Image.Image, b: Image.Image, box=None, blur: float = 0.0) -> float:
    """Mean absolute difference per channel. `blur` smooths both sides first: a region full of edges
    (the display's digits) otherwise reads a one-pixel shift of the whole frame as a change."""
    if box:
        a, b = a.crop(box), b.crop(box)
    if blur:
        a, b = a.filter(ImageFilter.GaussianBlur(blur)), b.filter(ImageFilter.GaussianBlur(blur))
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3.0


def floor_of(images: list, box=None, blur: float = 0.0) -> float:
    """The noise floor: the smallest difference between any two frames of the same scene. The smallest,
    not the mean, because a single disturbed frame (the robot's creep is not perfectly regular) would
    otherwise raise every threshold; a floor can only be too high by that, never too low."""
    return min(diff(images[i], images[j], box, blur) for i in range(len(images)) for j in range(i + 1, len(images)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", default=os.path.join(HERE, "..", "..", "docs", "evidence", "p5.6"))
    args = parser.parse_args()
    os.makedirs(args.evidence, exist_ok=True)
    results, failures = {}, []

    def save(name: str, image: Image.Image) -> None:
        image.resize((640, 360), Image.LANCZOS).save(os.path.join(args.evidence, f"{name}.jpg"), quality=82)

    def check(name: str, ok: bool, detail: str) -> None:
        results[name] = {"ok": ok, "detail": detail}
        if not ok:
            failures.append(f"{name}: {detail}")

    # The floor: two frames of the same, unchanged scene.
    run(LIGHTING, "nominal")
    run(STATE, "all", "norm")
    base = [frame() for _ in range(3)]
    nominal = base[0]
    floor = floor_of(base, None, BLUR)
    results["noise_floor"] = {"ok": True, "detail": f"frames of an unchanged scene differ by {floor:.2f} at best (mean abs after smoothing, 3 frames)"}
    save("regime_nominal", nominal)

    # 1. regimes
    shots = {}
    for regime in ("dimmed", "side"):
        run(LIGHTING, regime)
        shots[regime] = frame()
        save(f"regime_{regime}", shots[regime])
    run(LIGHTING, "nominal")
    restored = frame()
    for regime, image in shots.items():
        d = diff(nominal, image, None, BLUR)
        check(f"regime_{regime}_differs_from_nominal", d > max(10.0, 5 * floor), f"mean abs difference {d:.1f} (floor {floor:.1f}; needs > {max(10.0, 5 * floor):.1f})")
    d = diff(shots["dimmed"], shots["side"], None, BLUR)
    check("dimmed_and_side_differ", d > max(8.0, 4 * floor), f"mean abs difference {d:.1f} (needs > {max(8.0, 4 * floor):.1f})")
    d = diff(nominal, restored, None, BLUR)
    check("nominal_restores", d < 2.5 * floor + 1.0, f"mean abs difference {d:.2f} (needs < {2.5 * floor + 1.0:.2f})")
    check("regime_is_recorded", run(LIGHTING, "status").startswith("nominal "), run(LIGHTING, "status"))

    # 2. objects
    others = {"lamp": ("dial", "display"), "dial": ("lamp", "display"), "display": ("lamp", "dial")}
    for obj, variants in (("lamp", ("anomaly", "off")), ("dial", ("anomaly",)), ("display", ("anomaly",))):
        run(STATE, "all", "norm")
        same = [frame() for _ in range(3)]
        norm = same[0]
        inside_floor = floor_of(same, BOX[obj], BLUR)
        save(f"{obj}_norm", norm)
        for variant in variants:
            before = state()
            run(STATE, obj, variant)
            changed = state()
            other = frame()
            save(f"{obj}_{variant}", other)
            inside = diff(norm, other, BOX[obj], BLUR)
            need = max(4.0, 2.5 * inside_floor)
            check(f"{obj}_{variant}_changes_its_region", inside > need, f"inside {inside:.1f} (its own floor {inside_floor:.1f}; needs > {need:.1f})")
            untouched = all(before[k] == changed[k] for k in ("lamp", "dial", "display") if k != obj)
            check(f"{obj}_{variant}_changes_no_other_object", untouched and before[obj] != changed[obj], f"before {before} after {changed}")
        run(STATE, "all", "norm")

    # 3. reproducibility
    states, pics = [], []
    for _ in range(2):
        run(STATE, "dial", "anomaly")
        states.append(state())
        pics.append(frame())
    check("same_argument_same_state", states[0] == states[1], json.dumps(states))
    d = diff(pics[0], pics[1], None, BLUR)
    check("same_argument_same_frame", d < 2.5 * floor + 1.0, f"mean abs difference {d:.2f} (needs < {2.5 * floor + 1.0:.2f})")
    run(STATE, "all", "norm")

    print(json.dumps(results, indent=2))
    if failures:
        print("FAILED:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    print("all P5.6 acceptance checks hold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
