---
name: ros2-cmakelists
description: Create, fix, and normalize ROS2 CMakeLists.txt files for C++ nodes, Python nodes, message packages, bringup packages, ros2_control SystemInterface plugin libraries, hardware interfaces, include/ headers, share-directory installation, and generated ament lint placeholder cleanup. Use when editing CMakeLists.txt, adding find_package/install/include_directories rules, adding pluginlib/hardware_interface build wiring, removing default ROS2 build boilerplate, or generating build configuration with deterministic scripts.
---

# ROS2 CMakeLists.txt

Use deterministic scripts for repeated CMakeLists.txt mutations:

- `scripts/remove_default_lint_block.py <CMakeLists.txt>`: always run when editing a ROS2 CMakeLists.txt. Remove the generated placeholder dependency comment and `if(BUILD_TESTING)` lint block.
- `scripts/install_share_directories.py <CMakeLists.txt> <dir> [<dir> ...]`: install bringup/message package directories into `share/${PROJECT_NAME}` with directory entries side by side in a single `install(DIRECTORY ...)` block.
- `scripts/add_include_directories.py <CMakeLists.txt>`: add `include_directories(include)` after the package `find_package(...)` block when the package has headers in `include/`.

These skill-local scripts are compatibility wrappers around the namespace-level shared implementation at `../scripts/cmake.py`. Use the shared implementation for new reusable CMakeLists.txt transformations instead of duplicating helper code inside a skill.

Prefer running the scripts over rewriting these transformations manually. After script use, inspect the diff and make only task-specific adjustments.

When CMake wiring is for a `ros2_control` `hardware_interface::SystemInterface` plugin library, load the `ros2-control` skill and use its `scripts/add_ros2_control_cmake.py` script instead of duplicating the pluginlib/export recipe here. That skill also owns `package.xml` dependency and export wiring when the task needs the complete ros2_control package setup.

Load the `ros2-cpp-node` shared node module when build rules are for node executables, components, lifecycle-compatible helpers, or packages whose dependencies are determined by node interfaces. Keep build-file generation in this skill and node behavior decisions in the shared node module.
