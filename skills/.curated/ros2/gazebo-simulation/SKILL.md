---
name: gazebo-simulation
description: Set up and diagnose ROS2 Gazebo simulation wiring. Use when the user asks to diagnose Gazebo, Ignition, or gz sim configuration, check URDF/xacro inertial and collision tags, validate ros_gz_bridge gazebo_bridge.yaml under a bringup config folder, inspect ros_gz_sim launch wiring, or explicitly asks to set up or prepare Gazebo simulation scaffolding.
---

# Gazebo Simulation

Set up the minimal Gazebo files an agent needs to continue the simulation work, and diagnose existing ROS2 Gazebo simulation wiring without silently editing files.

## CLI

Prefer the `ros-devkit gazebo-simulation` CLI. It dispatches to the installed skill implementation; run `ros-devkit doctor` if the command or configured skill root is missing. Use scripts directly only when developing or debugging the CLI dispatch.

```bash
ros-devkit gazebo-simulation --diagnose [project_or_package_path]
ros-devkit gazebo-simulation --setup [project_or_package_path]
ros-devkit gazebo-simulation --setup [project_or_package_path] --robot-name my_robot --world-name test_world
```

Modes are workflow selectors:

- `--diagnose [path]`: inspect the description and bringup packages and report `ERROR`, `WARN`, and `INFO` findings. If `path` is omitted, discover packages under the current project. Exit non-zero only when `ERROR` findings exist. Do not edit files unless the user explicitly asks for fixes after diagnosis.
- `--setup [path]`: create only missing Gazebo scaffolding in discovered packages: `<name>_gazebo.xacro`, `config/gazebo_bridge.yaml`, `worlds/test_world.sdf`, `launch/gazebo.launch.xml`, package dependencies, and CMake share installs. Never overwrite existing files.

## Setup Workflow

Use setup only when the user explicitly requests setup or preparation, for example `$gazebo-simulation --setup`, "setup Gazebo", or "prepare the description repo for Gazebo".

1. Identify the target project, `<name>_description` package, and `<name>_bringup` package. Stop and list candidates when discovery is ambiguous.
2. Run `ros-devkit gazebo-simulation --setup [path]`.
3. Inspect the created or updated files. Keep user-authored launch files intact unless the user asked to adapt them.
4. Run `ros-devkit gazebo-simulation --diagnose [path]`.

Completion criterion: the setup command reports created or already-present Gazebo scaffolding, and a follow-up diagnose run has no `ERROR` findings caused by the scaffold itself.

## Diagnose Workflow

Use diagnose for requests to check, inspect, validate, debug, or find errors in an existing Gazebo simulation setup.

1. Run `ros-devkit gazebo-simulation --diagnose [path]`.
2. Treat missing inertial or collision tags as `ERROR` for every `<link>` except links named `base_footprint` or ending in `footprint`.
3. Check the Gazebo xacro file at `urdf/<name>_gazebo.xacro`: it should exist, contain at least one `<gazebo>` element, and be included by the description entry point.
4. Check the bringup package: a valid bringup package has `package.xml`, `CMakeLists.txt`, `launch/`, and `CMakeLists.txt` installs `launch/` to `share/${PROJECT_NAME}`.
5. Check the bridge at `<name>_bringup/config/gazebo_bridge.yaml`. If it is absent, report `WARN`. If present, validate its list structure, required keys, directions, and common `/clock`, `/joint_states`, `/tf`, and `/cmd_vel` mappings.
6. Check launch files for `ros_gz_sim` `gz_sim.launch.py`, `ros_gz_sim create -topic robot_description`, and `ros_gz_bridge parameter_bridge` with `config_file`.

Completion criterion: all `ERROR` findings are fixed or reported as blockers. Treat `WARN` findings as simulation-readiness gaps and `INFO` findings as package facts.

## Launch Adaptation

Load [references/templates.md](references/templates.md) when creating or adapting Gazebo launch files, bridge YAML, world files, or `<name>_gazebo.xacro`. For existing launch files:

- Prefer XML launch for the standard static Gazebo include and bridge nodes.
- Preserve the repo's existing launch style when it already uses Python launch files.
- Add the bridge config through a `gazebo_config_path` argument or variable instead of hard-coding a second path in the bridge node.

Load the `ros2-launch` skill before nontrivial launch rewrites. Load `ros2-cmakelists` before broader CMake changes beyond installing `launch`, `config`, or `worlds`.

## Key Rules

- The bridge file name is exactly `gazebo_bridge.yaml`.
- Missing bridge is `WARN`, not `ERROR`; malformed bridge entries are `ERROR`.
- `GZ_TO_ROS` is expected for `/clock`, `/joint_states`, and `/tf`; `ROS_TO_GZ` is expected for `/cmd_vel`.
- Do not auto-center, rewrite robot geometry, or invent physical inertias during diagnose. Report missing physics tags and let the user choose whether to scaffold or calculate real values.
