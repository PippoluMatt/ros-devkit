# ROS2 Control Header

Target ROS2 Jazzy `hardware_interface::SystemInterface`.

## Source of Truth

Use `scripts/create_system_interface_header.py` to generate the header. Do not copy a full header template from this reference; the script owns the exact generated text.

Review the generated file for the invariants below.

## Rules

- Include a driver header only when the user provides `--driver-include` or the package already has a driver type to store.
- Keep the private storage vector names exactly `hw_positions_`, `hw_velocities_`, `hw_efforts_`, and `hw_commands_` so the later `.cpp` implementation can rely on them.
- Keep the Jazzy `on_init`, lifecycle, `read`, and `write` signatures compatible with `hardware_interface::SystemInterface`.
- Keep traditional include guards.
- Do not generate controller YAML, URDF `<ros2_control>`, transmission tags, or bringup files in v1.
