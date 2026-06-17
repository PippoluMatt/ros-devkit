# Python Launch Files

Use Python launch files when the launch description needs logic that XML would make awkward: conditionals, generated action lists, event handlers, computed substitutions, or complex composable-node setup.

## Conventions

- Define `generate_launch_description()` and return a `LaunchDescription`.
- Keep imports specific to the actions and substitutions used.
- Use `DeclareLaunchArgument` for user-facing launch arguments.
- Use `LaunchConfiguration` for values supplied by launch arguments.
- Use `FindPackageShare`, `PathJoinSubstitution`, and launch substitutions instead of hard-coded absolute paths.
- Keep Python logic small and deterministic; move node behavior decisions into the node package rather than encoding them in launch code.

## Example

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    config_file = PathJoinSubstitution([
        FindPackageShare("my_robot_bringup"),
        "config",
        "robot.yaml",
    ])

    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        Node(
            package="my_robot_driver",
            executable="driver_node",
            name="driver",
            output="screen",
            parameters=[
                {"use_sim_time": use_sim_time},
                config_file,
            ],
            remappings=[
                ("cmd_vel", "/cmd_vel"),
            ],
        ),
    ])
```

## ros2_control Controller Remappings

Do not attach controller-specific `remappings` to a `controller_manager` or `ros2_control_node` `Node`. Pass them to the controller through the `controller_manager` `spawner` with `--controller-ros-args`.

```python
Node(
    package="controller_manager",
    executable="spawner",
    arguments=[
        "diff_drive_controller",
        "--controller-ros-args",
        "--ros-args --remap ~/cmd_vel:=/cmd_vel",
    ],
    output="screen",
)
```

For multiple controllers with different remappings, use one spawner action per controller or the spawner advanced `--controller <name>` form so each controller gets its own `--controller-ros-args` value.

## Validation

- Run `python3 -m py_compile <file>.launch.py` as a syntax check.
- Run `ros2 launch <package> <file>.launch.py --show-args` when the workspace is built and sourced.
- Do not execute arbitrary launch side effects just to inspect syntax; prefer `--show-args` for a low-impact sanity check.
