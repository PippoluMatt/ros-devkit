"""Templates used by the ros2 description-scaffold workflows."""

from __future__ import annotations


def main_xacro(name: str, sensors: list[str]) -> str:
    includes = [f"$(find {name}_description)/urdf/materials.xacro"]
    for sensor in sensors:
        includes.append(f"$(find {name}_description)/urdf/{sensor}.xacro")
    includes.append(f"$(find {name}_description)/urdf/{name}.urdf.xacro")
    lines = "\n    ".join(f'<xacro:include filename="{include}" />' for include in includes)
    return f"""<?xml version="1.0" ?>
<robot name="{name}" xmlns:xacro="http://www.ros.org/wiki/xacro">

    {lines}

</robot>
"""


def package_xml(pkg_name: str, robot_name: str) -> str:
    return f"""<?xml version="1.0"?>
<package format="3">
  <name>{pkg_name}</name>
  <version>0.0.0</version>
  <description>URDF/xacro description package for {robot_name}</description>
  <maintainer email="user@example.com">TODO</maintainer>
  <license>TODO: License declaration</license>

  <buildtool_depend>ament_cmake</buildtool_depend>

  <depend>urdf</depend>
  <depend>xacro</depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
"""


def cmakelists(pkg_name: str) -> str:
    return f"""cmake_minimum_required(VERSION 3.8)
project({pkg_name})

find_package(ament_cmake REQUIRED)
find_package(urdf REQUIRED)
find_package(xacro REQUIRED)

install(
  DIRECTORY urdf meshes rviz
  DESTINATION share/${{PROJECT_NAME}}
)

ament_package()
"""


MATERIALS_XACRO = """<?xml version="1.0" ?>
<robot name="{name}" xmlns:xacro="http://www.ros.org/wiki/xacro">

    <material name="black">
        <color rgba="0.0 0.0 0.0 1.0"/>
    </material>

    <material name="white">
        <color rgba="1.0 1.0 1.0 1.0"/>
    </material>

    <material name="red">
        <color rgba="0.8 0.0 0.0 1.0"/>
    </material>

    <material name="blue">
        <color rgba="0.0 0.0 0.8 1.0"/>
    </material>

    <material name="green">
        <color rgba="0.0 0.8 0.0 1.0"/>
    </material>

    <material name="grey">
        <color rgba="0.5 0.5 0.5 1.0"/>
    </material>

</robot>
"""


URDF_XACRO = """<?xml version="1.0" ?>
<robot name="{name}" xmlns:xacro="http://www.ros.org/wiki/xacro">

    <!-- Base link -->
    <link name="base_link">
        <visual>
            <origin xyz="0.0 0.0 0.0" rpy="0.0 0.0 0.0"/>
            <geometry>
                <box size="0.2 0.2 0.1"/>
            </geometry>
            <material name="white"/>
        </visual>
        <collision>
            <origin xyz="0.0 0.0 0.0" rpy="0.0 0.0 0.0"/>
            <geometry>
                <box size="0.2 0.2 0.1"/>
            </geometry>
        </collision>
        <inertial>
            <origin xyz="0.0 0.0 0.0" rpy="0.0 0.0 0.0"/>
            <mass value="1.0"/>
            <inertia
                ixx="0.0033" ixy="0.0" ixz="0.0"
                iyy="0.0033" iyz="0.0"
                izz="0.0067"/>
        </inertial>
    </link>

    <!-- Add more links and joints here -->

</robot>
"""


