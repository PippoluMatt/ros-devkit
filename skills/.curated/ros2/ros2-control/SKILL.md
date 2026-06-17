---
name: ros2-control
description: Create and wire ROS2 Jazzy ros2_control hardware plugins that implement hardware_interface::SystemInterface. Use when creating or maintaining a ROS2 control hardware interface package, generating the hardware interface header skeleton, adding pluginlib export macros, creating plugin XML, wiring CMakeLists.txt and package.xml, or adding URDF/xacro ros2_control scaffolding for SystemInterface plugins.
---

# ROS2 Control

Use this skill for ROS2 Jazzy `hardware_interface::SystemInterface` plugin packages. Keep v1.5 limited to package-level SystemInterface work plus minimal URDF/xacro `<ros2_control>` scaffolding: header skeletons, plugin exports, plugin XML, CMake wiring, `package.xml` dependencies, and a direct top-level xacro control block.

Do not implement `ActuatorInterface`, `SensorInterface`, transmissions, controller YAML, or bringup launch files in v1.5. See [references/v2-backlog.md](references/v2-backlog.md).

## Workflow

1. Identify package name, namespace, class name, library target, driver include, and output paths.
2. Generate or update the header with `scripts/create_system_interface_header.py`.
3. Create a minimal `.cpp` skeleton with `scripts/create_system_interface_cpp_skeleton.py` only when explicitly requested.
4. Add the plugin export macro to the `.cpp` with `scripts/add_plugin_export.py`.
5. Create the plugin description XML with `scripts/create_plugin_xml.py`.
6. Wire build files with `scripts/add_ros2_control_cmake.py` and `scripts/add_ros2_control_package_xml.py`.
7. Add minimal URDF/xacro ros2_control scaffolding with `scripts/add_ros2_control_xacro.py` when the task includes robot description wiring.
8. Inspect diffs and run a package build.

Use scripts for deterministic repeated edits, then make only task-specific manual adjustments.

## Default Layout

Prefer this package layout unless the user or existing package requires different paths:

```text
include/<package_name>/<name>_hardware_interface.hpp
src/<name>_hardware_interface.cpp
<package_name>_hardware_interface.xml
```

Use traditional include guards for generated hardware headers. Use a plugin XML `<library path="...">` that matches the CMake library target name without the `lib` prefix.

## References

Load [references/ros2-control-hpp.md](references/ros2-control-hpp.md) before creating or reviewing hardware interface headers.

Load [references/ros2-control-plugin.md](references/ros2-control-plugin.md) before editing plugin exports or plugin XML.

Load [references/ros2-control-xacro.md](references/ros2-control-xacro.md) before adding URDF/xacro `<ros2_control>` scaffolding.

Load [references/ros2-control-build.md](references/ros2-control-build.md) before editing `CMakeLists.txt` or `package.xml`.

Load [references/ros2-control-cpp.md](references/ros2-control-cpp.md) only when the user asks for `.cpp` implementation guidance. The full C++ method body implementation is intentionally deferred in v1.

## Checks

- Keep generated names consistent across header, source, plugin XML, CMake target, and `PLUGINLIB_EXPORT_CLASS`.
- Use `type="system"` for xacro `<ros2_control>` scaffolds; `SystemInterface` covers combined sensor and actuator hardware.
- Keep driver-specific members in the private placeholder unless the user provides driver details.
- Include `hardware_interface/system_interface.hpp`, `hardware_interface/types/hardware_interface_return_values.hpp`, `rclcpp/macros.hpp`, and lifecycle/time headers needed by the declarations.
- Make plugin export insertion idempotent.
- Build the package after edits when a ROS2 environment is available.
