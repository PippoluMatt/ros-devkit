---
name: ros2-description-scaffold
description: Create, validate, and split ROS2 URDF/xacro description packages. Use when creating a `<name>_description` package, checking an existing description package, or splitting monolithic xacro into the standard modular layout.
---

# ROS2 Description Scaffold

Create a `<name>_description` package with the standard modular xacro structure, validate existing packages against it, and split monolithic xacro files into the standard layout.

## CLI

Prefer the `ros-devkit description-scaffold` CLI. It dispatches to the installed skill implementation; run `ros-devkit doctor` if the command or configured skill root is missing. Use scripts directly only when developing or debugging the CLI dispatch.

```bash
ros-devkit description-scaffold --verify [package_path]
ros-devkit description-scaffold --create <robot_name> --sensors camera,lidar --destination-directory ~/ros2_ws/src
ros-devkit description-scaffold --create [existing_package_path]
ros-devkit description-scaffold --split [package_path]
```

Modes are workflow selectors:

- `--verify [package_path]`: inspect a package and report `ERROR`, `WARN`, and `INFO` findings. If `package_path` is omitted, discover exactly one `*_description` package under the current project; stop with `ERROR` and list candidates when multiple matches exist. Exit non-zero only when `ERROR` findings exist. Never edit files, run repair workflows, or start implementation from verification output unless the user explicitly asks for fixes.
- `--create <robot_name>`: create a new package from a robot name.
- `--create [existing_package_path]`: repair an existing package by creating only missing minimal files/directories without overwriting existing files. If the path is omitted, discover exactly one `*_description` package under the current project; stop with `ERROR` and list candidates when multiple matches exist.
- `--split [package_path]`: rename the monolithic source file to `<original>.unsplit.xacro`, then create active modular files. If `package_path` is omitted, discover exactly one `*_description` package under the current project; stop with `ERROR` and list candidates when multiple matches exist. The new `main.xacro` includes `materials.xacro`, one `<sensor>.xacro` per detected sensor, and `<name>.urdf.xacro`; it must not include the `.unsplit.xacro` backup.

## Package Structure

```
<name>_description/
├── meshes/                    # Optional: CAD meshes
├── rviz/
│   └── <name>.rviz            # Recommended: RViz config
├── urdf/
│   ├── main.xacro             # Mandatory: entry point (includes only)
│   ├── <name>.urdf.xacro      # Mandatory: robot body definition
│   ├── materials.xacro        # Recommended: color/material definitions
│   └── <sensor>.xacro         # Recommended: one file per sensor
├── CMakeLists.txt             # Mandatory
└── package.xml                # Mandatory
```

## Create Workflow

Source ROS 2 first (`source /opt/ros/<distro>/setup.bash`), then create through the CLI:

```bash
ros-devkit description-scaffold --create <robot_name> --sensors camera,lidar --destination-directory ~/ros2_ws/src
```

For a new package, the CLI uses `ros2 pkg create <name>_description --build-type ament_cmake --dependencies urdf xacro`, removes unused generated boilerplate, and adds the standard `urdf`, `meshes`, and `rviz` resources. When `--create` receives an existing package path, it repairs only missing minimal files and never overwrites existing files.

After creation, customize links/joints in `<name>.urdf.xacro`, adjust sensor positions, and enable Gazebo plugins in `<sensor>.xacro`.

Load the `ros2-cmakelists` skill for further CMakeLists.txt edits. Load the `ros2-sensor` skill for sensor interface details. Load the `ros2-control` skill when adding ros2_control hardware.

## Verify Workflow

Run `--verify` to check an existing package:

```bash
ros-devkit description-scaffold --verify [package_path]
```

Completion criterion: all `ERROR` findings are fixed or reported as blockers. Treat `WARN` findings as structure improvements and `INFO` findings as package facts.

## Split Workflow

Run `--split` for an existing non-empty package where sensors, links, joints, materials, macros, or related definitions live in one large xacro file:

```bash
ros-devkit description-scaffold --split <package_path>
```

The split workflow is conservative:

- Auto-detect the source only when there is one clear monolithic `.xacro` candidate.
- Use `--source <file>` when multiple candidates exist.
- Rename the source to `<original>.unsplit.xacro`.
- Write a new active `main.xacro` that references `materials.xacro`, detected sensor files, and `<name>.urdf.xacro`.
- Create one `<sensor>.xacro` file per detected sensor block.
- Keep ambiguous or non-sensor definitions in `<name>.urdf.xacro`.
- Refuse to overwrite existing modular output files.

## Key Rules

- **Materials first**: `materials.xacro` must be the first include in `main.xacro`
- **Modular**: each sensor in its own `.xacro` file (link, joint, optional Gazebo plugin)
- **Entry point only**: `main.xacro` contains only `<xacro:include>`, never definitions
- **Naming**: robot body file is `<name>.urdf.xacro`; package is `<name>_description`

## File Templates

Load [references/file-templates.md](references/file-templates.md) when creating or customizing individual files: main.xacro, materials.xacro, robot body, sensor xacros (camera, lidar, IMU, generic), expected CMakeLists.txt, package.xml, and RViz config.
