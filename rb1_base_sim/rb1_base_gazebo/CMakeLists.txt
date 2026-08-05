cmake_minimum_required(VERSION 2.8.3)
project(rb1_base_gazebo)


find_package(catkin REQUIRED COMPONENTS
  gazebo_ros
  gazebo_ros_control
  diff_drive_controller
)



catkin_package()


include_directories(
  ${catkin_INCLUDE_DIRS}
)

install(DIRECTORY launch
        DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})

install(DIRECTORY worlds
        DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})

install(DIRECTORY rviz
        DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})

install(DIRECTORY config
        DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})

install(PROGRAMS
        scripts/manual_speed_selector.py
        scripts/neo_workshop_auto_map.py
        scripts/neo_workshop_frontier_goal_guard.py
        scripts/sim_battery_model.py
        DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
