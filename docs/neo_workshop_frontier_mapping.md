# neo_workshop Frontier Mapping

This repository now includes an additive frontier-based mapping path for `neo_workshop` alongside the existing custom `neo_workshop_auto_map.py` flow.

## Repo Facts

- Repo root: `~/catkin_ws/src`
- Workspace root: `~/catkin_ws`
- Build system: `catkin_make`

## Chosen Package

- Package: `explore_lite`
- Apt package: `ros-noetic-explore-lite`

## Why This Package

- It is a lightweight frontier-exploration package released for ROS1 Noetic.
- It integrates directly with the standard `move_base` action server.
- It works with the existing `/robot/map` occupancy grid produced by `slam_gmapping`.
- It is a better fit for autonomous exploration than adding more custom `cmd_vel` logic.

## Install Prerequisite

The package is not part of this repository. Install it on the Ubuntu 20.04 VM with:

```bash
sudo apt update
sudo apt install ros-noetic-explore-lite
```

## New Launch Flow

The new launch file is:

- `rb1_base_sim/rb1_base_gazebo/launch/rb1_neo_workshop_frontier_mapping.launch`

It starts:

- Gazebo in `neo_workshop.world`
- the RB1 robot in the existing `/robot` namespace
- `slam_gmapping`
- a dedicated exploration-only `move_base`
- `explore_lite`
- `neo_workshop_frontier_goal_guard.py`
- the corrected frontier RViz config

The map still comes from:

- `/robot/map`

The saved map still goes to:

- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.yaml`
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.pgm`

## Helper Commands

Build:

```bash
cd ~/catkin_ws/src
./tools/run_neo_workshop.sh build
```

Start frontier exploration mapping:

```bash
cd ~/catkin_ws/src
./tools/run_neo_workshop.sh frontier-mapping
```

Save the resulting map safely into the active `neo_workshop` files:

```bash
cd ~/catkin_ws/src
./tools/run_neo_workshop.sh frontier-save
```

Launch navigation with the saved map:

```bash
cd ~/catkin_ws/src
./tools/run_neo_workshop.sh navigation
```

GUI helper:

```bash
cd ~/catkin_ws/src
./tools/neo_workshop_gui.sh frontier
```

## Safe Map Save Behavior

The frontier path uses `tools/save_neo_workshop_map.sh`.

It saves to:

- `neo_workshop_tmp.yaml`
- `neo_workshop_tmp.pgm`

in the same map directory first, verifies both temp files exist and are non-empty, and only then replaces:

- `neo_workshop.yaml`
- `neo_workshop.pgm`

That keeps the previous working map intact if `map_saver` fails.

## How This Differs From the Custom Path

- Custom path:
  - launch `rb1_neo_workshop_mapping.launch`
  - run `neo_workshop_auto_map.py`
  - uses repo-specific scripted motion

- Frontier path:
- launch `rb1_neo_workshop_frontier_mapping.launch`
- lets `explore_lite` choose frontier goals through `move_base`
- uses package-based exploration instead of custom motion scripting
- uses a dedicated frontier-only planning stack instead of the normal saved-map navigation stack
- uses a frontier goal guard to stop repeated retry of locally bad frontier regions

## Why The Frontier Path Has Its Own `move_base`

The normal navigation launch is tuned for fixed-map navigation after a saved map already exists.

For live gmapping exploration, that reuse caused planning failures because:

- the global planner was not configured for unknown-space planning
- the default frontier path reused the normal TEB-based move_base stack
- the frontier workflow needs a simpler and more forgiving planning setup while the map is still incomplete

The frontier launch now uses these dedicated files:

- `rb1_base_sim/rb1_base_gazebo/launch/rb1_neo_workshop_frontier_move_base.launch`
- `rb1_base_sim/rb1_base_gazebo/config/neo_workshop_frontier_move_base.yaml`
- `rb1_base_sim/rb1_base_gazebo/config/neo_workshop_frontier_costmap_common.yaml`
- `rb1_base_sim/rb1_base_gazebo/config/neo_workshop_frontier_global_costmap.yaml`
- `rb1_base_sim/rb1_base_gazebo/config/neo_workshop_frontier_local_costmap.yaml`
- `rb1_base_sim/rb1_base_gazebo/config/neo_workshop_frontier_base_local_planner.yaml`

This keeps normal navigation untouched while making manual 2D Nav Goals and `explore_lite` use the same exploration-specific planner.

The frontier-only stack is intentionally separate from normal navigation:

- simpler `TrajectoryPlannerROS` local planner
- frontier-only global/local costmap tuning
- frontier-only recovery and patience tuning
- frontier-only goal guard behavior

## Current Verified Frontier Behavior

- Frontier wiring is working:
  - `explore_lite` sends goals
  - `NavfnROS` produces a real global path
  - `move_base` publishes `cmd_vel`
- The corrected frontier RViz config now visualizes the active frontier plans and relevant costmap layers instead of stale TEB topics.
- The frontier goal guard exists and now blacklists only after repeated recovery on the same active goal.
- Repeated bad-corner reattack was reduced by the guard.
- The startup regression introduced by the goal guard was fixed.
- The robot geometry should continue to be modeled with `robot_radius`; the RB1 in this simulation is cylindrical.

## Current Verified Baselines

- Frontier global costmap baseline:
  - `inflation_radius: 0.33`
  - `cost_scaling_factor: 4.0`
- Frontier local costmap baseline:
  - `inflation_radius: 0.34`
  - `cost_scaling_factor: 3.0`
- Frontier local planner baseline includes:
  - `max_vel_x: 0.16`
  - `occdist_scale: 0.31`
  - `sim_time: 1.0`

## Current Remaining Issue

- The robot can start correctly and pass through the opening/passage.
- Post-pass wall-hugging improved in the tested failure mode.
- Current caution: do not yet claim full end-to-end perfect exploration in every long run.
- Future tuning, if needed, should stay focused on:
  - frontier global/local inflation behavior
  - frontier local planner wall-clearance behavior
  - long-run observed frontier behavior
- Do not spend time on explicit footprint-shape changes or polygon footprint ideas for this robot unless explicitly requested.
- Do not blindly retune inflation without runtime evidence.
- Prefer frontier-only minimal changes and avoid reopening earlier solved debugging branches unless new evidence clearly points back to them.

## Recommended Workflow

1. Install `ros-noetic-explore-lite` once.
2. Build the workspace with `catkin_make`.
3. Run `./tools/run_neo_workshop.sh frontier-mapping`.
4. Wait until exploration coverage looks sufficient.
5. Run `./tools/run_neo_workshop.sh frontier-save`.
6. Stop stale Gazebo/ROS processes if needed:

```bash
cd ~/catkin_ws/src
./tools/kill_gazebo_ros.sh
```

7. Run `./tools/run_neo_workshop.sh navigation`.

## Fallback

The existing custom automapping path remains available and unchanged:

```bash
cd ~/catkin_ws/src
./tools/run_neo_workshop.sh mapping
./tools/run_neo_workshop.sh automap
```
