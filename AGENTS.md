# Repo Instructions

- This repository is a ROS1 Noetic project on Ubuntu 20.04.
- Repo root: `~/catkin_ws/src`
- Workspace root: `~/catkin_ws`
- Build system: `catkin_make`
- Do not use `catkin build` unless explicitly requested.

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
- Prefer minimal localized changes.
- Do not refactor unrelated files.
- Require real runtime verification, not syntax-only checks.
- After changes, provide exact commands used and exact commands to rerun.

# neo_workshop Entry Points

- Mapping launch:
- `bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_mapping.launch'`
- Manual automap:
- `bash -lc 'source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && rosrun rb1_base_gazebo neo_workshop_auto_map.py'`
- Navigation launch:
- `bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_navigation.launch'`
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

# Known Issue

- Stale `gzserver` or `gzclient` processes can block relaunches with `SpawnModel: Failure - entity already exists.`
- Cleanup helper: `~/catkin_ws/src/tools/kill_gazebo_ros.sh`
