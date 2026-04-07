# neo_workshop Mapping and Navigation

This workspace uses `catkin_make`, not `catkin build`.

Real runtime topics:

- Laser scan: `/robot/front_laser/scan`
- Map: `/robot/map`
- Base velocity command: `/robot/robotnik_base_control/cmd_vel`

The mapping launch does not start `neo_workshop_auto_map.py` unless `launch_auto_map:=true` is set. The default is `launch_auto_map:=false`.

Build:

```bash
bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && catkin_make'
```

Launch mapping:

```bash
bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_mapping.launch'
```

Launch mapping and auto-start the script from the same launch:

```bash
bash -lc 'cd ~/catkin_ws && source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && roslaunch rb1_base_gazebo rb1_neo_workshop_mapping.launch launch_auto_map:=true'
```

Run the auto-mapping script manually:

```bash
bash -lc 'source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash && rosrun rb1_base_gazebo neo_workshop_auto_map.py'
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
pkill -f gzserver || true
pkill -f gzclient || true
```
