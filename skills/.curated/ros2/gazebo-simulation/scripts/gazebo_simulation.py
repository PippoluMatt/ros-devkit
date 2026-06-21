#!/usr/bin/env python3
"""Set up and diagnose ROS2 Gazebo simulation package wiring."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import urllib.request
import urllib.error

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SHARED_SCRIPTS))

from cmake import add_install_share_directories  # noqa: E402
from diagnostics import Finding, print_finding  # noqa: E402

DISCOVERY_SKIP_DIRS = {".git", ".venv", "__pycache__", "build", "install", "log"}
PLUGIN_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "plugin_registry.yaml"
GZ_SIM_RAW_BASE = "https://raw.githubusercontent.com/gazebosim/gz-sim/main/src/systems"
SENSOR_PLUGIN_ALIASES = {
    "lidar", "camera", "rgbd_camera", "depth_camera", "gpu_lidar",
    "thermal_camera", "segmentation_camera", "boundingbox_camera",
}
BRINGUP_INSTALL_DIRS = ("launch", "config", "worlds")
REQUIRED_BRIDGE_KEYS = {
    "ros_topic_name",
    "gz_topic_name",
    "ros_type_name",
    "gz_type_name",
    "direction",
}
VALID_DIRECTIONS = {"GZ_TO_ROS", "ROS_TO_GZ", "BIDIRECTIONAL"}
VALID_TYPE_PAIRS: dict[str, set[str]] = {
    # actuator_msgs
    "actuator_msgs/msg/Actuators": {"gz.msgs.Actuators"},
    # builtin_interfaces
    "builtin_interfaces/msg/Time": {"gz.msgs.Time"},
    # geometry_msgs
    "geometry_msgs/msg/Point": {"gz.msgs.Vector3d"},
    "geometry_msgs/msg/Pose": {"gz.msgs.Pose"},
    "geometry_msgs/msg/PoseArray": {"gz.msgs.Pose_V"},
    "geometry_msgs/msg/PoseStamped": {"gz.msgs.Pose"},
    "geometry_msgs/msg/PoseWithCovariance": {"gz.msgs.PoseWithCovariance"},
    "geometry_msgs/msg/PoseWithCovarianceStamped": {"gz.msgs.PoseWithCovariance"},
    "geometry_msgs/msg/Quaternion": {"gz.msgs.Quaternion"},
    "geometry_msgs/msg/Transform": {"gz.msgs.Pose"},
    "geometry_msgs/msg/TransformStamped": {"gz.msgs.Pose"},
    "geometry_msgs/msg/Twist": {"gz.msgs.Twist"},
    "geometry_msgs/msg/TwistStamped": {"gz.msgs.Twist"},
    "geometry_msgs/msg/TwistWithCovariance": {"gz.msgs.TwistWithCovariance"},
    "geometry_msgs/msg/TwistWithCovarianceStamped": {"gz.msgs.TwistWithCovariance"},
    "geometry_msgs/msg/Vector3": {"gz.msgs.Vector3d"},
    "geometry_msgs/msg/Wrench": {"gz.msgs.Wrench"},
    "geometry_msgs/msg/WrenchStamped": {"gz.msgs.Wrench"},
    # gps_msgs
    "gps_msgs/msg/GPSFix": {"gz.msgs.NavSat"},
    # marine_acoustic_msgs
    "marine_acoustic_msgs/msg/Dvl": {"gz.msgs.DVLVelocityTracking"},
    # nav_msgs
    "nav_msgs/msg/Odometry": {"gz.msgs.Odometry", "gz.msgs.OdometryWithCovariance"},
    # rcl_interfaces
    "rcl_interfaces/msg/ParameterValue": {"gz.msgs.Any"},
    # ros_gz_interfaces
    "ros_gz_interfaces/msg/Altimeter": {"gz.msgs.Altimeter"},
    "ros_gz_interfaces/msg/Contact": {"gz.msgs.Contact"},
    "ros_gz_interfaces/msg/Contacts": {"gz.msgs.Contacts"},
    "ros_gz_interfaces/msg/Dataframe": {"gz.msgs.Dataframe"},
    "ros_gz_interfaces/msg/Entity": {"gz.msgs.Entity"},
    "ros_gz_interfaces/msg/EntityWrench": {"gz.msgs.EntityWrench"},
    "ros_gz_interfaces/msg/Float32Array": {"gz.msgs.Float_V"},
    "ros_gz_interfaces/msg/GuiCamera": {"gz.msgs.GUICamera"},
    "ros_gz_interfaces/msg/JointWrench": {"gz.msgs.JointWrench"},
    "ros_gz_interfaces/msg/Light": {"gz.msgs.Light"},
    "ros_gz_interfaces/msg/LogicalCameraImage": {"gz.msgs.LogicalCameraImage"},
    "ros_gz_interfaces/msg/LogPlaybackStatistics": {"gz.msgs.LogPlaybackStatistics"},
    "ros_gz_interfaces/msg/ParamVec": {"gz.msgs.Param", "gz.msgs.Param_V"},
    "ros_gz_interfaces/msg/SensorNoise": {"gz.msgs.SensorNoise"},
    "ros_gz_interfaces/msg/StringVec": {"gz.msgs.StringMsg_V"},
    "ros_gz_interfaces/msg/TrackVisual": {"gz.msgs.TrackVisual"},
    "ros_gz_interfaces/msg/VideoRecord": {"gz.msgs.VideoRecord"},
    "ros_gz_interfaces/msg/WorldStatistics": {"gz.msgs.WorldStatistics"},
    # rosgraph_msgs
    "rosgraph_msgs/msg/Clock": {"gz.msgs.Clock"},
    # sensor_msgs
    "sensor_msgs/msg/BatteryState": {"gz.msgs.BatteryState"},
    "sensor_msgs/msg/CameraInfo": {"gz.msgs.CameraInfo"},
    "sensor_msgs/msg/FluidPressure": {"gz.msgs.FluidPressure"},
    "sensor_msgs/msg/Image": {"gz.msgs.Image"},
    "sensor_msgs/msg/Imu": {"gz.msgs.IMU"},
    "sensor_msgs/msg/JointState": {"gz.msgs.Model"},
    "sensor_msgs/msg/Joy": {"gz.msgs.Joy"},
    "sensor_msgs/msg/LaserScan": {"gz.msgs.LaserScan"},
    "sensor_msgs/msg/MagneticField": {"gz.msgs.Magnetometer"},
    "sensor_msgs/msg/NavSatFix": {"gz.msgs.NavSat"},
    "sensor_msgs/msg/PointCloud2": {"gz.msgs.PointCloudPacked"},
    "sensor_msgs/msg/Range": {"gz.msgs.LaserScan"},
    # std_msgs
    "std_msgs/msg/Bool": {"gz.msgs.Boolean"},
    "std_msgs/msg/ColorRGBA": {"gz.msgs.Color"},
    "std_msgs/msg/Empty": {"gz.msgs.Empty"},
    "std_msgs/msg/Float32": {"gz.msgs.Float"},
    "std_msgs/msg/Float64": {"gz.msgs.Double"},
    "std_msgs/msg/Header": {"gz.msgs.Header"},
    "std_msgs/msg/Int32": {"gz.msgs.Int32"},
    "std_msgs/msg/String": {"gz.msgs.StringMsg"},
    "std_msgs/msg/UInt32": {"gz.msgs.UInt32"},
    # tf2_msgs
    "tf2_msgs/msg/TFMessage": {"gz.msgs.Pose_V"},
    # trajectory_msgs
    "trajectory_msgs/msg/JointTrajectory": {"gz.msgs.JointTrajectory"},
    # vision_msgs
    "vision_msgs/msg/Detection2D": {"gz.msgs.AnnotatedAxisAligned2DBox"},
    "vision_msgs/msg/Detection2DArray": {"gz.msgs.AnnotatedAxisAligned2DBox_V"},
    "vision_msgs/msg/Detection3D": {"gz.msgs.AnnotatedOriented3DBox"},
    "vision_msgs/msg/Detection3DArray": {"gz.msgs.AnnotatedOriented3DBox_V"},
}


@dataclass
class Context:
    root: Path
    description_pkg: Path | None
    bringup_pkg: Path | None
    errors: list[str]


def find_package_name(pkg_dir: Path) -> str:
    pkg_xml = pkg_dir / "package.xml"
    if pkg_xml.exists():
        try:
            root = ET.parse(pkg_xml).getroot()
            name = root.findtext("name")
            if name:
                return name.strip()
        except ET.ParseError:
            pass
    return pkg_dir.name


def robot_name_from_package(pkg_name: str) -> str:
    return pkg_name[: -len("_description")] if pkg_name.endswith("_description") else pkg_name


def _should_skip_dir(dirname: str) -> bool:
    return dirname in DISCOVERY_SKIP_DIRS or dirname.startswith(".")


def _find_packages(root: Path, suffix: str) -> list[Path]:
    candidates: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [dirname for dirname in dirnames if not _should_skip_dir(dirname)]
        if "package.xml" not in filenames:
            continue
        pkg_dir = Path(current)
        if find_package_name(pkg_dir).endswith(suffix):
            candidates.append(pkg_dir.resolve())
    return sorted(candidates)


def _resolve_optional_package(value: str | None, suffix: str, label: str) -> tuple[Path | None, list[str]]:
    if not value:
        return None, []
    path = Path(value).expanduser().resolve()
    errors: list[str] = []
    if not path.is_dir():
        errors.append(f"{label} package path is not a directory: {path}")
        return None, errors
    pkg_name = find_package_name(path)
    if not pkg_name.endswith(suffix):
        errors.append(f"{label} package should end with {suffix}: {pkg_name}")
    return path, errors


def _choose_discovered(candidates: list[Path], label: str, root: Path) -> tuple[Path | None, list[str]]:
    if len(candidates) == 1:
        return candidates[0], []
    if not candidates:
        return None, []
    errors = [f"Multiple {label} packages found under {root}; pass --{label.replace(' ', '-')}-package"]
    errors.extend(f"Candidate: {candidate}" for candidate in candidates)
    return None, errors


def discover_context(
    target: str | None,
    description_package: str | None,
    bringup_package: str | None,
) -> Context:
    target_path = Path(target).expanduser().resolve() if target else Path.cwd().resolve()
    root = target_path
    errors: list[str] = []

    explicit_description, explicit_errors = _resolve_optional_package(
        description_package, "_description", "description"
    )
    errors.extend(explicit_errors)
    explicit_bringup, explicit_errors = _resolve_optional_package(
        bringup_package, "_bringup", "bringup"
    )
    errors.extend(explicit_errors)

    description_pkg = explicit_description
    bringup_pkg = explicit_bringup

    if target_path.is_dir() and (target_path / "package.xml").exists():
        pkg_name = find_package_name(target_path)
        root = target_path.parent
        if pkg_name.endswith("_description") and description_pkg is None:
            description_pkg = target_path
        elif pkg_name.endswith("_bringup") and bringup_pkg is None:
            bringup_pkg = target_path

    if not target_path.exists():
        errors.append(f"Target path does not exist: {target_path}")
        return Context(target_path, description_pkg, bringup_pkg, errors)

    search_root = root if root.exists() else target_path
    if description_pkg is None:
        discovered, discovered_errors = _choose_discovered(
            _find_packages(search_root, "_description"), "description", search_root
        )
        description_pkg = discovered
        errors.extend(discovered_errors)
    if bringup_pkg is None:
        discovered, discovered_errors = _choose_discovered(
            _find_packages(search_root, "_bringup"), "bringup", search_root
        )
        bringup_pkg = discovered
        errors.extend(discovered_errors)

    return Context(search_root, description_pkg, bringup_pkg, errors)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _source(pkg_name: str, rel_path: str | None = None) -> str:
    if rel_path:
        return f"{pkg_name}:{rel_path}"
    return pkg_name


def _cmake_without_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _installed_share_directories(cmake_content: str) -> set[str]:
    uncommented = _cmake_without_comments(cmake_content)
    installed: set[str] = set()
    for match in re.finditer(
        r"install\s*\(\s*DIRECTORY\s+(?P<dirs>.*?)\s+DESTINATION\s+share/\$\{PROJECT_NAME\}",
        uncommented,
        re.DOTALL,
    ):
        for token in re.split(r"[\s;]+", match.group("dirs").strip()):
            directory = token.strip("\"'").replace("\\", "/").rstrip("/")
            basename = directory.split("/")[-1]
            if basename:
                installed.add(basename)
    return installed


def _link_is_footprint(name: str) -> bool:
    return name == "base_footprint" or name.endswith("footprint")


def _has_direct_child(element: ET.Element, child_name: str) -> bool:
    return any(_local_name(child.tag) == child_name for child in list(element))


def _diagnose_description(pkg_dir: Path, findings: list[Finding]) -> str | None:
    pkg_name = find_package_name(pkg_dir)
    robot_name = robot_name_from_package(pkg_name)
    urdf_dir = pkg_dir / "urdf"

    findings.append(
        Finding("INFO", f"Description package path: {pkg_dir}", source=pkg_name)
    )

    if not urdf_dir.is_dir():
        findings.append(
            Finding(
                "ERROR",
                f"Missing description urdf/ directory: {pkg_dir / 'urdf'}",
                source=pkg_name,
            )
        )
        return robot_name

    xacro_files = sorted(urdf_dir.glob("*.xacro"))
    if not xacro_files:
        findings.append(
            Finding(
                "ERROR",
                f"No xacro files found under {_relative(urdf_dir, pkg_dir)}",
                source=pkg_name,
            )
        )

    for xacro_file in xacro_files:
        rel = _relative(xacro_file, pkg_dir)
        try:
            root = ET.parse(xacro_file).getroot()
        except ET.ParseError as exc:
            findings.append(
                Finding("ERROR", f"Invalid XML: {exc}", source=_source(pkg_name, rel))
            )
            continue
        for link in root.iter():
            if _local_name(link.tag) != "link":
                continue
            link_name = link.attrib.get("name", "").strip()
            if _link_is_footprint(link_name):
                findings.append(
                    Finding(
                        "INFO",
                        f"Footprint link exempt from physics tags: {link_name}",
                        source=_source(pkg_name, rel),
                    )
                )
                continue
            label = link_name or "unnamed link"
            if not _has_direct_child(link, "collision"):
                findings.append(
                    Finding(
                        "ERROR",
                        f"Link missing collision tag: {label}",
                        source=_source(pkg_name, rel),
                    )
                )
            if not _has_direct_child(link, "inertial"):
                findings.append(
                    Finding(
                        "ERROR",
                        f"Link missing inertial tag: {label}",
                        source=_source(pkg_name, rel),
                    )
                )

    gazebo_xacro = urdf_dir / f"{robot_name}_gazebo.xacro"
    gazebo_rel = f"urdf/{robot_name}_gazebo.xacro"
    if not gazebo_xacro.exists():
        findings.append(
            Finding("ERROR", f"Missing Gazebo xacro: {gazebo_rel}", source=pkg_name)
        )
    else:
        findings.append(
            Finding("INFO", "Found Gazebo xacro", source=_source(pkg_name, gazebo_rel))
        )
        try:
            root = ET.parse(gazebo_xacro).getroot()
            if not any(_local_name(element.tag) == "gazebo" for element in root.iter()):
                findings.append(
                    Finding(
                        "WARN",
                        "contains no <gazebo> elements",
                        source=_source(pkg_name, gazebo_rel),
                    )
                )
        except ET.ParseError as exc:
            findings.append(
                Finding(
                    "ERROR",
                    f"Invalid XML: {exc}",
                    source=_source(pkg_name, gazebo_rel),
                )
            )

    entrypoint = urdf_dir / "main.xacro"
    if entrypoint.exists():
        content = entrypoint.read_text(encoding="utf-8")
        if f"{robot_name}_gazebo.xacro" in content:
            findings.append(
                Finding(
                    "INFO",
                    f"includes {robot_name}_gazebo.xacro",
                    source=_source(pkg_name, "urdf/main.xacro"),
                )
            )
        else:
            findings.append(
                Finding(
                    "WARN",
                    f"does not include {robot_name}_gazebo.xacro",
                    source=_source(pkg_name, "urdf/main.xacro"),
                )
            )
    else:
        findings.append(
            Finding(
                "WARN",
                "Missing urdf/main.xacro; cannot check Gazebo xacro include",
                source=pkg_name,
            )
        )

    return robot_name


def _diagnose_bringup(pkg_dir: Path, findings: list[Finding]) -> None:
    pkg_name = find_package_name(pkg_dir)
    findings.append(Finding("INFO", f"Bringup package path: {pkg_dir}", source=pkg_name))

    for rel_path in ("package.xml", "CMakeLists.txt"):
        if (pkg_dir / rel_path).exists():
            findings.append(
                Finding("INFO", "Found bringup file", source=_source(pkg_name, rel_path))
            )
        else:
            findings.append(
                Finding("ERROR", f"Bringup package missing {rel_path}", source=pkg_name)
            )

    launch_dir = pkg_dir / "launch"
    if launch_dir.is_dir():
        findings.append(Finding("INFO", "Found bringup launch/ directory", source=pkg_name))
    else:
        findings.append(Finding("ERROR", "Bringup package missing launch/ directory", source=pkg_name))

    cmake = pkg_dir / "CMakeLists.txt"
    installed_dirs: set[str] = set()
    if cmake.exists():
        installed_dirs = _installed_share_directories(cmake.read_text(encoding="utf-8"))
        if "launch" in installed_dirs:
            findings.append(
                Finding(
                    "INFO",
                    "CMakeLists.txt installs launch/",
                    source=_source(pkg_name, "CMakeLists.txt"),
                )
            )
        else:
            findings.append(
                Finding(
                    "ERROR",
                    "CMakeLists.txt must install launch/ to share/${PROJECT_NAME}",
                    source=_source(pkg_name, "CMakeLists.txt"),
                )
            )
        for directory in ("config", "worlds"):
            if (pkg_dir / directory).exists() and directory not in installed_dirs:
                findings.append(
                    Finding(
                        "WARN",
                        f"CMakeLists.txt does not install present {directory}/ directory",
                        source=pkg_name,
                    )
                )

    _diagnose_bridge(pkg_dir, findings)
    _diagnose_launch(pkg_dir, findings)


def _parse_bridge_yaml(path: Path) -> list[dict[str, str]]:
    try:
        import yaml  # type: ignore
    except ImportError:
        return _parse_simple_bridge_yaml(path.read_text(encoding="utf-8"))

    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if parsed is None:
        return []
    if not isinstance(parsed, list):
        raise ValueError("bridge config must be a YAML list")
    entries: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            raise ValueError("bridge config entries must be mappings")
        entries.append({str(key): str(value) for key, value in item.items()})
    return entries


def _parse_simple_bridge_yaml(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current is not None:
                entries.append(current)
            current = {}
            rest = stripped[2:].strip()
            if rest:
                _parse_bridge_key_value(rest, current, line_number)
            continue
        if current is None:
            raise ValueError(f"expected '-' list item before line {line_number}")
        _parse_bridge_key_value(stripped, current, line_number)
    if current is not None:
        entries.append(current)
    return entries


def _parse_bridge_key_value(line: str, target: dict[str, str], line_number: int) -> None:
    if ":" not in line:
        raise ValueError(f"expected key/value mapping on line {line_number}")
    key, value = line.split(":", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        raise ValueError(f"empty key on line {line_number}")
    target[key] = value.strip("\"'")


def _diagnose_bridge(pkg_dir: Path, findings: list[Finding]) -> None:
    pkg_name = find_package_name(pkg_dir)
    bridge = pkg_dir / "config" / "gazebo_bridge.yaml"
    if not bridge.exists():
        findings.append(
            Finding(
                "WARN",
                "Missing Gazebo bridge: config/gazebo_bridge.yaml",
                source=pkg_name,
            )
        )
        return

    bridge_source = _source(pkg_name, "config/gazebo_bridge.yaml")
    findings.append(Finding("INFO", "Found Gazebo bridge", source=bridge_source))
    try:
        entries = _parse_bridge_yaml(bridge)
    except (OSError, ValueError) as exc:
        findings.append(
            Finding(
                "ERROR",
                f"Invalid gazebo_bridge.yaml: {exc}",
                source=bridge_source,
            )
        )
        return

    if not entries:
        findings.append(
            Finding(
                "ERROR",
                "gazebo_bridge.yaml has no bridge entries",
                source=bridge_source,
            )
        )
        return

    by_ros_topic: dict[str, dict[str, str]] = {}
    for index, entry in enumerate(entries, start=1):
        missing = sorted(REQUIRED_BRIDGE_KEYS - set(entry))
        if missing:
            findings.append(
                Finding(
                    "ERROR",
                    f"Bridge entry {index} missing required keys: {', '.join(missing)}",
                    source=bridge_source,
                )
            )
            continue
        direction = entry["direction"]
        if direction not in VALID_DIRECTIONS:
            findings.append(
                Finding(
                    "ERROR",
                    f"Bridge entry {index} has invalid direction: {direction}",
                    source=bridge_source,
                )
            )

        ros_type = entry["ros_type_name"]
        gz_type = entry["gz_type_name"]
        valid_gz_types = VALID_TYPE_PAIRS.get(ros_type)
        if valid_gz_types is None:
            findings.append(
                Finding(
                    "ERROR",
                    f"Bridge entry {index} has unsupported ROS type: {ros_type}",
                    source=bridge_source,
                )
            )
        elif gz_type not in valid_gz_types:
            findings.append(
                Finding(
                    "ERROR",
                    f"Bridge entry {index} invalid type pairing: {ros_type} -> {gz_type}",
                    source=bridge_source,
                )
            )

        ros_topic = entry["ros_topic_name"]
        by_ros_topic[ros_topic] = entry

        if ros_topic in {"/joint_states", "/tf", "/cmd_vel"} and "/model/" not in entry.get(
            "gz_topic_name", ""
        ):
            findings.append(
                Finding(
                    "WARN",
                    f"Bridge {ros_topic} gz_topic_name should reference /model/<robot>",
                    source=bridge_source,
                )
            )


def _diagnose_launch(pkg_dir: Path, findings: list[Finding]) -> None:
    pkg_name = find_package_name(pkg_dir)
    launch_dir = pkg_dir / "launch"
    if not launch_dir.is_dir():
        return

    launch_files = sorted(
        path
        for path in launch_dir.iterdir()
        if path.suffix in {".xml", ".py"} or path.name.endswith((".launch.xml", ".launch.py"))
    )
    if not launch_files:
        findings.append(
            Finding(
                "WARN",
                "launch/ contains no XML or Python launch files",
                source=pkg_name,
            )
        )
        return

    compliant_files: list[str] = []
    for launch_file in launch_files:
        text = launch_file.read_text(encoding="utf-8")
        rel = _relative(launch_file, pkg_dir)
        launch_source = _source(pkg_name, rel)
        if launch_file.name.endswith(".xml"):
            try:
                ET.fromstring(text)
            except ET.ParseError as exc:
                findings.append(
                    Finding(
                        "ERROR",
                        f"Invalid XML launch file: {exc}",
                        source=launch_source,
                    )
                )
                continue
        checks = {
            "ros_gz_sim gz_sim.launch.py include": (
                "ros_gz_sim" in text and "gz_sim.launch.py" in text
            ),
            "ros_gz_sim create robot_description node": (
                "ros_gz_sim" in text and "create" in text and "robot_description" in text
            ),
            "ros_gz_bridge parameter_bridge node": (
                "ros_gz_bridge" in text and "parameter_bridge" in text
            ),
            "gazebo_bridge.yaml config_file parameter": (
                "config_file" in text and "gazebo_bridge.yaml" in text
            ),
        }
        missing = [label for label, passed in checks.items() if not passed]
        if missing:
            findings.append(
                Finding(
                    "WARN",
                    f"missing Gazebo launch wiring: {', '.join(missing)}",
                    source=launch_source,
                )
            )
        else:
            compliant_files.append(rel)

    if compliant_files:
        findings.append(
            Finding(
                "INFO",
                f"Gazebo launch wiring present in: {', '.join(compliant_files)}",
                source=pkg_name,
            )
        )


def diagnose(args: argparse.Namespace) -> bool:
    context = discover_context(args.path, args.description_package, args.bringup_package)
    findings = [Finding("ERROR", error) for error in context.errors]

    robot_name = args.robot_name
    if context.description_pkg is None:
        findings.append(Finding("WARN", "No *_description package found; skipping xacro checks"))
    else:
        robot_name = robot_name or _diagnose_description(context.description_pkg, findings)

    if context.bringup_pkg is None:
        findings.append(Finding("WARN", "No *_bringup package found; skipping bridge and launch checks"))
    else:
        _diagnose_bringup(context.bringup_pkg, findings)

    _print_report("ROS2 Gazebo Simulation Diagnostics", context, findings)
    return not any(finding.severity == "ERROR" for finding in findings)


def _write_missing(path: Path, content: str, created: list[str], root: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(_relative(path, root))


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


def _append_once(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def _ensure_gazebo_include(
    description_pkg: Path,
    robot_name: str,
    changed: list[str],
    root: Path,
) -> None:
    main_xacro = description_pkg / "urdf" / "main.xacro"
    if not main_xacro.exists():
        return
    content = main_xacro.read_text(encoding="utf-8")
    if f"{robot_name}_gazebo.xacro" in content:
        return
    include_line = (
        f'    <xacro:include filename="$(find {robot_name}_description)/urdf/'
        f'{robot_name}_gazebo.xacro" />'
    )
    lines = content.splitlines()
    insert_at = None
    for index, line in enumerate(lines):
        if f"{robot_name}.urdf.xacro" in line:
            insert_at = index
            break
    if insert_at is None:
        for index, line in enumerate(lines):
            if "</robot>" in line:
                insert_at = index
                break
    if insert_at is None:
        return
    lines.insert(insert_at, include_line)
    main_xacro.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _append_once(changed, _relative(main_xacro, root))


def _ensure_package_exec_depends(
    pkg_dir: Path,
    deps: list[str],
    changed: list[str],
    root: Path,
) -> None:
    package_xml = pkg_dir / "package.xml"
    if not package_xml.exists():
        return
    content = package_xml.read_text(encoding="utf-8")
    missing = [dep for dep in deps if f">{dep}<" not in content]
    if not missing:
        return
    insertion = "".join(f"  <exec_depend>{dep}</exec_depend>\n" for dep in missing)
    if "</package>" in content:
        updated = content.replace("</package>", f"\n{insertion}</package>", 1)
    else:
        updated = content.rstrip() + "\n" + insertion
    package_xml.write_text(updated, encoding="utf-8")
    _append_once(changed, _relative(package_xml, root))


def _ensure_cmake_installs(
    pkg_dir: Path,
    directories: list[str],
    changed: list[str],
    root: Path,
) -> None:
    cmake = pkg_dir / "CMakeLists.txt"
    if not cmake.exists():
        content = (
            "cmake_minimum_required(VERSION 3.8)\n"
            f"project({find_package_name(pkg_dir)})\n\n"
            "find_package(ament_cmake REQUIRED)\n\n"
            "ament_package()\n"
        )
        cmake.write_text(content, encoding="utf-8")
        _append_once(changed, _relative(cmake, root))

    before = cmake.read_text(encoding="utf-8")
    after = add_install_share_directories(before, directories)
    if after != before:
        cmake.write_text(after, encoding="utf-8")
        _append_once(changed, _relative(cmake, root))


# ── Plugin registry helpers ─────────────────────────────────────────────────

def _load_plugin_registry() -> dict[str, dict[str, object]]:
    """Load the plugin registry from references/plugin_registry.yaml.

    Falls back to a simple parser if PyYAML is not installed.
    """
    if not PLUGIN_REGISTRY_PATH.exists():
        return {}
    text = PLUGIN_REGISTRY_PATH.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items() if isinstance(v, dict)}
        return {}
    except ImportError:
        return _parse_simple_plugin_registry(text)


def _parse_simple_plugin_registry(text: str) -> dict[str, dict[str, object]]:
    """Minimal YAML parser for the flat plugin registry structure."""
    registry: dict[str, dict[str, object]] = {}
    current_key: str | None = None
    current_entry: dict[str, object] = {}
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        stripped = line.strip()
        if not line.startswith(" "):
            if current_key is not None:
                registry[current_key] = current_entry
            if stripped.endswith(":"):
                current_key = stripped[:-1].strip()
                current_entry = {}
            else:
                current_key = None
                current_entry = {}
        elif current_key is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value.lower() in ("true", "false"):
                current_entry[key] = value.lower() == "true"
            else:
                current_entry[key] = value
    if current_key is not None:
        registry[current_key] = current_entry
    return registry


def _fetch_plugin_name_from_github(github_dir: str, github_file: str) -> str | None:
    """Fetch the last non-empty line of the .cc file from GitHub.

    The last line typically contains GZ_ADD_PLUGIN_ALIAS(ClassName, \"gz::sim::systems::ClassName\").
    Returns the fully-qualified name, e.g. "gz::sim::systems::DiffDrive".
    """
    url = f"{GZ_SIM_RAW_BASE}/{github_dir}/{github_file}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError):
        return None
    for line in reversed(body.splitlines()):
        line = line.strip()
        if not line:
            continue
        match = re.search(r'GZ_ADD_PLUGIN_ALIAS\s*\([^,]+,\s*"([^"]+)"\)', line)
        if match:
            return match.group(1)
    return None


def _resolve_plugin(plugin_alias: str) -> dict[str, object] | None:
    """Look up a plugin by alias in the registry, or fetch from GitHub.

    Returns a dict with keys: filename, name, category, needs_sensors_system.
    Returns None if the plugin cannot be resolved.
    """
    registry = _load_plugin_registry()
    entry = registry.get(plugin_alias)
    if entry:
        return entry
    # Try fuzzy match: replace spaces/dashes/underscores
    normalised = plugin_alias.lower().replace(" ", "_").replace("-", "_")
    for key, value in registry.items():
        if key.lower().replace(" ", "_").replace("-", "_") == normalised:
            return value
    return None


def _format_plugin_block(plugin_filename: str, plugin_name: str) -> str:
    """Render a <gazebo><plugin .../></gazebo> block for the robot xacro."""
    return (
        f'\n    <gazebo>\n'
        f'        <plugin filename="{plugin_filename}" name="{plugin_name}">\n'
        f'        </plugin>\n'
        f'    </gazebo>\n'
    )


def _add_model_plugin_to_xacro(
    gazebo_xacro_path: Path,
    plugin_filename: str,
    plugin_name: str,
    changed: list[str],
    root: Path,
) -> bool:
    """Insert (or merge) a <gazebo><plugin> block into the robot gazebo xacro.

    Returns True if the file was modified.
    """
    if not gazebo_xacro_path.exists():
        return False
    content = gazebo_xacro_path.read_text(encoding="utf-8")
    if plugin_filename in content and plugin_name in content:
        return False
    block = _format_plugin_block(plugin_filename, plugin_name)
    if "</robot>" in content:
        updated = content.replace("</robot>", f"{block}</robot>", 1)
    else:
        updated = content.rstrip() + "\n" + block
    gazebo_xacro_path.write_text(updated, encoding="utf-8")
    _append_once(changed, _relative(gazebo_xacro_path, root))
    return True


def _world_plugin_line(plugin_filename: str, plugin_name: str) -> str:
    """Render a self-closing <plugin> line for the world SDF."""
    return f'    <plugin filename="{plugin_filename}" name="{plugin_name}"/>'


def _world_sensors_system_block() -> str:
    """Render the Sensors system plugin block with ogre2 render engine."""
    return (
        '    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">\n'
        '      <render_engine>ogre2</render_engine>\n'
        '    </plugin>'
    )


def _add_world_plugin_to_sdf(
    world_sdf_path: Path,
    plugin_filename: str,
    plugin_name: str,
    changed: list[str],
    root: Path,
) -> bool:
    """Add a <plugin> line inside the <world> tag of the world SDF.

    Returns True if the file was modified.
    """
    if not world_sdf_path.exists():
        return False
    content = world_sdf_path.read_text(encoding="utf-8")
    if plugin_filename in content and plugin_name in content:
        return False
    plugin_line = _world_plugin_line(plugin_filename, plugin_name)
    # Insert after the last existing <plugin .../> line inside <world>,
    # otherwise right after the opening <world ...> tag.
    lines = content.splitlines()
    insert_at = None
    in_world = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("<world") or stripped.startswith("<world "):
            in_world = True
        if in_world and "<plugin " in line and "/>" in line:
            insert_at = index + 1
        if in_world and stripped.startswith("</world>"):
            break
    if insert_at is None:
        for index, line in enumerate(lines):
            if "<world" in line:
                insert_at = index + 1
                break
    if insert_at is None:
        return False
    lines.insert(insert_at, plugin_line)
    world_sdf_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _append_once(changed, _relative(world_sdf_path, root))
    return True


def _ensure_sensors_system_in_world(
    world_sdf_path: Path,
    changed: list[str],
    root: Path,
) -> bool:
    """Ensure the Sensors system plugin (with ogre2 render engine) is in the world SDF.

    Returns True if the file was modified.
    """
    if not world_sdf_path.exists():
        return False
    content = world_sdf_path.read_text(encoding="utf-8")
    if "gz-sim-sensors-system" in content and "gz::sim::systems::Sensors" in content:
        return False
    block = _world_sensors_system_block()
    lines = content.splitlines()
    insert_at = None
    in_world = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("<world") or stripped.startswith("<world "):
            in_world = True
        if in_world and "<plugin " in line and "/>" in line:
            insert_at = index + 1
        if in_world and stripped.startswith("</world>"):
            break
    if insert_at is None:
        for index, line in enumerate(lines):
            if "<world" in line:
                insert_at = index + 1
                break
    if insert_at is None:
        return False
    lines.insert(insert_at, block)
    world_sdf_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _append_once(changed, _relative(world_sdf_path, root))
    return True


def _list_available_plugins() -> str:
    """Return a formatted, human-readable table of available plugins."""
    registry = _load_plugin_registry()
    if not registry:
        return "  (plugin registry not found at references/plugin_registry.yaml)"

    # Group by category preserving insertion order
    categories: dict[str, list[tuple[str, dict[str, object]]]] = {
        "model": [],
        "sensor": [],
        "world": [],
    }
    for alias, entry in registry.items():
        cat = str(entry.get("category", "model"))
        categories.setdefault(cat, []).append((alias, entry))

    category_titles: list[tuple[str, str, str]] = [
        ("model", "Model plugins", "added to <gazebo> in the robot xacro"),
        ("sensor", "Sensor plugins", "added as <plugin/> in the world .sdf"),
        ("world", "World plugins", "added as <plugin/> in the world .sdf"),
    ]

    lines: list[str] = []
    for cat_key, title, subtitle in category_titles:
        entries = categories.get(cat_key, [])
        if not entries:
            continue
        lines.append("")
        lines.append(f"  {title} ({subtitle})")
        lines.append("")
        # Column widths: alias | filename | name | description
        alias_w = max(len(a) for a, _ in entries)
        alias_w = max(alias_w, len("alias"))
        file_w = max(len(str(e.get("filename", ""))) for _, e in entries)
        file_w = max(file_w, len("filename"))
        name_w = max(len(str(e.get("name", ""))) for _, e in entries)
        name_w = max(name_w, len("name"))
        desc_w = max(len(str(e.get("description", ""))) for _, e in entries)
        desc_w = max(desc_w, len("description"))

        # Header
        lines.append(
            f"  {'alias':<{alias_w}}  {'filename':<{file_w}}  {'name':<{name_w}}  {'description'}"
        )
        lines.append(
            f"  {'─' * alias_w}  {'─' * file_w}  {'─' * name_w}  {'─' * desc_w}"
        )
        for alias, entry in entries:
            filename = str(entry.get("filename", ""))
            name = str(entry.get("name", ""))
            desc = str(entry.get("description", ""))
            lines.append(
                f"  {alias:<{alias_w}}  {filename:<{file_w}}  {name:<{name_w}}  {desc}"
            )

    lines.append("")
    lines.append("  Usage:  ros-devkit gazebo-simulation --add-plugin --plugin <alias>")
    return "\n".join(lines)


def add_plugin(args: argparse.Namespace) -> bool:
    """Add a Gazebo system plugin to the robot's gazebo xacro and/or world SDF."""
    plugin_alias = args.plugin
    context = discover_context(args.path, args.description_package, args.bringup_package)
    findings = [Finding("ERROR", error) for error in context.errors]
    changed: list[str] = []

    if args.list_plugins:
        print("Available Gazebo Sim plugins:")
        print(_list_available_plugins())
        return True

    if not plugin_alias:
        findings.append(Finding("ERROR", "No plugin specified. Use --plugin <name> or --list-plugins."))
        _print_report("ROS2 Gazebo Simulation — Add Plugin", context, findings)
        return False

    plugin = _resolve_plugin(plugin_alias)
    if plugin is None:
        findings.append(
            Finding(
                "ERROR",
                f"Unknown plugin alias '{plugin_alias}'. Use --list-plugins to see available plugins.",
            )
        )
        _print_report("ROS2 Gazebo Simulation — Add Plugin", context, findings)
        return False

    plugin_filename = str(plugin.get("filename", ""))
    plugin_name = str(plugin.get("name", ""))
    category = str(plugin.get("category", "model"))
    needs_sensors = bool(plugin.get("needs_sensors_system", False))

    # If the name is missing or generic, try to fetch from GitHub
    if not plugin_name and plugin.get("github_dir") and plugin.get("github_file"):
        fetched = _fetch_plugin_name_from_github(
            str(plugin["github_dir"]), str(plugin["github_file"])
        )
        if fetched:
            plugin_name = fetched
            findings.append(Finding("INFO", f"Fetched plugin name from GitHub: {plugin_name}"))
        else:
            findings.append(
                Finding("WARN", f"Could not fetch plugin name from GitHub for '{plugin_alias}'")
            )

    if not plugin_filename or not plugin_name:
        findings.append(
            Finding(
                "ERROR",
                f"Could not resolve filename and/or name for plugin '{plugin_alias}'",
            )
        )
        _print_report("ROS2 Gazebo Simulation — Add Plugin", context, findings)
        return False

    findings.append(
        Finding(
            "INFO",
            f"Plugin: filename='{plugin_filename}', name='{plugin_name}', category='{category}'",
        )
    )

    robot_name = args.robot_name

    # Determine robot name from description package
    if context.description_pkg is not None:
        pkg_name = find_package_name(context.description_pkg)
        robot_name = robot_name or robot_name_from_package(pkg_name)
    elif context.bringup_pkg is not None:
        bringup_name = find_package_name(context.bringup_pkg)
        robot_name = robot_name or bringup_name[: -len("_bringup")] if bringup_name.endswith("_bringup") else robot_name

    # Model-level plugins go in the <gazebo> tag of the robot xacro
    if category == "model":
        if context.description_pkg is None:
            findings.append(Finding("ERROR", "No *_description package found; cannot add model plugin"))
        elif not robot_name:
            findings.append(Finding("ERROR", "Could not determine robot name; pass --robot-name"))
        else:
            gazebo_xacro = context.description_pkg / "urdf" / f"{robot_name}_gazebo.xacro"
            if not gazebo_xacro.exists():
                findings.append(
                    Finding(
                        "WARN",
                        f"Gazebo xacro not found at {gazebo_xacro}; creating it with --setup first is recommended",
                        source=find_package_name(context.description_pkg),
                    )
                )
            else:
                if _add_model_plugin_to_xacro(
                    gazebo_xacro, plugin_filename, plugin_name, changed, context.root
                ):
                    findings.append(
                        Finding(
                            "INFO",
                            f"Added <gazebo><plugin> block to {robot_name}_gazebo.xacro",
                            source=_source(
                                find_package_name(context.description_pkg),
                                f"urdf/{robot_name}_gazebo.xacro",
                            ),
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            "INFO",
                            f"Plugin already present in {robot_name}_gazebo.xacro",
                        )
                    )

    # Sensor and world plugins go in the world .sdf
    if category in ("sensor", "world"):
        if context.bringup_pkg is None:
            findings.append(Finding("ERROR", "No *_bringup package found; cannot add world plugin"))
        else:
            world_name = args.world_name
            world_sdf = context.bringup_pkg / "worlds" / f"{world_name}.sdf"
            if not world_sdf.exists():
                findings.append(
                    Finding(
                        "WARN",
                        f"World SDF not found at {world_sdf}; creating it with --setup first is recommended",
                        source=find_package_name(context.bringup_pkg),
                    )
                )
            else:
                # For sensor rendering plugins (lidar, camera, etc.), skip adding
                # the Sensors plugin itself to the world — instead we add the
                # Sensors system block below.
                skip_world_line = needs_sensors and category == "sensor"
                if not skip_world_line:
                    if _add_world_plugin_to_sdf(
                        world_sdf, plugin_filename, plugin_name, changed, context.root
                    ):
                        findings.append(
                            Finding(
                                "INFO",
                                f"Added <plugin> line to {world_name}.sdf",
                                source=_source(
                                    find_package_name(context.bringup_pkg),
                                    f"worlds/{world_name}.sdf",
                                ),
                            )
                        )
                    else:
                        findings.append(
                            Finding("INFO", f"Plugin already present in {world_name}.sdf")
                        )

                if needs_sensors:
                    if _ensure_sensors_system_in_world(world_sdf, changed, context.root):
                        findings.append(
                            Finding(
                                "INFO",
                                f"Added Sensors system plugin (ogre2) to {world_name}.sdf",
                                source=_source(
                                    find_package_name(context.bringup_pkg),
                                    f"worlds/{world_name}.sdf",
                                ),
                            )
                        )
                    else:
                        findings.append(
                            Finding("INFO", f"Sensors system plugin already present in {world_name}.sdf")
                        )

    findings.extend(Finding("INFO", f"Updated: {path}") for path in changed)
    if not changed:
        findings.append(Finding("INFO", "No files were modified"))

    _print_report("ROS2 Gazebo Simulation — Add Plugin", context, findings)
    return not any(finding.severity == "ERROR" for finding in findings)


def setup(args: argparse.Namespace) -> bool:
    context = discover_context(args.path, args.description_package, args.bringup_package)
    findings = [Finding("ERROR", error) for error in context.errors]
    created: list[str] = []
    changed: list[str] = []

    robot_name = args.robot_name
    if context.description_pkg is not None:
        pkg_name = find_package_name(context.description_pkg)
        robot_name = robot_name or robot_name_from_package(pkg_name)
        gazebo_xacro = context.description_pkg / "urdf" / f"{robot_name}_gazebo.xacro"
        _write_missing(gazebo_xacro, _gazebo_xacro(robot_name), created, context.root)
        _ensure_gazebo_include(context.description_pkg, robot_name, changed, context.root)
    else:
        findings.append(Finding("WARN", "No *_description package found; skipped Gazebo xacro setup"))

    if context.bringup_pkg is not None:
        bringup_name = find_package_name(context.bringup_pkg)
        robot_name = robot_name or args.robot_name or bringup_name[: -len("_bringup")]
        for directory in BRINGUP_INSTALL_DIRS:
            path = context.bringup_pkg / directory
            if not path.exists():
                path.mkdir(parents=True)
                created.append(_relative(path, context.root) + "/")
        _write_missing(
            context.bringup_pkg / "config" / "gazebo_bridge.yaml",
            _bridge_yaml(robot_name, args.world_name),
            created,
            context.root,
        )
        _write_missing(
            context.bringup_pkg / "worlds" / f"{args.world_name}.sdf",
            _world_sdf(args.world_name),
            created,
            context.root,
        )
        _write_missing(
            context.bringup_pkg / "launch" / "gazebo.launch.xml",
            _gazebo_launch_xml(bringup_name, args.world_name),
            created,
            context.root,
        )
        _ensure_cmake_installs(
            context.bringup_pkg,
            list(BRINGUP_INSTALL_DIRS),
            changed,
            context.root,
        )
        _ensure_package_exec_depends(
            context.bringup_pkg,
            ["ros_gz_sim", "ros_gz_bridge"],
            changed,
            context.root,
        )
    else:
        findings.append(Finding("WARN", "No *_bringup package found; skipped bridge and launch setup"))

    findings.extend(Finding("INFO", f"Created: {path}") for path in created)
    findings.extend(Finding("INFO", f"Updated: {path}") for path in changed)
    if not created and not changed:
        findings.append(Finding("INFO", "No missing Gazebo scaffold files found"))

    _print_report("ROS2 Gazebo Simulation Setup", context, findings)
    return not any(finding.severity == "ERROR" for finding in findings)


def _print_report(title: str, context: Context, findings: list[Finding]) -> None:
    print()
    print(title)
    print(f"Root        : {context.root}")
    print(f"Description : {context.description_pkg or 'not found'}")
    print(f"Bringup     : {context.bringup_pkg or 'not found'}")
    print()
    for finding in findings:
        print_finding(finding)
    if not findings:
        print_finding(Finding("INFO", "No findings"))
    elif not any(finding.severity == "ERROR" for finding in findings):
        print_finding(Finding("INFO", "No errors found"))
    else:
        print_finding(Finding("ERROR", "Errors found; fix before proceeding"))
    print()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ROS2 Gazebo simulation workflows.")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--diagnose",
        dest="mode",
        action="store_const",
        const="diagnose",
        help="inspect Gazebo simulation wiring",
    )
    modes.add_argument(
        "--setup",
        dest="mode",
        action="store_const",
        const="setup",
        help="create missing Gazebo simulation scaffold files",
    )
    modes.add_argument(
        "--add-plugin",
        dest="mode",
        action="store_const",
        const="add_plugin",
        help="add a Gazebo system plugin to the robot xacro and/or world SDF",
    )
    parser.add_argument("path", nargs="?", help="Project root or package path")
    parser.add_argument("--description-package", help="Explicit <name>_description package path")
    parser.add_argument("--bringup-package", help="Explicit <name>_bringup package path")
    parser.add_argument("--robot-name", help="Robot/model name when package discovery is insufficient")
    parser.add_argument("--world-name", default="test_world", help="Gazebo world name for setup")
    parser.add_argument("--plugin", help="Plugin alias to add (use --list-plugins to see available)")
    parser.add_argument(
        "--list-plugins",
        action="store_true",
        help="List all available Gazebo Sim plugin aliases",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.mode == "diagnose":
        return 0 if diagnose(args) else 1
    if args.mode == "setup":
        return 0 if setup(args) else 1
    if args.mode == "add_plugin":
        return 0 if add_plugin(args) else 1
    raise AssertionError(f"unhandled mode: {args.mode}")


if __name__ == "__main__":
    sys.exit(main())