SENSOR_SPECS: dict[str, dict[str, str]] = {
    "camera": {
        "geometry": '<box size="0.03 0.03 0.03"/>',
        "mass": "0.05",
        "inertia": 'ixx="0.00001" ixy="0.0" ixz="0.0" iyy="0.00001" iyz="0.0" izz="0.00001"',
        "origin_xyz": "0.1 0.0 0.05",
        "plugin_lines": """    <!-- Gazebo plugin (uncomment for simulation) -->
    <!--
    <gazebo reference="camera_link">
        <sensor type="camera" name="camera_sensor">
            <update_rate>30.0</update_rate>
            <camera name="camera">
                <horizontal_fov>1.3962634</horizontal_fov>
                <image>
                    <width>640</width>
                    <height>480</height>
                    <format>R8G8B8</format>
                </image>
                <clip>
                    <near>0.02</near>
                    <far>300.0</far>
                </clip>
            </camera>
            <plugin name="camera_controller" filename="libgazebo_ros_camera.so">
                <alwaysOn>true</alwaysOn>
                <cameraName>camera</cameraName>
                <imageTopicName>image_raw</imageTopicName>
                <cameraInfoTopicName>camera_info</cameraInfoTopicName>
                <frameName>camera_link</frameName>
            </plugin>
        </sensor>
    </gazebo>
    -->""",
    },
    "lidar": {
        "geometry": '<cylinder length="0.05" radius="0.03"/>',
        "mass": "0.1",
        "inertia": 'ixx="0.00002" ixy="0.0" ixz="0.0" iyy="0.00002" iyz="0.0" izz="0.00002"',
        "origin_xyz": "0.0 0.0 0.1",
        "plugin_lines": """    <!-- Gazebo plugin (uncomment for simulation) -->
    <!--
    <gazebo reference="lidar_link">
        <sensor type="ray" name="lidar_sensor">
            <update_rate>10.0</update_rate>
            <ray>
                <scan>
                    <horizontal>
                        <samples>360</samples>
                        <resolution>1</resolution>
                        <min_angle>-3.14159</min_angle>
                        <max_angle>3.14159</max_angle>
                    </horizontal>
                </scan>
                <range>
                    <min>0.1</min>
                    <max>30.0</max>
                </range>
            </ray>
            <plugin name="lidar_controller" filename="libgazebo_ros_laser.so">
                <topicName>scan</topicName>
                <frameName>lidar_link</frameName>
            </plugin>
        </sensor>
    </gazebo>
    -->""",
    },
    "imu": {
        "geometry": '<box size="0.02 0.02 0.02"/>',
        "mass": "0.01",
        "inertia": 'ixx="0.000001" ixy="0.0" ixz="0.0" iyy="0.000001" iyz="0.0" izz="0.000001"',
        "origin_xyz": "0.0 0.0 0.0",
        "plugin_lines": """    <!-- Gazebo plugin (uncomment for simulation) -->
    <!--
    <gazebo reference="imu_link">
        <sensor type="imu" name="imu_sensor">
            <update_rate>100.0</update_rate>
            <plugin name="imu_plugin" filename="libgazebo_ros_imu.so">
                <topicName>imu/data</topicName>
                <frameName>imu_link</frameName>
            </plugin>
        </sensor>
    </gazebo>
    -->""",
    },
}

DEFAULT_SPEC = {
    "geometry": '<box size="0.03 0.03 0.03"/>',
    "mass": "0.05",
    "inertia": 'ixx="0.00001" ixy="0.0" ixz="0.0" iyy="0.00001" iyz="0.0" izz="0.00001"',
    "origin_xyz": "0.0 0.0 0.05",
    "plugin_lines": "    <!-- Add Gazebo plugin here if needed -->",
}


def sensor_xacro(name: str, sensor: str) -> str:
    spec = SENSOR_SPECS.get(sensor, DEFAULT_SPEC)
    link_name = f"{sensor}_link"
    joint_name = f"{sensor}_joint"
    return f"""<?xml version="1.0" ?>
<robot name="{name}" xmlns:xacro="http://www.ros.org/wiki/xacro">

    <link name="{link_name}">
        <visual>
            <geometry>
                {spec["geometry"]}
            </geometry>
            <material name="black"/>
        </visual>
        <collision>
            <geometry>
                {spec["geometry"]}
            </geometry>
        </collision>
        <inertial>
            <mass value="{spec["mass"]}"/>
            <inertia {spec["inertia"]}/>
        </inertial>
    </link>

    <joint name="{joint_name}" type="fixed">
        <parent link="base_link"/>
        <child link="{link_name}"/>
        <origin xyz="{spec["origin_xyz"]}" rpy="0.0 0.0 0.0"/>
    </joint>

{spec["plugin_lines"]}

</robot>
"""


RVIZ_CONFIG = """Panels:
  - Class: rviz_common/Displays
    Name: Displays
  - Class: rviz_common/Views
    Name: Views
Visualization Manager:
  Displays:
    - Class: rviz_default_plugins/RobotModel
      Name: RobotModel
      Description Topic:
        Value: /robot_description
      Visual Enabled: true
      Collision Enabled: false
  Global Options:
    Fixed Frame: base_link
    Frame Rate: 30
  Value: true
Views:
  Current:
    Class: rviz_default_plugins/Orbit
    Distance: 3.0
    Name: Current View
    Near Clip Distance: 0.01
    Focal Point:
      X: 0
      Y: 0
      Z: 0
"""
