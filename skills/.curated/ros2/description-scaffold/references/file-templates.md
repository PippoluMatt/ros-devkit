# File Templates

Complete templates for all files in a `<name>_description` package.
Replace `<name>` with the robot name and `<sensor>` with the sensor type.

## urdf/main.xacro

Entry point — includes only. **materials.xacro must be first.**

```xml
<?xml version="1.0" ?>
<robot name="<name>" xmlns:xacro="http://www.ros.org/wiki/xacro">

    <xacro:include filename="$(find <name>_description)/urdf/materials.xacro" />
    <xacro:include filename="$(find <name>_description)/urdf/<sensor>.xacro" />
    <xacro:include filename="$(find <name>_description)/urdf/<name>.urdf.xacro" />

</robot>
```

Add one `<xacro:include>` line per sensor file. Never put robot definitions here.

## urdf/materials.xacro

Color and material definitions. Always included first to avoid redundancy.

```xml
<?xml version="1.0" ?>
<robot name="<name>" xmlns:xacro="http://www.ros.org/wiki/xacro">

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
```

## urdf/<name>.urdf.xacro

Robot body definition — links, joints, inertial properties.

```xml
<?xml version="1.0" ?>
<robot name="<name>" xmlns:xacro="http://www.ros.org/wiki/xacro">

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
```

## urdf/<sensor>.xacro

One file per sensor. Contains: link, joint to parent, optional Gazebo plugin.

### Camera

```xml
<?xml version="1.0" ?>
<robot name="<name>" xmlns:xacro="http://www.ros.org/wiki/xacro">

    <link name="camera_link">
        <visual>
            <geometry>
                <box size="0.03 0.03 0.03"/>
            </geometry>
            <material name="black"/>
        </visual>
        <collision>
            <geometry>
                <box size="0.03 0.03 0.03"/>
            </geometry>
        </collision>
        <inertial>
            <mass value="0.05"/>
            <inertia ixx="0.00001" ixy="0.0" ixz="0.0" iyy="0.00001" iyz="0.0" izz="0.00001"/>
        </inertial>
    </link>

    <joint name="camera_joint" type="fixed">
        <parent link="base_link"/>
        <child link="camera_link"/>
        <origin xyz="0.1 0.0 0.05" rpy="0.0 0.0 0.0"/>
    </joint>

    <!-- Gazebo plugin (uncomment for simulation) -->
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
    -->

</robot>
```

### Lidar

```xml
<?xml version="1.0" ?>
<robot name="<name>" xmlns:xacro="http://www.ros.org/wiki/xacro">

    <link name="lidar_link">
        <visual>
            <geometry>
                <cylinder length="0.05" radius="0.03"/>
            </geometry>
            <material name="black"/>
        </visual>
        <collision>
            <geometry>
                <cylinder length="0.05" radius="0.03"/>
            </geometry>
        </collision>
        <inertial>
            <mass value="0.1"/>
            <inertia ixx="0.00002" ixy="0.0" ixz="0.0" iyy="0.00002" iyz="0.0" izz="0.00002"/>
        </inertial>
    </link>

    <joint name="lidar_joint" type="fixed">
        <parent link="base_link"/>
        <child link="lidar_link"/>
        <origin xyz="0.0 0.0 0.1" rpy="0.0 0.0 0.0"/>
    </joint>

    <!-- Gazebo plugin (uncomment for simulation) -->
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
    -->

</robot>
```

### IMU

```xml
<?xml version="1.0" ?>
<robot name="<name>" xmlns:xacro="http://www.ros.org/wiki/xacro">

    <link name="imu_link">
        <visual>
            <geometry>
                <box size="0.02 0.02 0.02"/>
            </geometry>
            <material name="black"/>
        </visual>
        <collision>
            <geometry>
                <box size="0.02 0.02 0.02"/>
            </geometry>
        </collision>
        <inertial>
            <mass value="0.01"/>
            <inertia ixx="0.000001" ixy="0.0" ixz="0.0" iyy="0.000001" iyz="0.0" izz="0.000001"/>
        </inertial>
    </link>

    <joint name="imu_joint" type="fixed">
        <parent link="base_link"/>
        <child link="imu_link"/>
        <origin xyz="0.0 0.0 0.0" rpy="0.0 0.0 0.0"/>
    </joint>

    <!-- Gazebo plugin (uncomment for simulation) -->
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
    -->

</robot>
```

### Generic sensor

```xml
<?xml version="1.0" ?>
<robot name="<name>" xmlns:xacro="http://www.ros.org/wiki/xacro">

    <link name="<sensor>_link">
        <visual>
            <geometry>
                <box size="0.03 0.03 0.03"/>
            </geometry>
            <material name="black"/>
        </visual>
        <collision>
            <geometry>
                <box size="0.03 0.03 0.03"/>
            </geometry>
        </collision>
        <inertial>
            <mass value="0.05"/>
            <inertia ixx="0.00001" ixy="0.0" ixz="0.0" iyy="0.00001" iyz="0.0" izz="0.00001"/>
        </inertial>
    </link>

    <joint name="<sensor>_joint" type="fixed">
        <parent link="base_link"/>
        <child link="<sensor>_link"/>
        <origin xyz="0.0 0.0 0.05" rpy="0.0 0.0 0.0"/>
    </joint>

</robot>
```

## CMakeLists.txt

Expected final state after `ros-devkit description-scaffold --create`:

```cmake
cmake_minimum_required(VERSION 3.8)
project(<name>_description)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(urdf REQUIRED)
find_package(xacro REQUIRED)

install(
  DIRECTORY urdf meshes rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
```

## package.xml

Generated by `ros2 pkg create --dependencies urdf xacro`:

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name><name>_description</name>
  <version>0.0.0</version>
  <description>URDF/xacro description package for <name></description>
  <maintainer email="user@example.com">Your Name</maintainer>
  <license>TODO: License declaration</license>

  <buildtool_depend>ament_cmake</buildtool_depend>

  <depend>urdf</depend>
  <depend>xacro</depend>

  <test_depend>ament_lint_auto</test_depend>
  <test_depend>ament_lint_common</test_depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
```

## rviz/<name>.rviz

Minimal RViz config showing the robot model:

```yaml
Panels:
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
```
