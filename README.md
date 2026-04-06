# RB-1 Base Simulation (ROS Noetic)

This repository contains the simulation packages for the RB-1 Base robot, updated for ROS Noetic and Ubuntu 20.04.

## Project Structure

The project is divided into the following main components:

### rb1_base_common
Common packages including:
- **rb1_base_description**: URDF models, meshes, and kinematic configurations.
- **rb1_base_control**: Controller configurations for differential drive and the elevator system.
- **rb1_base_localization**: Configuration for robot localization.
- **rb1_base_navigation**: ROS navigation stack integration.
- **rb1_base_pad**: Joystick/Gamepad control logic.

### rb1_base_sim
Simulation-specific packages:
- **rb1_base_gazebo**: Gazebo world files and launch configurations.
- **rb1_base_sim_bringup**: Top-level launch files to bring up the complete simulation.

## Installation

### 1) Dependencies
Ensure you have ROS Noetic and Gazebo 11 installed. You will also need `vcstool`:

```bash
sudo apt-get update
sudo apt-get install -y python3-vcstool python3-catkin-tools
```

### 2) Workspace Setup

```bash
mkdir -p catkin_ws/src
cd catkin_ws/src
# Clone or import necessary repositories here
rosdep install --from-paths src --ignore-src -y
```

### 3) Build

```bash
catkin build
source devel/setup.bash
```

## Usage

### Launching the simulation
To launch a single RB-1 Base robot in a default demo world:

```bash
roslaunch rb1_base_sim_bringup rb1_base_complete.launch
```

### Teleoperation
You can control the robot via the command line:

```bash
rostopic pub /robot/robotnik_base_control/cmd_vel geometry_msgs/Twist "linear:
  x: 0.2
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.5" -r 10
```