---
name: ros2-description-scaffold
description: Scaffold and validate ROS2 URDF/xacro description packages using the standard modular structure. Creates packages with `ros2 pkg create`, removes unused src/include boilerplate and generated CMake lint placeholder boilerplate, adds templated xacro files (main, materials, robot body, per-sensor), and cross-checks existing packages for compliance. Use when creating a new robot description package, scaffolding URDF/xacro files, or validating an existing description package structure.
---

# ROS2 Description Scaffold

Scaffold a `<name>_description` package with the standard modular xacro structure, validate existing packages against it, and split monolithic xacro files into the standard layout.

## Invocation Modes

Treat skill flags as workflow selectors:

```bash
$ros2-description-scaffold --verify [package_path]
$ros2-description-scaffold --create <robot_name> --sensors camera,lidar --destination-directory ~/ros2_ws/src
$ros2-description-scaffold --create [existing_package_path]
$ros2-description-scaffold --split [package_path]
```

Use `scripts/description_scaffold.py` as the deterministic implementation:

```bash
python3 scripts/description_scaffold.py --verify [package_path]
python3 scripts/description_scaffold.py --create <robot_name> --sensors camera,lidar --destination-directory ~/ros2_ws/src
python3 scripts/description_scaffold.py --create [existing_package_path]
python3 scripts/description_scaffold.py --split [package_path]
```

Modes:

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

For new packages, prefer the existing `ros2 pkg create` workflow through `scripts/description_scaffold.py --create` or `scripts/scaffold.py`:

```bash
python3 scripts/description_scaffold.py --create <robot_name> --sensors camera,lidar --destination-directory ~/ros2_ws/src
python3 scripts/scaffold.py <robot_name> --sensors camera,lidar --destination-directory ~/ros2_ws/src
```

Prerequisite: source ROS 2 first (`source /opt/ros/<distro>/setup.bash`).

The script performs:

1. `ros2 pkg create <name>_description --build-type ament_cmake --dependencies urdf xacro`
2. Remove `src/` and `include/` directories (unused in description packages)
3. Remove the generated dependency placeholder and ament lint block from `CMakeLists.txt`
4. Add `install(DIRECTORY urdf meshes rviz ...)` to `CMakeLists.txt`
5. Create `urdf/` files from templates (materials.xacro first, then sensors, then robot body)
6. Create `rviz/<name>.rviz` and `meshes/` directory

When `--create` receives an existing package path, or when no target is provided and exactly one `*_description` package is discovered under the current project, it repairs only missing minimal structure:

- Create missing `urdf/`, `meshes/`, and `rviz/` directories
- Create missing `CMakeLists.txt` and `package.xml`
- Create `urdf/main.xacro` only when neither `main.xacro` nor `main.urdf.xacro` exists
- Create missing `materials.xacro`, `<name>.urdf.xacro`, requested sensor files, and `rviz/<name>.rviz`
- Never overwrite existing files

After creation, customize links/joints in `<name>.urdf.xacro`, adjust sensor positions, and enable Gazebo plugins in `<sensor>.xacro`.

Load the `ros2-cmakelists` skill for further CMakeLists.txt edits. Load the `ros2-sensor` skill for sensor interface details. Load the `ros2-control` skill when adding ros2_control hardware.

## Verify Workflow

Run `--verify` or `scripts/validate.py` to check an existing package:

```bash
python3 scripts/description_scaffold.py --verify [package_path]
python3 scripts/validate.py [package_path]
```

Checks:

- Required files exist (CMakeLists.txt, package.xml, urdf/main.xacro or urdf/main.urdf.xacro, urdf/\<name>.urdf.xacro)
- Recommended files present (materials.xacro, rviz/\*.rviz)
- main.xacro includes materials.xacro first
- All .xacro files in urdf/ are included in main.xacro
- No broken include references in main.xacro
- package.xml lists urdf and xacro dependencies
- CMakeLists.txt uses ament_cmake
- CMakeLists.txt installs each present package resource directory from `urdf`, `meshes`, `rviz`, `config`, and `launch`
- CMakeLists.txt does not contain the generated `ros2 pkg create` dependency placeholder and ament lint block
- All .xacro files are valid XML

Severity rules:

- `ERROR`: missing `CMakeLists.txt`, missing `package.xml`, missing both `main.xacro` and `main.urdf.xacro`, missing canonical `urdf/<name>.urdf.xacro`, invalid XML, ROS1 catkin CMake usage, or broken required include references.
- `WARN`: missing recommended files, using `main.urdf.xacro` instead of standard `main.xacro`, missing included `<sensor>.xacro`, `sensors.xacro` aggregate file present, missing dependencies, missing install rules for present package resource directories, generated CMake dependency/lint placeholder block still present, or other non-fatal structure drift.
- `INFO`: package facts and successful checks.

Derive `<name>` from the package name `<name>_description`.

## Split Workflow

Run `--split` for an existing non-empty package where sensors, links, joints, materials, macros, or related definitions live in one large xacro file:

```bash
python3 scripts/description_scaffold.py --split <package_path>
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
