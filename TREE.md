# Important Tree

```text
~/catkin_ws/src/
|- AGENTS.md
|- PROJECT_STATE.md
|- TREE.md
|- LINKS.md
|- .codex/
|  `- config.toml
|- docs/
|  |- neo_workshop_workflow.md
|  `- neo_workshop_frontier_mapping.md  (preserved, not the current active operator path)
|- tools/
|  |- kill_gazebo_ros.sh
|  |- run_neo_workshop.sh
|  |- save_neo_workshop_map.sh
|  `- verify_neo_workshop.sh
|- rb1_base_sim/
|  `- rb1_base_gazebo/
|     |- package.xml
|     |- CMakeLists.txt
|     |- README_neo_workshop_mapping.md
|     |- config/
|     |  |- neo_workshop_joy.yaml
|     |  |- neo_workshop_f710_xinput_twist_joy.yaml
|     |  `- neo_workshop_f710_xinput_teleop.yaml  (legacy, not the current active manual path)
|     |- launch/
|     |  |- rb1_base_gazebo.launch
|     |  |- rb1_neo_workshop_manual_mapping.launch  (current active operator path)
|     |  |- rb1_neo_workshop_mapping.launch
|     |  |- rb1_neo_workshop_navigation.launch
|     |  |- rb1_neo_workshop_frontier_mapping.launch  (preserved, not the current active operator path)
|     |  `- rb1navindemoworl.launch
|     |- scripts/
|     |  |- manual_speed_selector.py
|     |  `- neo_workshop_auto_map.py  (preserved, do not modify unless explicitly requested)
|     |- rviz/
|     |  |- rb1_base.rviz
|     |  |- rb1_neo_workshop_frontier_mapping.rviz  (preserved, not the current active operator path)
|     |  `- rb1_neo_workshop_navigation.rviz
|     `- worlds/
|        |- demo.world
|        `- neo_workshop.world
`- rb1_base_common/
   `- rb1_base_localization/
      |- package.xml
      |- CMakeLists.txt
      |- launch/
      |  |- amcl.launch
      |  |- gmapping.launch
      |  |- map_saver.launch
      |  `- map_server.launch
      |- maps/
      |  |- demo/
      |  |- empty/
      |  |- neo_workshop/
      |  |  |- neo_workshop.pgm
      |  |  `- neo_workshop.yaml
      |  |- obstacle/
      |  |- rbk_warehouse/
      |  |- robotnik/
      |  `- willow_garage/
      `- scripts/
         `- amcl_resample.py
```

Current active operator path: `rb1_neo_workshop_manual_mapping.launch` + `neo_workshop_joy.yaml` + `neo_workshop_f710_xinput_twist_joy.yaml` + `manual_speed_selector.py` + `tools/save_neo_workshop_map.sh`
