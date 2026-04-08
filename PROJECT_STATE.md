# Current Verified State

- Repo root: `~/catkin_ws/src`
- Workspace root: `~/catkin_ws`
- Repo origin: `https://github.com/skydancerbg/rb1-base-sim-noetic.git`
- Branch at inspection time: `main`
- Build system: `catkin_make`

# neo_workshop

- Current active operator path: manual mapping in `neo_workshop.world`
- Working manual mapping launch:
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/launch/rb1_neo_workshop_manual_mapping.launch`
- Manual mapping is working: the operator can drive the robot and save the map
- RViz is supported for manual mapping and the verified operator launch uses `launch_rviz:=true`
- Manual joystick device:
- `/dev/input/js1`
- Controller mode for the current manual path:
- Logitech F710 in X mode over usbip
- Manual control no longer relies on `rb1_base_pad` for joystick driving
- Manual mapping now uses `teleop_twist_joy`
- Active manual control path:
- `/dev/input/js1`
- `/robot/joy_node`
- `/robot/joy`
- `/robot/teleop_twist_joy`
- `/robot/pad_teleop/cmd_vel`
- `/robot/twist_mux`
- `/robot/robotnik_base_control/cmd_vel`
- Gazebo
- Active manual X-mode mapping:
- `enable_button = 5`
- `axis_linear.x = 4`
- `axis_angular.yaw = 0`
- `scale_linear.x = -0.35`
- `scale_angular.yaw = 0.8`
- Optional manual debug helper:
- `echo_pad_cmd_vel:=true`
- This starts `rostopic echo /robot/pad_teleop/cmd_vel`
- Map save workflow while mapping remains running:
- `cd ~/catkin_ws/src && ./tools/save_neo_workshop_map.sh`
- Saved map files:
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.yaml`
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.pgm`
- `rb1_neo_workshop_navigation.launch` works with the saved map
- `rb1navindemoworl.launch` still works and must remain untouched
- `neo_workshop_auto_map.py` is preserved and must not be modified unless explicitly requested
- Frontier/autonomous work is preserved in the repo but is temporarily deprioritized and is not the current active operator path

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

- Manual mapping:
- `/gazebo`
- `/gazebo_gui`
- `/robot/joy_node`
- `/robot/teleop_twist_joy`
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

- Prefer `rb1_neo_workshop_manual_mapping.launch` for current neo_workshop work.
- The current manual path uses Logitech F710 in X mode over usbip.
- The current manual path uses `teleop_twist_joy`, not `rb1_base_pad`, for joystick driving.
- Older D-mode / DirectInput / `rb1_base_pad` joystick notes are legacy for the current manual path and should not be treated as active guidance.
- `rb1_neo_workshop_mapping.launch` does not auto-run `neo_workshop_auto_map.py` by default.
- Auto-start is only enabled if `launch_auto_map:=true` is passed.
- Stale Gazebo processes can cause `SpawnModel: Failure - entity already exists.` between back-to-back world launches.
- The RB1 robot geometry is cylindrical; `robot_radius` is the correct model for costmap tuning.
- Autonomous/frontier work is preserved but currently paused in favor of the working manual mapping path.
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
- Active manual mapping with RViz:
- `bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_manual_mapping.launch launch_rviz:=true'`
- Active manual mapping with cmd_vel echo helper:
- `bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_manual_mapping.launch launch_rviz:=true echo_pad_cmd_vel:=true'`
- Save manual map:
- `cd ~/catkin_ws/src && ./tools/save_neo_workshop_map.sh`
- Legacy mapping launch:
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
