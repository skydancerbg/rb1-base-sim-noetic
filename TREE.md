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
|  `- neo_workshop_workflow.md
|- tools/
|  |- kill_gazebo_ros.sh
|  |- run_neo_workshop.sh
|  `- verify_neo_workshop.sh
|- rb1_base_sim/
|  `- rb1_base_gazebo/
|     |- package.xml
|     |- CMakeLists.txt
|     |- README_neo_workshop_mapping.md
|     |- launch/
|     |  |- rb1_base_gazebo.launch
|     |  |- rb1_neo_workshop_mapping.launch
|     |  |- rb1_neo_workshop_navigation.launch
|     |  `- rb1navindemoworl.launch
|     |- scripts/
|     |  `- neo_workshop_auto_map.py
|     |- rviz/
|     |  |- rb1_base.rviz
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
