# Repo Instructions

- This repository is a ROS1 Noetic project on Ubuntu 20.04.
- Repo root: `~/catkin_ws/src`
- Workspace root: `~/catkin_ws`
- Build system: `catkin_make`
- Do not use `catkin build` unless explicitly requested.
- Prefer testing changes directly in this Codex session instead of asking the user to run diagnostic commands manually.

# ROS Environment

- Always source before ROS commands:
- `source /opt/ros/noetic/setup.bash`
- `source ~/catkin_ws/devel/setup.bash`
- If `~/catkin_ws/devel/setup.bash` does not exist yet, build first:
- `bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && catkin_make'`

# Important Packages

- `rb1_base_gazebo`
- `rb1_base_localization`

# Constraints

- Do not modify `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/launch/rb1navindemoworl.launch` unless explicitly requested.
- Do not modify `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/scripts/neo_workshop_auto_map.py` unless explicitly requested.
- Prefer minimal localized changes.
- Do not refactor unrelated files.
- Require real runtime verification, not syntax-only checks.
- After changes, provide exact commands used and exact commands to rerun.
- The RB1 robot in this simulation is cylindrical; `robot_radius` is the correct geometry model for navigation tuning. Do not spend time on explicit footprint-shape changes unless explicitly requested.

# neo_workshop Entry Points

- Mapping launch:
- `bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_mapping.launch'`
- Manual automap:
- `bash -lc 'source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && rosrun rb1_base_gazebo neo_workshop_auto_map.py'`
- Navigation launch:
- `bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_navigation.launch'`
- Frontier exploration launch:
- `bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_frontier_mapping.launch'`
- Original demo launch:
- `bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1navindemoworl.launch'`

# Runtime Facts

- Real scan topic: `/robot/front_laser/scan`
- Map topic: `/robot/map`
- Velocity command topic: `/robot/robotnik_base_control/cmd_vel`
- Mapping launch default does not auto-run `neo_workshop_auto_map.py`
- Saved map files:
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.yaml`
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.pgm`
- Frontier stack is integrated and uses `explore_lite` with a dedicated frontier-only `move_base`
- Frontier goal guard exists at:
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/scripts/neo_workshop_frontier_goal_guard.py`
- Frontier RViz config exists at:
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/rviz/rb1_neo_workshop_frontier_mapping.rviz`

# Frontier Notes

- The frontier stack no longer uses TEB topics; the active plan topics are:
- `/robot/move_base/NavfnROS/plan`
- `/robot/move_base/TrajectoryPlannerROS/global_plan`
- `/robot/move_base/TrajectoryPlannerROS/local_plan`
- The `explore_lite` frontier stack is integrated, launches, and moves with a dedicated frontier-only `move_base`.
- The frontier goal guard now blacklists only after repeated recovery on the same active goal.
- Repeated bad-corner reattack was reduced by the guard.
- The startup regression from the frontier goal guard was fixed.
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
- Current reported improvement: the tested post-pass wall-hugging failure mode improved.
- Current caution: do not claim full end-to-end perfect exploration in every long run yet.
- Do not revisit polygon footprint ideas for this robot.
- Do not blindly retune inflation without runtime evidence.
- Prefer frontier-only minimal changes and base next work on observed long-run behavior, not on reopening older solved debugging branches.

# Known Issue

- Stale `gzserver` or `gzclient` processes can block relaunches with `SpawnModel: Failure - entity already exists.`
- Cleanup helper: `~/catkin_ws/src/tools/kill_gazebo_ros.sh`
