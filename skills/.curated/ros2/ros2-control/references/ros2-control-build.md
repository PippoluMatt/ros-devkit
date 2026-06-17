# ROS2 Control Build Wiring

Use `ament_cmake` and pluginlib export wiring for SystemInterface plugin libraries.

## CMakeLists.txt

Use `scripts/add_ros2_control_cmake.py` for the repeated mutation; the script owns the exact generated block.

Review that the result has:

- `find_package(...)` calls for `hardware_interface`, `pluginlib`, `rclcpp`, and `rclcpp_lifecycle`.
- A shared library target for the hardware interface source.
- Public include directories for build and install interfaces.
- `ament_target_dependencies(...)` for the ROS2 control dependencies.
- `pluginlib_export_plugin_description_file(hardware_interface <plugin_xml>)`.
- Header and target install rules.
- `ament_export_targets(...)` and `ament_export_dependencies(...)`.

## package.xml

Use `scripts/add_ros2_control_package_xml.py` for the repeated mutation.

Review that dependencies include `hardware_interface`, `pluginlib`, `rclcpp`, and `rclcpp_lifecycle`, and that the export block declares `ament_cmake` as the build type.
