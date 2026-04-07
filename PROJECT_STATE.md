# Current Verified State

- Repo root: `~/catkin_ws/src`
- Workspace root: `~/catkin_ws`
- Repo origin: `https://github.com/skydancerbg/rb1-base-sim-noetic.git`
- Branch at inspection time: `main`
- Build system: `catkin_make`

# neo_workshop

- `rb1_neo_workshop_mapping.launch` works
- `neo_workshop_auto_map.py` works when run manually
- Map files save successfully to:
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.yaml`
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.pgm`
- `rb1_neo_workshop_navigation.launch` works with the saved map
- `rb1navindemoworl.launch` still works and must remain untouched

# Verified Topics

- Scan: `/robot/front_laser/scan`
- Map: `/robot/map`
- Map metadata: `/robot/map_metadata`
- Particle cloud: `/robot/particlecloud`
- Base cmd_vel: `/robot/robotnik_base_control/cmd_vel`
- Base odom: `/robot/robotnik_base_control/odom`
- move_base cmd_vel: `/robot/move_base/cmd_vel`
- Local plan: `/robot/move_base/TebLocalPlannerROS/local_plan`
- Global plan: `/robot/move_base/TebLocalPlannerROS/global_plan`

# Verified Nodes

- Mapping:
- `/gazebo`
- `/gazebo_gui`
- `/robot/slam_gmapping`
- `/robot/twist_mux`
- `/robot/robot_state_publisher`
- `/robot/complementary_filter_node`

- Navigation:
- `/gazebo`
- `/gazebo_gui`
- `/rviz`
- `/robot/robot_map_server`
- `/robot/amcl`
- `/robot/move_base`
- `/robot/twist_mux`
- `/robot/robot_state_publisher`
- `/robot/complementary_filter_node`

# Behavior Notes

- `rb1_neo_workshop_mapping.launch` does not auto-run `neo_workshop_auto_map.py` by default.
- Auto-start is only enabled if `launch_auto_map:=true` is passed.
- Stale Gazebo processes can cause `SpawnModel: Failure - entity already exists.` between back-to-back world launches.

# Daily Commands

- Build:
- `tools/run_neo_workshop.sh build`
- Mapping:
- `tools/run_neo_workshop.sh mapping`
- Automap:
- `tools/run_neo_workshop.sh automap`
- Check map:
- `tools/run_neo_workshop.sh check-map`
- Navigation:
- `tools/run_neo_workshop.sh navigation`
- Demo:
- `tools/run_neo_workshop.sh demo`
