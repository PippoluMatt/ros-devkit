# ROS2 Control Xacro

Use `scripts/add_ros2_control_xacro.py` to create minimal robot description scaffolding for a `hardware_interface::SystemInterface` plugin.

## Script

```bash
scripts/add_ros2_control_xacro.py [--main-xacro PATH] [--plugin-xml PATH] [--output-xacro PATH] [--hardware-name NAME]
```

Default behavior:

- Detect `main.urdf.xacro`, then `main.xacro`, in the current directory unless `--main-xacro` is passed.
- Detect a unique plugin XML containing a `<class>` with `base_class_type="hardware_interface::SystemInterface"` unless `--plugin-xml` is passed.
- Read the robot name from `<robot name="...">` in the main xacro.
- Create `<robot_name>.ros2_control.xacro` next to the main xacro unless `--output-xacro` is passed.
- Leave an existing output xacro untouched.
- Ensure the main xacro has `xmlns:xacro="http://www.ros.org/wiki/xacro"`.
- Insert `<xacro:include filename="<robot_name>.ros2_control.xacro" />` immediately after the opening `<robot ...>` tag when missing.

## Generated File

Generate a direct top-level block, not a `xacro:macro`, because the include does not call a macro.

```xml
<?xml version="1.0" ?>
<robot xmlns:xacro="http://www.ros.org/wiki/xacro">
  <ros2_control name="MyRobotHardwareInterface" type="system">
    <hardware>
      <plugin>package_name/ClassName</plugin>
    </hardware>
  </ros2_control>
</robot>
```

Set `<plugin>` from the plugin XML `<class name="...">` value. Use `type="system"` for this skill's scaffolding; `SystemInterface` is the supported interface even when the hardware includes sensors and actuators.
