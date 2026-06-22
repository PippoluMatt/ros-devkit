---
name: ros2-cmakelists
description: Create, fix, and normalize ROS2 CMakeLists.txt files for C++ nodes, Python nodes, message packages, bringup packages, ros2_control SystemInterface plugin libraries, hardware interfaces, include/ headers, share-directory installation, and generated ament lint placeholder cleanup. Use when editing CMakeLists.txt, adding find_package/install/include_directories rules, adding pluginlib/hardware_interface build wiring, removing default ROS2 build boilerplate, or generating build configuration with deterministic scripts.
---

# ROS2 CMakeLists.txt

Use the shared CLI at `../scripts/cmake_lib/` for deterministic CMakeLists.txt mutations:

- `python3 ../scripts/cmake_lib/__main__.py remove-default-lint-block <CMakeLists.txt>`: always run when editing a ROS2 CMakeLists.txt. Remove the generated placeholder dependency comment and `if(BUILD_TESTING)` lint block.
- `python3 ../scripts/cmake_lib/__main__.py add-install-share-directories <CMakeLists.txt> <dir> [<dir> ...]`: install bringup/message package directories into `share/${PROJECT_NAME}` with directory entries side by side in a single `install(DIRECTORY ...)` block.
- `python3 ../scripts/cmake_lib/__main__.py add-include-directories <CMakeLists.txt>`: add `include_directories(include)` after the package `find_package(...)` block when the package has headers in `include/`.

These subcommands live in the shared `cmake_lib` package under `../scripts/`. Prefer running them over rewriting these transformations manually. After script use, inspect the diff and make only task-specific adjustments.

When CMake wiring is for a new `ros2_control` `hardware_interface::SystemInterface` hardware package, load the `ros2-control` skill and use its `scripts/add_ros2_control_cmake.py` script instead of duplicating generated package wiring here. When an existing `_controllers` or `_hardware` package needs pluginlib conversion, load `ros2-control-pluginize` instead.

Load the `ros2-cpp-node` shared node module when build rules are for node executables, components, lifecycle-compatible helpers, or packages whose dependencies are determined by node interfaces. Keep build-file generation in this skill and node behavior decisions in the shared node module.
