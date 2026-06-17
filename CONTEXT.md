# ROS2 Devkit

A curated collection of installable Codex skills for ROS2 development.

## Language

**Skill**:
A self-contained Codex extension that bundles instructions, references, and scripts for a specific ROS2 development task.

**Curated skill**:
A production-ready skill stored under `skills/.curated/` and available for installation.
_Avoid_: Stable skill, released skill

**Namespace**:
A grouping prefix under `.curated/` (e.g., `ros2/`) that organizes skills by domain.

**Agent skill root**:
The directory where an AI agent discovers installed skills for a namespace.
_Avoid_: Agent root, skill install folder

**Namespace root**:
The installed directory for one namespace beneath an agent skill root.
_Avoid_: Namespace folder, installed skill folder

**Agent target**:
A supported AI-agent destination selected during installation to determine the agent skill root.
_Avoid_: Agent type, agent kind

**Shared skill script**:
A reusable script stored at a namespace level for use by multiple curated skills in that namespace.
_Avoid_: Global script, common script

**Skill-local script**:
A script owned by one curated skill because its behavior is specific to that skill.
_Avoid_: Private script, per-skill script

**Launch file**:
An XML or Python file that starts ROS2 nodes and loads parameter files. Not YAML-based.
_Avoid_: Launch script, startup file

**Param file**:
A YAML file that defines ROS2 node parameters, loaded by launch files or the `--ros-args --params-file` CLI flag.
_Avoid_: Config file, settings file

**Build type**:
The ROS2 package build system selected during package creation, such as `ament_cmake` or `ament_python`.
_Avoid_: Package kind, project type

**Package type**:
The role of a ROS2 package, such as C++ node, Python node, description package, message package, or hardware interface.
_Avoid_: Build type

**Base image**:
An OSRF-published Docker image (e.g. `osrf/ros:jazzy-ros-base`, `osrf/ros:humble-desktop`) that all custom ROS 2 Dockerfiles use as the `FROM` layer. Variants differ in what is pre-installed: `-ros-base` is the minimal core, `-desktop` adds `rviz`/`rqt`/`gazebo` and related tools, `-desktop-full` adds more.
_Avoid_: ROS image, upstream image

**Overlay (workspace)**:
A colcon workspace layered on top of `/opt/ros/<distro>` to add custom packages. Built with `colcon build` after its `src/` is populated (typically by `vcs import` from a `.repos` file). Sourced at runtime to make its packages visible alongside the base install.
_Avoid_: Custom workspace, user workspace

**`overlay.repos` file**:
A vcs-tool YAML file that lists git repositories to clone into an overlay workspace's `src/`. Read by `vcs import`. The Dockerfile in the `ros2-dockerfile` skill fetches this file from a URL passed via the `OVERLAY_REPOS_URL` build-arg.
_Avoid_: repos file, rosdistro file

## Example Dialogue

> **Dev**: I need a skill that writes a CMakeLists.txt for a hardware interface package.
> **Domain expert**: That's the `cmakelists` curated skill under the `ros2` namespace. It uses shared skill scripts for reusable CMakeLists.txt transformations and skill-local scripts for its command entry points.
> **Dev**: And if I want to set up a launch file that loads a param file?
> **Domain expert**: Use the `launch` skill. It handles XML launch files, Python launch files, and param YAML files through separate reference docs — pick the one you need.
> **Dev**: Is debugging covered?
> **Domain expert**: The `debug-rqt` skill covers rqt-based debugging — rqt_graph, rqt_console, rqt_plot, and related tools.
