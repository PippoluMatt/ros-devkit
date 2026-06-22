---
name: ros2-control
description: Scaffold new ROS2 Jazzy ros2_control hardware packages that implement hardware_interface::SystemInterface. Use when creating a new SystemInterface header/source skeleton, generated plugin files, build wiring, package.xml dependencies, or minimal URDF/xacro ros2_control scaffolding. Use ros2-control-pluginize for existing `_controllers` or `_hardware` packages that need pluginlib conversion.
---

# ROS2 Control

Use this skill to scaffold new ROS2 Jazzy `hardware_interface::SystemInterface` hardware packages plus minimal URDF/xacro `<ros2_control>` scaffolding.

For existing packages ending `_controllers` or `_hardware` that already contain the implementation and need pluginlib XML, export macros, `package.xml`, and `CMakeLists.txt` wiring, use `ros2-control-pluginize` instead.

Keep v1.5 limited to new package-level SystemInterface scaffolding and a direct top-level xacro control block.

Do not implement `ActuatorInterface`, `SensorInterface`, transmissions, controller YAML, or bringup launch files in v1.5. See [references/v2-backlog.md](references/v2-backlog.md).

## Workflow

1. Identify package name, namespace, class name, library target, driver include, and output paths for the new hardware package.
2. Generate the header with `scripts/create_system_interface_header.py`.
3. Create a minimal `.cpp` skeleton with `scripts/create_system_interface_cpp_skeleton.py` only when explicitly requested.
4. Generate the SystemInterface plugin export and XML with `scripts/add_plugin_export.py` and `scripts/create_plugin_xml.py`.
5. Wire the new package build files with `scripts/add_ros2_control_cmake.py` and `scripts/add_ros2_control_package_xml.py`.
6. Add minimal URDF/xacro ros2_control scaffolding with `scripts/add_ros2_control_xacro.py` when the task includes robot description wiring.
7. Inspect diffs and run a package build.

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

Load [references/ros2-control-plugin.md](references/ros2-control-plugin.md) before generating new package plugin exports or plugin XML.

Load [references/ros2-control-xacro.md](references/ros2-control-xacro.md) before adding URDF/xacro `<ros2_control>` scaffolding.

Load [references/ros2-control-build.md](references/ros2-control-build.md) before generating new package `CMakeLists.txt` or `package.xml` wiring.

Load [references/ros2-control-cpp.md](references/ros2-control-cpp.md) only when the user asks for `.cpp` implementation guidance. The full C++ method body implementation is intentionally deferred in v1.

## Checks

- Keep generated names consistent across header, source, plugin XML, CMake target, and `PLUGINLIB_EXPORT_CLASS`.
- Use `type="system"` for xacro `<ros2_control>` scaffolds; `SystemInterface` covers combined sensor and actuator hardware.
- Keep driver-specific members in the private placeholder unless the user provides driver details.
- Include `hardware_interface/system_interface.hpp`, `hardware_interface/types/hardware_interface_return_values.hpp`, `rclcpp/macros.hpp`, and lifecycle/time headers needed by the declarations.
- Defer existing-package plugin conversion to `ros2-control-pluginize`.
- Build the package after edits when a ROS2 environment is available.
