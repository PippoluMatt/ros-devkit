"""Gazebo simulation scaffold templates."""

from __future__ import annotations


def _gazebo_xacro(robot_name: str) -> str:
    return f"""<?xml version="1.0" ?>
<robot name="{robot_name}" xmlns:xacro="http://www.ros.org/wiki/xacro">

    <gazebo reference="base_link">
        <material>Gazebo/Grey</material>
    </gazebo>

</robot>
"""


def _bridge_yaml(robot_name: str, world_name: str) -> str:
    return f"""- ros_topic_name: "/clock"
  gz_topic_name: "/clock"
  ros_type_name: "rosgraph_msgs/msg/Clock"
  gz_type_name: "gz.msgs.Clock"
  direction: GZ_TO_ROS

- ros_topic_name: "/joint_states"
  gz_topic_name: "/world/{world_name}/model/{robot_name}/joint_state"
  ros_type_name: "sensor_msgs/msg/JointState"
  gz_type_name: "gz.msgs.Model"
  direction: GZ_TO_ROS

- ros_topic_name: "/tf"
  gz_topic_name: "/model/{robot_name}/tf"
  ros_type_name: "tf2_msgs/msg/TFMessage"
  gz_type_name: "gz.msgs.Pose_V"
  direction: GZ_TO_ROS

- ros_topic_name: "/cmd_vel"
  gz_topic_name: "/model/{robot_name}/cmd_vel"
  ros_type_name: "geometry_msgs/msg/Twist"
  gz_type_name: "gz.msgs.Twist"
  direction: ROS_TO_GZ
"""


def _world_sdf(world_name: str) -> str:
    return f"""<?xml version="1.0" ?>
<sdf version="1.9">
  <world name="{world_name}">
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>

    <light name="sun" type="directional">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.8 0.8 0.8 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.5 0.1 -0.9</direction>
    </light>

    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>100 100</size>
            </plane>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>100 100</size>
            </plane>
          </geometry>
        </visual>
      </link>
    </model>
  </world>
</sdf>
"""


def _gazebo_launch_xml(bringup_pkg: str, world_name: str) -> str:
    return f"""<launch>
  <arg name="gazebo_config_path" default="$(find-pkg-share {bringup_pkg})/config/gazebo_bridge.yaml"/>

  <include file="$(find-pkg-share ros_gz_sim)/launch/gz_sim.launch.py">
    <arg name="gz_args" value="$(find-pkg-share {bringup_pkg})/worlds/{world_name}.sdf -r"/>
    <!-- <arg name="gz_args" value="empty.sdf -r"/> -->
  </include>

  <node pkg="ros_gz_sim" exec="create" args="-topic robot_description"/>
  <node pkg="ros_gz_bridge" exec="parameter_bridge">
    <param name="config_file" value="$(var gazebo_config_path)"/>
  </node>
</launch>
"""
