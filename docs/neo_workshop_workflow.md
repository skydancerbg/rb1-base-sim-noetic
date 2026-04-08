# neo_workshop Workflow

This repository includes helper scripts under `tools/` so you do not need to retype the long ROS setup and launch commands each time.

Current active path:

- Manual mapping in `neo_workshop.world`
- Logitech F710 in X mode over usbip
- `rb1_neo_workshop_manual_mapping.launch`
- Autonomous/frontier files are preserved but are not the current active operator path

# Workflow Order

1. Build the workspace.
2. Launch the manual neo_workshop mapping world with RViz.
3. Drive the robot manually to build the map.
4. Save the map with `tools/save_neo_workshop_map.sh` while mapping stays running.
5. Verify that the saved map files exist.
6. Launch neo_workshop navigation using the saved map.
7. Launch the original demo navigation only when you want the baseline demo world instead.

# Command Shortcuts

Build the workspace:

```bash
tools/run_neo_workshop.sh build
```

Launch the current active manual mapping path with RViz:

```bash
bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_manual_mapping.launch launch_rviz:=true'
```

Launch the current manual path with `/robot/pad_teleop/cmd_vel` echo enabled:

```bash
bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_manual_mapping.launch launch_rviz:=true echo_pad_cmd_vel:=true'
```

Save the manual map:

```bash
cd ~/catkin_ws/src
./tools/save_neo_workshop_map.sh
```

Check the saved map files:

```bash
tools/run_neo_workshop.sh check-map
```

Launch neo_workshop navigation:

```bash
tools/run_neo_workshop.sh navigation
```

Launch the original demo navigation:

```bash
tools/run_neo_workshop.sh demo
```

Clean stale Gazebo and ROS GUI processes before switching worlds:

```bash
tools/kill_gazebo_ros.sh
```

# What Each Step Does

- Manual mapping launch:
- Starts `rb1_neo_workshop_manual_mapping.launch`
- Brings up the neo_workshop world with gmapping
- Keeps RViz available when `launch_rviz:=true` is used
- Uses `joy_node` on `/dev/input/js1`
- Uses Logitech F710 in X mode over usbip
- Uses `teleop_twist_joy` plus `manual_speed_selector.py`, not `rb1_base_pad`, for the current joystick-driving path
- Uses:
  - `enable_button = 5`
  - left stick vertical `axis 1` and right stick vertical `axis 4` control forward/back
  - left stick horizontal `axis 0` and right stick horizontal `axis 3` control rotation
  - base linear scale `0.35`
  - base angular scale `0.8`
  - D-pad up = `TURBO`
  - D-pad down = `NORMAL`
- Supports `echo_pad_cmd_vel:=true` to run `rostopic echo /robot/pad_teleop/cmd_vel`

- Preserved autonomous path:
- `rb1_neo_workshop_mapping.launch` and `neo_workshop_auto_map.py` remain in the repo
- They are not the current active operator path

- Navigation launch:
- Starts `rb1_neo_workshop_navigation.launch`
- Loads `neo_workshop.yaml`
- Starts map server, AMCL, move_base, and RViz through the current navigation launch path

- Demo launch:
- Starts `rb1navindemoworl.launch`
- Uses the original demo setup and should remain unchanged unless explicitly requested

# Saved Map Location

- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.yaml`
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.pgm`

# Verification

The helper verifier supports environment, runtime, and file checks:

```bash
tools/verify_neo_workshop.sh env
tools/verify_neo_workshop.sh map-files
tools/verify_neo_workshop.sh mapping
tools/verify_neo_workshop.sh navigation
tools/verify_neo_workshop.sh all
```

Use `mapping` while the mapping launch is already running. Use `navigation` while the navigation launch is already running.
