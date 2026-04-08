# neo_workshop_gui.sh Usage

The GUI launcher opens separate `gnome-terminal` windows for the verified neo_workshop workflow so you do not need to manage multiple terminals manually.

Current active operator path:

- Manual mapping in `neo_workshop.world`
- Logitech F710 in X mode over usbip
- Save maps with `./tools/save_neo_workshop_map.sh`
- Frontier/autonomous files are preserved but are not the current active path

## Commands

Start mapping plus automap:

```bash
./tools/neo_workshop_gui.sh map
```

Start frontier-based mapping:

```bash
./tools/neo_workshop_gui.sh frontier
```

Start navigation in neo_workshop:

```bash
./tools/neo_workshop_gui.sh nav
```

Stop stale Gazebo and ROS GUI processes:

```bash
./tools/neo_workshop_gui.sh stop
```

Show help:

```bash
./tools/neo_workshop_gui.sh help
```

## What `map` Does

1. Opens a terminal for:
   `cd ~/catkin_ws/src && ./tools/kill_gazebo_ros.sh && ./tools/run_neo_workshop.sh mapping`
2. Waits a few seconds.
3. Opens a second terminal for:
   `cd ~/catkin_ws/src && ./tools/run_neo_workshop.sh automap`
4. Opens a third terminal for:
   `cd ~/catkin_ws/src && ./tools/verify_neo_workshop.sh map-files`
5. Keeps each terminal open with `exec bash`

## What `nav` Does

1. Opens a terminal for:
   `cd ~/catkin_ws/src && ./tools/kill_gazebo_ros.sh && ./tools/run_neo_workshop.sh navigation`
2. Waits a few seconds.
3. Opens a second terminal for:
   `cd ~/catkin_ws/src && ./tools/verify_neo_workshop.sh navigation`
4. Keeps each terminal open with `exec bash`

## What `frontier` Does

1. Opens a terminal for:
   `cd ~/catkin_ws/src && ./tools/kill_gazebo_ros.sh && ./tools/run_neo_workshop.sh frontier-mapping`
2. Leaves the exploration stack running in that terminal
3. After exploration is complete, save the map manually from another terminal with:
   `cd ~/catkin_ws/src && ./tools/run_neo_workshop.sh frontier-save`

## What `stop` Does

- Runs `./tools/kill_gazebo_ros.sh` from the repo root
- Stops stale Gazebo and ROS GUI processes commonly left behind after switching worlds
- Does not close unrelated user terminals directly

## Notes

- Repo root: `~/catkin_ws/src`
- Workspace root: `~/catkin_ws`
- The script requires `gnome-terminal`
- The current active manual path is launched directly with:
  - `bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_manual_mapping.launch launch_rviz:=true'`
- Optional manual debug helper:
  - `bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_manual_mapping.launch launch_rviz:=true echo_pad_cmd_vel:=true'`
- The current manual path uses `teleop_twist_joy`, not `rb1_base_pad`, for joystick driving.
- The script reuses:
  - `./tools/kill_gazebo_ros.sh`
  - `./tools/run_neo_workshop.sh`
  - `./tools/verify_neo_workshop.sh`
