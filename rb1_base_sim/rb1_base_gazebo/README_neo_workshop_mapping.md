# neo_workshop Mapping and Navigation

This workspace uses `catkin_make`, not `catkin build`.

Real runtime topics:

- Laser scan: `/robot/front_laser/scan`
- Map: `/robot/map`
- Base velocity command: `/robot/robotnik_base_control/cmd_vel`

The current active operator path is manual mapping in `neo_workshop.world` using `rb1_neo_workshop_manual_mapping.launch`.
Autonomous/frontier files are preserved in the repo, but they are not the current active operator path.

Current manual joystick assumptions:

- Device: `/dev/input/js1`
- Controller: Logitech F710 in X mode over usbip
- Joystick driver path: `joy_node -> /robot/joy -> teleop_twist_joy -> /robot/pad_teleop/cmd_vel_raw -> manual_speed_selector -> /robot/pad_teleop/cmd_vel -> twist_mux -> /robot/robotnik_base_control/cmd_vel`
- Active manual mapping:
  - `enable_button = 5`
  - both sticks drive
  - left stick vertical `axis 1` and right stick vertical `axis 4` control forward/back
  - left stick horizontal `axis 0` and right stick horizontal `axis 3` control rotation
  - base linear scale `0.35`
  - base angular scale `0.8`
  - D-pad up = `TURBO`
  - D-pad down = `NORMAL`

Legacy note:

- Older DirectInput / D-mode / `rb1_base_pad` joystick notes are not the active manual path anymore.

Build:

```bash
bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && catkin_make'
```

Launch the current active manual mapping path with RViz:

```bash
bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_manual_mapping.launch launch_rviz:=true'
```

Launch the current manual path with `/robot/pad_teleop/cmd_vel` echo enabled:

```bash
bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_manual_mapping.launch launch_rviz:=true echo_pad_cmd_vel:=true'
```

Legacy mapping launch kept in the repo:

```bash
bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_mapping.launch'
```

Save the manual map while the mapping launch stays running:

```bash
bash -lc 'cd ~/catkin_ws/src && ./tools/save_neo_workshop_map.sh'
```

Check the saved map files:

```bash
bash -lc 'ls -lh ~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.yaml ~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.pgm'
```

Launch navigation with the saved neo_workshop map:

```bash
bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_navigation.launch'
```

Gazebo cleanup note:

Back-to-back launches can leave stale `gzserver` or `gzclient` processes running, which can cause `SpawnModel: Failure - entity already exists.` If that happens, stop the old Gazebo processes before relaunching:

```bash
bash -lc 'cd ~/catkin_ws/src && ./tools/kill_gazebo_ros.sh'
```
