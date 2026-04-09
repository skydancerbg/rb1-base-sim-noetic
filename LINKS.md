# Local

- Repo root: `~/catkin_ws/src`
- Workspace root: `~/catkin_ws`
- Git remote: `https://github.com/skydancerbg/rb1-base-sim-noetic.git`
- Current active operator path: manual neo_workshop mapping
- Active manual launch:
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/launch/rb1_neo_workshop_manual_mapping.launch`
- Active joystick device:
- `/dev/input/js1`
- Current controller mode:
- Logitech F710 in X mode over usbip
- Active manual control path:
- `/robot/joy -> /robot/teleop_twist_joy -> /robot/pad_teleop/cmd_vel_raw -> /robot/manual_speed_selector -> /robot/pad_teleop/cmd_vel -> /robot/twist_mux -> /robot/robotnik_base_control/cmd_vel`
- Active joy config:
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/config/neo_workshop_joy.yaml`
- Active teleop config:
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/config/neo_workshop_f710_xinput_twist_joy.yaml`
- Manual speed selector:
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/scripts/manual_speed_selector.py`
- Map save helper:
- `~/catkin_ws/src/tools/save_neo_workshop_map.sh`
- Map outputs:
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.yaml`
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.pgm`
- neo_workshop README:
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/README_neo_workshop_mapping.md`
- neo_workshop workflow doc:
- `~/catkin_ws/src/docs/neo_workshop_workflow.md`
- Active navigation launch:
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/launch/rb1_neo_workshop_navigation.launch`
- Simulated USB camera xacro:
- `~/catkin_ws/src/rb1_base_common/rb1_base_description/urdf/sensors/usb_cam_webcam.urdf.xacro`
- Simulated USB camera mesh:
- `~/catkin_ws/src/rb1_base_common/rb1_base_description/meshes/sensors/usb_cam_c922_style.dae`
- Simulated USB camera topics:
- `/robot/usb_cam/image_raw`
- `/robot/usb_cam/camera_info`
- Preserved but non-active operator paths:
- frontier/autonomous neo_workshop files remain in the repo, but they are not the current active operator path

# Relevant Upstream Docs

- ROS Noetic: `https://wiki.ros.org/noetic`
- catkin workspace basics: `https://wiki.ros.org/catkin/Tutorials/create_a_workspace`
- roslaunch: `https://wiki.ros.org/roslaunch`
- map_server: `https://wiki.ros.org/map_server`
- gmapping: `https://wiki.ros.org/gmapping`
- amcl: `https://wiki.ros.org/amcl`

# First Places To Inspect

- `~/catkin_ws/src/tools/`
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/launch/`
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/config/`
- `~/catkin_ws/src/rb1_base_sim/rb1_base_gazebo/scripts/`
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/`
