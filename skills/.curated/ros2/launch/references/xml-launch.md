# XML Launch Files

Use XML launch files for simple/static bringup: fixed node lists, includes, arguments, remappings, namespaces, environment values, and straightforward parameter loading.

## Conventions

- Use `<launch>` as the root element.
- Use `<let>` for internal variables such as paths, computed substitutions, package names, and repeated values.
- Use `<arg>` only for user-facing values that callers should be able to override at launch time.
- Use `$(find-pkg-share package_name)` for package share directories.
- Keep substitutions readable by assigning repeated expressions to `<let>` names.
- Prefer explicit node names, namespaces, remaps, and output settings when they affect graph behavior.

## Example

```xml
<launch>
  <arg name="use_sim_time" default="false"/>

  <let name="bringup_pkg" value="$(find-pkg-share my_robot_bringup)"/>
  <let name="config_file" value="$(var bringup_pkg)/config/robot.yaml"/>

  <node pkg="my_robot_driver"
        exec="driver_node"
        name="driver"
        output="screen">
    <param name="use_sim_time" value="$(var use_sim_time)"/>
    <param from="$(var config_file)"/>
    <remap from="cmd_vel" to="/cmd_vel"/>
  </node>

  <include file="$(var bringup_pkg)/launch/sensors.launch.xml"/>
</launch>
```

## ros2_control Controller Remappings

Do not attach controller-specific `<remap>` entries to a `controller_manager` or `ros2_control_node` action. Pass them to the controller through the `controller_manager` `spawner` with `--controller-ros-args`.

```xml
<node pkg="controller_manager"
      exec="spawner"
      args="diff_drive_controller --controller-ros-args '--ros-args --remap ~/cmd_vel:=/cmd_vel'"
      output="screen"/>
```

For multiple controllers with different remappings, use one spawner action per controller or the spawner advanced `--controller &lt;name&gt;` form so each controller gets its own `--controller-ros-args` value.

## Validation

- Run `ros2 launch <package> <file>.launch.xml --show-args` when the workspace is sourced.
- Run an XML parser or formatter as a syntax fallback when ROS2 is unavailable.
- Do not claim runtime validity from XML syntax alone; launch substitutions and package lookups still need ROS2 context.
