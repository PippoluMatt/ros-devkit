---
name: ros2-control-pluginize
description: Pluginize existing ROS2 ros2_control controller and hardware interface packages. Use when a package ending `_controllers` or `_hardware` must gain pluginlib XML, PLUGINLIB_EXPORT_CLASS, package.xml dependencies, and CMakeLists.txt wiring for controller_interface or hardware_interface plugins.
---

# ROS2 Control Pluginize

Convert an existing ros2_control controller or hardware interface package into a loadable pluginlib plugin, or diagnose existing pluginlib wiring.

## CLI

Prefer the `ros-devkit ros2-control-pluginize` CLI. It dispatches to the installed skill implementation; run `ros-devkit doctor` if the command or configured skill root is missing. Use scripts directly only when developing or debugging the CLI dispatch.

```bash
ros-devkit ros2-control-pluginize --check <package_dir>
ros-devkit ros2-control-pluginize --pluginize <package_dir>
```

Modes are workflow selectors:

- `--check <package_dir>`: inspect one existing `_hardware` or `_controllers` package and report `ERROR`, `WARN`, and `INFO` findings. It never edits files. Exit non-zero only when `ERROR` findings exist.
- `--pluginize <package_dir>`: add missing pluginlib XML, `PLUGINLIB_EXPORT_CLASS`, `package.xml` dependencies, and `CMakeLists.txt` wiring, then run `--check`. It refuses ambiguous packages instead of guessing when multiple plugin classes, multiple plugin XML files, or multiple CMake library targets exist.

## Pluginize Workflow

Use `--pluginize` when the user asks to convert, fix, add, or repair ros2_control pluginlib wiring.

1. Run `ros-devkit ros2-control-pluginize --pluginize <package_dir>`.
2. Inspect the changed files. Keep the conversion surgical: do not rename the package, move the class, or rewrite unrelated build structure.
3. If the command reports ambiguity, inspect the listed candidates and ask the user which class or target is intended.
4. Run `git diff --check`.
5. Run `colcon build --packages-select <package_name>` when a ROS2 environment is available.

Completion criterion: `--pluginize` finishes successfully, its follow-up `--check` has no `ERROR` findings, and available workspace validation passes.

## Check Workflow

Use `--check` for requests to inspect, diagnose, validate, or review an existing pluginized package.

1. Run `ros-devkit ros2-control-pluginize --check <package_dir>`.
2. Treat `ERROR` findings as blockers, `WARN` findings as design or readiness concerns, and `INFO` findings as package facts.
3. Do not edit files from check output unless the user explicitly asks for fixes.

## Branch Rules

- `_hardware` packages export `hardware_interface::SystemInterface` and depend on `hardware_interface` plus `pluginlib`.
- `_controllers` packages export `controller_interface::ChainableControllerInterface` or the existing `controller_interface::ControllerInterface` base and depend on `controller_interface` plus `pluginlib`.
- Do not silently convert a non-chainable controller to chainable. Export the existing base unless the user asks for an inheritance change.
- The source export macro must be outside the implementation namespace and appear exactly once for the plugin class.
- Plugin XML `<library path>` must equal the CMake library target.
- Plugin XML `type` and `base_class_type` must match the `PLUGINLIB_EXPORT_CLASS(...)` arguments.
- `pluginlib_export_plugin_description_file(...)` must use `hardware_interface` for hardware packages and `controller_interface` for controller packages.
- Preserve the package's existing CMake dependency style. Use `THIS_PACKAGE_INCLUDE_DEPENDS` or `ament_target_dependencies(...)` when the package already does.
