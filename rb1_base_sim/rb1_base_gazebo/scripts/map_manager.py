#!/usr/bin/env python3
"""Start and stop a SLAM session on the running simulation (plan step P2.5).

**What this is for.** The console needs a mapping toggle: an operator starts a session, walks the
robot around while the map grows on screen, and stops it, leaving a saved map the navigation stack
then uses. Someone has to stop AMCL, start gmapping, save the result and put localisation back —
and it has to be a *server*, because the browser must never reach the robot infrastructure. The
browser talks to the backend, the backend talks to this, and only this touches ROS.

**Why not relaunch the simulation in mapping mode.** The repository's launcher can do that, but it
reloads 204 models and returns the robot to its spawn pose: about a minute of blackout every time
someone toggles mapping, and the technician's position lost. A facility robot does not restart the
world to make a map. So this performs node surgery on the running system instead, which was
verified by hand before it was written: AMCL and the map server can be killed and gmapping started
without the launch tearing down, `/robot/map` updates as the robot moves, and localisation comes
back afterwards.

**Security posture, stated plainly.** This has no authentication. It is a *write* path to the
robot infrastructure and it is protected the way `:9090` and `:8080` already are on this
deployment: a firewall that admits the web VM alone. Authentication, the role check and the audit
record live in the backend, which is the only client. Anything else with a route to this port can
start a SLAM session, which is why the port must never be opened wider.

**Operations are synchronous, and one at a time.** Starting takes ~20 s and stopping ~40 s;
returning early with "accepted" would mean the console reporting a state nobody had verified. A
second request while one is running gets 409 rather than a race between two roslaunches.

**On failure it tries to leave the robot navigable.** If gmapping does not come up, the session is
not silently half-started: localisation is restored and the error is returned. A robot with no map
server and no gmapping cannot plan at all, and that must not be the resting state of a failed
button press.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("MAP_MANAGER_HOST", "0.0.0.0")
PORT = int(os.environ.get("MAP_MANAGER_PORT", "8090"))

WORKSPACE = pathlib.Path(os.environ.get("WORKSPACE_ROOT", str(pathlib.Path.home() / "catkin_ws")))
SAVE_SCRIPT = WORKSPACE / "src/tools/save_neo_workshop_map.sh"
LOG_DIR = pathlib.Path(os.environ.get("MAP_MANAGER_LOG_DIR", "/tmp"))

ROS_MASTER_URI = os.environ.get("ROS_MASTER_URI", "http://10.25.25.115:11311")
ROS_IP = os.environ.get("ROS_IP", "10.25.25.115")

#: How long to wait for a service to appear or disappear before calling the step failed.
SERVICE_TIMEOUT = float(os.environ.get("MAP_MANAGER_SERVICE_TIMEOUT", "45"))

#: The nodes a mapping session displaces, and the one it creates.
LOCALISATION_NODES = ("/robot/amcl", "/robot/robot_map_server")
GMAPPING_NODE = "/robot/slam_gmapping"
STATIC_MAP_SERVICE = "/robot/static_map"
DYNAMIC_MAP_SERVICE = "/robot/dynamic_map"

_lock = threading.Lock()
_state = {
    "active": False,
    "phase": "idle",
    "started_at": None,
    "stopped_at": None,
    "map_saved_at": None,
    "detail": "no session has run since this service started",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def ros(command: str, timeout: float = 60.0) -> subprocess.CompletedProcess:
    """Run one command with ROS 1 and the workspace sourced.

    `set +u` before sourcing is not decoration: ROS's setup scripts read unset variables, and this
    project has already lost time to a script that failed at the `source` line under `set -u`.
    """
    script = (
        "set +u; "
        "source /opt/ros/noetic/setup.bash >/dev/null 2>&1; "
        f"source {WORKSPACE}/devel/setup.bash >/dev/null 2>&1; "
        f"export ROS_MASTER_URI={ROS_MASTER_URI}; export ROS_IP={ROS_IP}; "
        f"{command}"
    )
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, timeout=timeout
    )


def launch(launch_file: str, log_name: str) -> None:
    """Start a roslaunch detached, so it outlives the request that asked for it."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / log_name
    script = (
        "set +u; "
        "source /opt/ros/noetic/setup.bash >/dev/null 2>&1; "
        f"source {WORKSPACE}/devel/setup.bash >/dev/null 2>&1; "
        f"export ROS_MASTER_URI={ROS_MASTER_URI}; export ROS_IP={ROS_IP}; "
        f"exec roslaunch rb1_base_gazebo {launch_file}"
    )
    with log_path.open("wb") as log:
        subprocess.Popen(
            ["bash", "-c", script],
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )


def service_present(name: str) -> bool:
    result = ros(f"rosservice list 2>/dev/null | grep -qx {name}", timeout=20)
    return result.returncode == 0


