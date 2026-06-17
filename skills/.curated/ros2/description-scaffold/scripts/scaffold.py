#!/usr/bin/env python3
"""Scaffold a ROS2 description package using the official ros2 pkg create command.

Creates <name>_description/ using `ros2 pkg create`, removes unused src/include
directories and generated CMake lint boilerplate, then adds the standard
modular xacro structure with templated files.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SHARED_SCRIPTS))

from cmake import add_install_share_directories, remove_default_lint_block  # noqa: E402


# ── Xacro templates ─────────────────────────────────────────────────

def main_xacro(name: str, sensors: list[str]) -> str:
    includes = [f"$(find {name}_description)/urdf/materials.xacro"]
    for s in sensors:
        includes.append(f"$(find {name}_description)/urdf/{s}.xacro")
    includes.append(f"$(find {name}_description)/urdf/{name}.urdf.xacro")
    lines = "\n    ".join(f'<xacro:include filename="{inc}" />' for inc in includes)
    return f"""<?xml version="1.0" ?>
<robot name="{name}" xmlns:xacro="http://www.ros.org/wiki/xacro">

    {lines}

</robot>
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


# ── Sensor templates ───────────────────────────────────────────────

SENSOR_SPECS: dict[str, dict] = {
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


# ── RViz config ──────────────────────────────────────────────────────

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


# ── CMakeLists.txt editing ──────────────────────────────────────────

def edit_cmake(cmake_path: Path) -> None:
    """Remove generated lint boilerplate and add install directive."""
    content = cmake_path.read_text(encoding="utf-8")
    content = remove_default_lint_block(content)
    content = add_install_share_directories(content, ["urdf", "meshes", "rviz"])
    cmake_path.write_text(content, encoding="utf-8")


# ── Scaffold ─────────────────────────────────────────────────────────

def scaffold(
    name: str,
    sensors: list[str],
    destination: Path,
    maintainer: str | None,
    email: str | None,
    license_type: str | None,
) -> None:
    """Create the full package structure using ros2 pkg create."""
    pkg_name = f"{name}_description"

    if not shutil.which("ros2"):
        print("ERROR: 'ros2' command not found. Source ROS 2 first.")
        sys.exit(1)

    pkg_dir = destination / pkg_name
    if pkg_dir.exists():
        print(f"ERROR: Package directory already exists: {pkg_dir}")
        sys.exit(1)

    destination.mkdir(parents=True, exist_ok=True)

    # Build ros2 pkg create command
    cmd: list[str] = [
        "ros2", "pkg", "create", pkg_name,
        "--build-type", "ament_cmake",
        "--dependencies", "urdf", "xacro",
        "--description", f"URDF/xacro description package for {name}",
        "--destination-directory", str(destination),
    ]
    if maintainer:
        cmd.extend(["--maintainer-name", maintainer])
    if email:
        cmd.extend(["--maintainer-email", email])
    if license_type:
        cmd.extend(["--license", license_type])

    # Run ros2 pkg create
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR: ros2 pkg create failed:")
        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)
        sys.exit(1)

    created: list[str] = []
    removed: list[str] = []

    # Remove src/ and include/ directories
    for d in ["src", "include"]:
        p = pkg_dir / d
        if p.exists():
            shutil.rmtree(p)
            removed.append(d)

    # Edit CMakeLists.txt
    edit_cmake(pkg_dir / "CMakeLists.txt")

    # Create directories
    for d in ["meshes", "rviz", "urdf"]:
        (pkg_dir / d).mkdir(exist_ok=True)

    # Create urdf files (skip if already exists)
    def write_new(rel_path: str, content: str) -> None:
        p = pkg_dir / rel_path
        if p.exists():
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        created.append(rel_path)

    write_new("urdf/main.xacro", main_xacro(name, sensors))
    write_new("urdf/materials.xacro", MATERIALS_XACRO.format(name=name))
    write_new(f"urdf/{name}.urdf.xacro", URDF_XACRO.format(name=name))
    for sensor in sensors:
        write_new(f"urdf/{sensor}.xacro", sensor_xacro(name, sensor))
    write_new(f"rviz/{name}.rviz", RVIZ_CONFIG)

    # Report
    print(f"\nPackage : {pkg_name}")
    print(f"Path    : {pkg_dir}")
    print(f"Sensors : {', '.join(sensors) if sensors else 'none'}")
    if removed:
        print(f"Removed : {', '.join(d + '/' for d in removed)}")
    print("Modified: CMakeLists.txt (removed BUILD_TESTING, added install)")
    if created:
        print(f"Created : {', '.join(created)}")
    print(f"\nNext steps:")
    print(f"  1. Customize links/joints in urdf/{name}.urdf.xacro")
    print(f"  2. Adjust sensor positions and enable Gazebo plugins")
    print(f"  3. Update license in package.xml")
    print(f"  4. Validate: ros-devkit description-scaffold --verify {pkg_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scaffold a ROS2 description package using ros2 pkg create."
    )
    parser.add_argument("name", help="Robot name (e.g., my_robot)")
    parser.add_argument("--sensors", default="", help="Comma-separated sensor names (e.g., camera,lidar,imu)")
    parser.add_argument(
        "--destination-directory", "--dir",
        dest="destination",
        default=".",
        help="Directory where to create the package (default: current directory)",
    )
    parser.add_argument("--maintainer", default=None, help="Maintainer name (passed to ros2 pkg create)")
    parser.add_argument("--email", default=None, help="Maintainer email (passed to ros2 pkg create)")
    parser.add_argument("--license", default=None, help="License (passed to ros2 pkg create)")

    args = parser.parse_args()
    sensors = [s.strip() for s in args.sensors.split(",") if s.strip()]
    scaffold(
        name=args.name,
        sensors=sensors,
        destination=Path(args.destination),
        maintainer=args.maintainer,
        email=args.email,
        license_type=args.license,
    )
