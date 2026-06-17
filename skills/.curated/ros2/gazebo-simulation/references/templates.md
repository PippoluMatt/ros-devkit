# Gazebo Simulation Templates

Use these templates when `--setup` is not enough or when adapting an existing launch file by hand.

## config/gazebo_bridge.yaml

```yaml
- ros_topic_name: "/clock"
  gz_topic_name: "/clock"
  ros_type_name: "rosgraph_msgs/msg/Clock"
  gz_type_name: "gz.msgs.Clock"
  direction: GZ_TO_ROS

- ros_topic_name: "/joint_states"
  gz_topic_name: "/world/test_world/model/<robot_name>/joint_state"
  ros_type_name: "sensor_msgs/msg/JointState"
  gz_type_name: "gz.msgs.Model"
  direction: GZ_TO_ROS

- ros_topic_name: "/tf"
  gz_topic_name: "/model/<robot_name>/tf"
  ros_type_name: "tf2_msgs/msg/TFMessage"
  gz_type_name: "gz.msgs.Pose_V"
  direction: GZ_TO_ROS

- ros_topic_name: "/cmd_vel"
  gz_topic_name: "/model/<robot_name>/cmd_vel"
  ros_type_name: "geometry_msgs/msg/Twist"
  gz_type_name: "gz.msgs.Twist"
  direction: ROS_TO_GZ
```

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