def wait_for_service(name: str, present: bool, timeout: float = SERVICE_TIMEOUT) -> bool:
    """Wait until `name` is (or is not) offered. Returns False on timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if service_present(name) == present:
            return True
        time.sleep(1.0)
    return False


def kill_nodes(*names: str) -> None:
    ros("rosnode kill " + " ".join(names), timeout=30)
    # `rosnode kill` returns before the node is gone, and `rosnode cleanup` needs a confirmation it
    # cannot get here; a short settle is enough for the master to drop the registrations.
    time.sleep(3.0)


def read_map_meta() -> dict | None:
    """The saved map's own numbers, so a stop can report what it wrote rather than that it ran."""
    yaml_path = None
    result = ros("rospack find rb1_base_localization", timeout=20)
    if result.returncode == 0:
        yaml_path = pathlib.Path(result.stdout.strip()) / "maps/neo_workshop/neo_workshop.yaml"
    if yaml_path is None or not yaml_path.exists():
        return None
    fields = {}
    for line in yaml_path.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    stat = yaml_path.stat()
    return {
        "yaml": str(yaml_path),
        "image": fields.get("image"),
        "resolution": fields.get("resolution"),
        "saved_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(
            timespec="seconds"
        ),
    }


# --- the two operations -------------------------------------------------------------------------


def start_session() -> tuple[int, dict]:
    if _state["active"]:
        return 409, {"error": "a mapping session is already running", "state": public_state()}

    _state["phase"] = "stopping localisation"
    kill_nodes(*LOCALISATION_NODES)
    if not wait_for_service(STATIC_MAP_SERVICE, present=False, timeout=20):
        _state["phase"] = "idle"
        return 500, {"error": "the map server did not stop; localisation left as it was"}

    _state["phase"] = "starting gmapping"
    launch("mapping_session.launch", "mapping_session.log")
    if not wait_for_service(DYNAMIC_MAP_SERVICE, present=True):
        # Do not leave the robot with neither a map server nor gmapping: it could not plan at all.
        _state["phase"] = "restoring localisation after a failed start"
        launch("localization_restore.launch", "localization_restore.log")
        wait_for_service(STATIC_MAP_SERVICE, present=True)
        _state["phase"] = "idle"
        return 500, {"error": "gmapping did not start; localisation restored"}

    _state.update(
        active=True,
        phase="mapping",
        started_at=now(),
        stopped_at=None,
        detail="gmapping is building the map; drive the robot to extend it",
    )
    return 200, {"state": public_state()}


def stop_session() -> tuple[int, dict]:
    if not _state["active"]:
        return 409, {"error": "no mapping session is running", "state": public_state()}

    _state["phase"] = "saving the map"
    saved = ros(f"bash {SAVE_SCRIPT}", timeout=180)
    if saved.returncode != 0:
        # The session stays up on purpose: the map is still in gmapping's memory, and stopping now
        # would throw away whatever the operator has just driven.
        _state["phase"] = "mapping"
        return 500, {
            "error": "map_saver failed; the session is still running so nothing was lost",
            "detail": (saved.stderr or saved.stdout)[-400:],
        }

    _state["phase"] = "stopping gmapping"
    kill_nodes(GMAPPING_NODE)

    _state["phase"] = "restoring localisation"
    launch("localization_restore.launch", "localization_restore.log")
    restored = wait_for_service(STATIC_MAP_SERVICE, present=True)

    _state.update(
        active=False,
        phase="idle" if restored else "localisation did not come back",
        stopped_at=now(),
        map_saved_at=now(),
        detail=(
            "map saved and localisation restored against it"
            if restored
            else "map saved, but the map server did not come back - check the sim VM"
        ),
    )
    body = {"state": public_state(), "map": read_map_meta()}
    return (200 if restored else 500), body


def public_state() -> dict:
    return {key: _state[key] for key in
            ("active", "phase", "started_at", "stopped_at", "map_saved_at", "detail")}


# --- HTTP ---------------------------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    server_version = "robco-map-manager/1.0"

    def _respond(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        if self.path.rstrip("/") in ("", "/session"):
            self._respond(200, {"state": public_state()})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")
        if path not in ("/session/start", "/session/stop"):
            self._respond(404, {"error": "not found"})
            return
        if not _lock.acquire(blocking=False):
            self._respond(409, {"error": "another mapping operation is in progress",
                                "state": public_state()})
            return
        try:
            status, payload = start_session() if path.endswith("start") else stop_session()
        except Exception as exc:  # noqa: BLE001 - the caller gets the reason, not a hung socket
            status, payload = 500, {"error": f"{type(exc).__name__}: {exc}"}
        finally:
            _lock.release()
        self._respond(status, payload)

    def log_message(self, fmt: str, *args) -> None:
        print(f"{now()} {self.address_string()} {fmt % args}", flush=True)


def main() -> int:
    print(f"{now()} map manager listening on {HOST}:{PORT}, master {ROS_MASTER_URI}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
