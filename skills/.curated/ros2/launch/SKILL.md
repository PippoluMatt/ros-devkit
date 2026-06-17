---
name: ros2-launch
description: Create, edit, and debug ROS2 launch files in XML or Python. Use when working with launch files under name_bringup/launch, choosing between .launch.xml and .launch.py, wiring nodes/includes/arguments/remappings/parameters into launch actions, or validating launch behavior with ros2 launch.
---

# ROS2 Launch Files

## Workflow

1. Inspect the package layout before creating or editing files.
2. Prefer new launch files under `<name>_bringup/launch`.
3. When editing an existing package, follow the established launch directory if one already exists.
4. Name new files `<purpose>.launch.xml` or `<purpose>.launch.py`; avoid generic `launch.py` or package-name-only files unless the repo already uses that convention.
5. Prefer XML for simple/static launch descriptions. Use Python when launch behavior needs conditionals, generated action lists, nontrivial substitutions, event handlers, composable-node setup that is clearer in Python, or logic that XML would make awkward.
6. Ensure launch files are installed so `ros2 launch` can find them. Keep this as a brief check; load `ros2-cmakelists` for detailed package build/install edits.
7. Validate when possible:
   - Use `ros2 launch <package> <file> --show-args` when the workspace is built and sourced.
   - Use XML or Python syntax checks as a fallback when ROS2 tooling is unavailable.
   - Report clearly when validation could not run because the ROS environment is not sourced.

## ros2_control

- Do not put controller-specific remappings on the `controller_manager` or `ros2_control_node` launch action. That path is deprecated and emits: `The use of remapping arguments to the controller_manager node is deprecated`.
- Pass controller remappings through the `controller_manager` `spawner` executable with `--controller-ros-args` so the arguments are applied to the controller node itself.
- Keep the ROS args string grouped after `--controller-ros-args`, for example `--ros-args --remap ~/cmd_vel:=/cmd_vel`.

## References

- Read `references/xml-launch.md` when creating or modifying `.launch.xml` files.
- Read `references/python-launch.md` when creating or modifying `.launch.py` files.

Load the `ros2-cpp-node` shared node module when launch changes depend on node names, parameters, namespaces, remappings, lifecycle behavior, or graph interfaces. Keep launch-specific syntax in this skill and node behavior decisions in the shared node module.
