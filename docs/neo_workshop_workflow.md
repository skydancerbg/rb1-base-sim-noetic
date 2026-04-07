# neo_workshop Workflow

This repository includes helper scripts under `tools/` so you do not need to retype the long ROS setup and launch commands each time.

# Workflow Order

1. Build the workspace.
2. Launch the neo_workshop mapping world.
3. Run the automap script to create or recreate the map.
4. Verify that the saved map files exist.
5. Launch neo_workshop navigation using the saved map.
6. Launch the original demo navigation when you want the baseline demo world instead.

# Command Shortcuts

Build the workspace:

```bash
tools/run_neo_workshop.sh build
```

Launch mapping:

```bash
tools/run_neo_workshop.sh mapping
```

Run the automap script:

```bash
tools/run_neo_workshop.sh automap
```

Check the saved map files:

```bash
tools/run_neo_workshop.sh check-map
```

Launch neo_workshop navigation:

```bash
tools/run_neo_workshop.sh navigation
```

Launch the original demo navigation:

```bash
tools/run_neo_workshop.sh demo
```

Clean stale Gazebo and ROS GUI processes before switching worlds:

```bash
tools/kill_gazebo_ros.sh
```

# What Each Step Does

- Mapping launch:
- Starts `rb1_neo_workshop_mapping.launch`
- Brings up the neo_workshop world with gmapping
- Does not auto-run `neo_workshop_auto_map.py` unless `launch_auto_map:=true` is explicitly passed

- Automap script:
- Runs `neo_workshop_auto_map.py`
- Uses the real scan topic `/robot/front_laser/scan`
- Drives the robot and saves the map into `rb1_base_localization/maps/neo_workshop/`

- Navigation launch:
- Starts `rb1_neo_workshop_navigation.launch`
- Loads `neo_workshop.yaml`
- Starts map server, AMCL, move_base, and the matching RViz config `rb1_neo_workshop_navigation.rviz`

- Demo launch:
- Starts `rb1navindemoworl.launch`
- Uses the original demo setup and should remain unchanged unless explicitly requested

# Saved Map Location

- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.yaml`
- `~/catkin_ws/src/rb1_base_common/rb1_base_localization/maps/neo_workshop/neo_workshop.pgm`

# Verification

The helper verifier supports environment, runtime, and file checks:

```bash
tools/verify_neo_workshop.sh env
tools/verify_neo_workshop.sh map-files
tools/verify_neo_workshop.sh mapping
tools/verify_neo_workshop.sh navigation
tools/verify_neo_workshop.sh all
```

Use `mapping` while the mapping launch is already running. Use `navigation` while the navigation launch is already running.
