"""Gazebo bridge YAML parsing and validation."""

from __future__ import annotations

from pathlib import Path

from package_xml_lib.parsing import read_package_name
from utils.diagnostics import Finding, source as _source


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
    pkg_name = read_package_name(pkg_dir / "package.xml")
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
