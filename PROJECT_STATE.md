# Current Verified State

- Repo root: `~/catkin_ws/src`
- Workspace root: `~/catkin_ws`
- Repo origin: `https://github.com/skydancerbg/rb1-base-sim-noetic.git`
- Branch at inspection time: `main`
- Build system: `catkin_make`

# neo_workshop

- `rb1_neo_workshop_mapping.launch` works
- `neo_workshop_auto_map.py` works when run manually and should not be modified unless explicitly requested
- Map files save successfully to:
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.yaml`
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.pgm`
- `rb1_neo_workshop_navigation.launch` works with the saved map
- `rb1navindemoworl.launch` still works and must remain untouched
- `rb1_neo_workshop_frontier_mapping.launch` is integrated and launches:
- Gazebo in `neo_workshop.world`
- `slam_gmapping`
- frontier-only `move_base`
- `explore_lite`
- frontier goal guard
- frontier-specific RViz config

# Verified Topics

- Scan: `/robot/front_laser/scan`
- Map: `/robot/map`
- Map metadata: `/robot/map_metadata`
- Particle cloud: `/robot/particlecloud`
- Base cmd_vel: `/robot/robotnik_base_control/cmd_vel`
- Base odom: `/robot/robotnik_base_control/odom`
- move_base cmd_vel: `/robot/move_base/cmd_vel`
- Global planner plan: `/robot/move_base/NavfnROS/plan`
- Local planner global plan: `/robot/move_base/TrajectoryPlannerROS/global_plan`
- Local planner local plan: `/robot/move_base/TrajectoryPlannerROS/local_plan`
- Frontier goal input: `/robot/move_base/goal`
- Frontier current goal: `/robot/move_base/current_goal`
- Frontier recovery status: `/robot/move_base/recovery_status`

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

- Frontier mapping:
- `/gazebo`
- `/gazebo_gui`
- `/rviz`
- `/robot/slam_gmapping`
- `/robot/move_base`
- `/robot/explore`
- `/robot/frontier_goal_guard`
- `/robot/twist_mux`
- `/robot/robot_state_publisher`
- `/robot/complementary_filter_node`

# Behavior Notes

- `rb1_neo_workshop_mapping.launch` does not auto-run `neo_workshop_auto_map.py` by default.
- Auto-start is only enabled if `launch_auto_map:=true` is passed.
- Stale Gazebo processes can cause `SpawnModel: Failure - entity already exists.` between back-to-back world launches.
- The RB1 robot geometry is cylindrical; `robot_radius` is the correct model for costmap tuning.
- The frontier stack uses a dedicated frontier-only `move_base` and corrected frontier RViz config.
- The frontier goal guard exists and blacklists only after repeated recovery on the same active goal.
- Repeated bad-corner reattack was reduced by the guard.
- The startup regression introduced by the guard was fixed.
- Current verified frontier global costmap baseline:
- `inflation_radius: 0.33`
- `cost_scaling_factor: 4.0`
- Current verified frontier local costmap baseline:
- `inflation_radius: 0.34`
- `cost_scaling_factor: 3.0`
- Current verified frontier local planner baseline includes:
- `max_vel_x: 0.16`
- `occdist_scale: 0.31`
- `sim_time: 1.0`
- Current reported improvement: post-pass wall-hugging improved in the tested failure mode.
- Current caution: do not yet claim full end-to-end perfect exploration in every long run.
- Do not revisit footprint-shape changes; future tuning should keep using `robot_radius`.
- Do not blindly retune inflation without runtime evidence.
- Prefer frontier-only minimal changes and base next work on observed long-run behavior rather than restarting older solved debugging branches.
- For frontier work, Codex should test changes itself and avoid asking the user to run diagnostic commands whenever possible.

# Daily Commands

- Build:
- `tools/run_neo_workshop.sh build`
- Mapping:
- `tools/run_neo_workshop.sh mapping`
- Automap:
- `tools/run_neo_workshop.sh automap`
- Frontier mapping:
- `tools/run_neo_workshop.sh frontier-mapping`
- Frontier save:
- `tools/run_neo_workshop.sh frontier-save`
- Check map:
- `tools/run_neo_workshop.sh check-map`
- Navigation:
- `tools/run_neo_workshop.sh navigation`
- Demo:
- `tools/run_neo_workshop.sh demo`
