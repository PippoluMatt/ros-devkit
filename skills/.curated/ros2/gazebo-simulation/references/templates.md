# Gazebo Simulation Templates

Use these templates when `--setup` is not enough or when adapting an existing launch file by hand.

## launch/gazebo.launch.xml

```xml
<launch>
  <arg name="gazebo_config_path" default="$(find-pkg-share <bringup_package>)/config/gazebo_bridge.yaml"/>

  <include file="$(find-pkg-share ros_gz_sim)/launch/gz_sim.launch.py">
    <arg name="gz_args" value="$(find-pkg-share <bringup_package>)/worlds/test_world.sdf -r"/>
    <!-- <arg name="gz_args" value="empty.sdf -r"/> -->
  </include>

  <node pkg="ros_gz_sim" exec="create" args="-topic robot_description"/>
  <node pkg="ros_gz_bridge" exec="parameter_bridge">
    <param name="config_file" value="$(var gazebo_config_path)"/>
  </node>
</launch>
```

## Python Launch Equivalent

Use this shape only when the package already uses Python launch files or needs launch-time logic.

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    gazebo_config_path = LaunchConfiguration("gazebo_config_path")
    world_path = PathJoinSubstitution(
        [FindPackageShare("<bringup_package>"), "worlds", "test_world.sdf"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "gazebo_config_path",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare("<bringup_package>"),
                        "config",
                        "gazebo_bridge.yaml",
                    ]
                ),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [
                        PathJoinSubstitution(
                            [
                                FindPackageShare("ros_gz_sim"),
                                "launch",
                                "gz_sim.launch.py",
                            ]
                        )
                    ]
                ),
                launch_arguments={"gz_args": [world_path, " -r"]}.items(),
            ),
            Node(pkg="ros_gz_sim", executable="create", arguments=["-topic", "robot_description"]),
            Node(
                pkg="ros_gz_bridge",
                executable="parameter_bridge",
                parameters=[{"config_file": gazebo_config_path}],
            ),
        ]
    )
```

## urdf/<robot_name>_gazebo.xacro

```xml
<?xml version="1.0" ?>
<robot name="<robot_name>" xmlns:xacro="http://www.ros.org/wiki/xacro">

    <gazebo reference="base_link">
        <material>Gazebo/Grey</material>
    </gazebo>

</robot>
```

Include it from `urdf/main.xacro`:

```xml
<xacro:include filename="$(find <robot_name>_description)/urdf/<robot_name>_gazebo.xacro" />
```

## Adding Gazebo System Plugins

### Model-level plugins (in the gazebo xacro)

Model-level plugins are added inside `<gazebo>` tags in `<robot_name>_gazebo.xacro`. Example for `DiffDrive`:

```xml
<gazebo>
    <plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
        <left_joint>wheel_left_joint</left_joint>
        <right_joint>wheel_right_joint</right_joint>
        <wheel_separation>0.4</wheel_separation>
        <wheel_radius>0.1</wheel_radius>
    </plugin>
</gazebo>
```

Example for `JointTrajectoryController`:

```xml
<gazebo>
    <plugin filename="gz-sim-joint-trajectory-controller-system" name="gz::sim::systems::JointTrajectoryController">
        <joint_name>joint_1</joint_name>
        <position_p_gain>100</position_p_gain>
    </plugin>
</gazebo>
```

### Sensor and world-level plugins (in the world .sdf)

Sensor system plugins are added as `<plugin .../>` lines inside the `<world>` tag of the `.sdf` file in `worlds/`. Example for `IMU`:

```xml
<plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
```

Example for `ForceTorque`:

```xml
<plugin name="gz::sim::systems::ForceTorque" filename="gz-sim-forcetorque-system"/>
```

### Sensors system plugin (for rendering sensors)

When the robot has rendering sensors (lidar, camera, depth_camera, rgbd_camera, gpu_lidar, thermal_camera, segmentation_camera, boundingbox_camera), add this block inside `<world>` in the `.sdf` file:

```xml
<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
  <render_engine>ogre2</render_engine>
</plugin>
```

### Plugin naming conventions

- **filename**: `gz-sim-<cmake_name>-system` (all lowercase, dashes). The cmake name comes from the first argument to `gz_add_system()` in the plugin's `CMakeLists.txt` in the [gz-sim repository](https://github.com/gazebosim/gz-sim/tree/main/src/systems).
- **name**: `gz::sim::systems::<ClassName>` found in the last line of the `.cc` file via the `GZ_ADD_PLUGIN_ALIAS` macro.
- The full plugin registry is in [plugin_registry.yaml](plugin_registry.yaml).
