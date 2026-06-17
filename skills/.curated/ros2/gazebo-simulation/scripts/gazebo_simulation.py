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

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SHARED_SCRIPTS))

from cmake import add_install_share_directories  # noqa: E402

DISCOVERY_SKIP_DIRS = {".git", ".venv", "__pycache__", "build", "install", "log"}
BRINGUP_INSTALL_DIRS = ("launch", "config", "worlds")
REQUIRED_BRIDGE_KEYS = {
    "ros_topic_name",
    "gz_topic_name",
    "ros_type_name",
    "gz_type_name",
    "direction",
}
VALID_DIRECTIONS = {"GZ_TO_ROS", "ROS_TO_GZ", "BIDIRECTIONAL"}
EXPECTED_BRIDGES = {
    "/clock": {
        "ros_type_name": "rosgraph_msgs/msg/Clock",
        "gz_type_name": "gz.msgs.Clock",
        "direction": "GZ_TO_ROS",
    },
    "/joint_states": {
        "ros_type_name": "sensor_msgs/msg/JointState",
        "gz_type_name": "gz.msgs.Model",
        "direction": "GZ_TO_ROS",
    },
    "/tf": {
        "ros_type_name": "tf2_msgs/msg/TFMessage",
        "gz_type_name": "gz.msgs.Pose_V",
        "direction": "GZ_TO_ROS",
    },
    "/cmd_vel": {
        "ros_type_name": "geometry_msgs/msg/Twist",
        "gz_type_name": "gz.msgs.Twist",
        "direction": "ROS_TO_GZ",
    },
}


@dataclass(frozen=True)
class Finding:
    severity: str
    message: str


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

    findings.append(Finding("INFO", f"Description package: {pkg_name} ({pkg_dir})"))

    if not urdf_dir.is_dir():
        findings.append(Finding("ERROR", f"Missing description urdf/ directory: {pkg_dir / 'urdf'}"))
        return robot_name

    xacro_files = sorted(urdf_dir.glob("*.xacro"))
    if not xacro_files:
        findings.append(Finding("ERROR", f"No xacro files found under {_relative(urdf_dir, pkg_dir)}"))

    for xacro_file in xacro_files:
        try:
            root = ET.parse(xacro_file).getroot()
        except ET.ParseError as exc:
            findings.append(Finding("ERROR", f"Invalid XML in {_relative(xacro_file, pkg_dir)}: {exc}"))
            continue
        for link in root.iter():
            if _local_name(link.tag) != "link":
                continue
            link_name = link.attrib.get("name", "").strip()
            if _link_is_footprint(link_name):
                findings.append(Finding("INFO", f"Footprint link exempt from physics tags: {link_name}"))
                continue
            label = link_name or f"unnamed link in {_relative(xacro_file, pkg_dir)}"
            if not _has_direct_child(link, "collision"):
                findings.append(Finding("ERROR", f"Link missing collision tag: {label}"))
            if not _has_direct_child(link, "inertial"):
                findings.append(Finding("ERROR", f"Link missing inertial tag: {label}"))

    gazebo_xacro = urdf_dir / f"{robot_name}_gazebo.xacro"
    if not gazebo_xacro.exists():
        findings.append(Finding("ERROR", f"Missing Gazebo xacro: urdf/{robot_name}_gazebo.xacro"))
    else:
        findings.append(Finding("INFO", f"Found Gazebo xacro: urdf/{robot_name}_gazebo.xacro"))
        try:
            root = ET.parse(gazebo_xacro).getroot()
            if not any(_local_name(element.tag) == "gazebo" for element in root.iter()):
                findings.append(
                    Finding("WARN", f"urdf/{robot_name}_gazebo.xacro contains no <gazebo> elements")
                )
        except ET.ParseError as exc:
            findings.append(Finding("ERROR", f"Invalid XML in urdf/{robot_name}_gazebo.xacro: {exc}"))

    entrypoint = urdf_dir / "main.xacro"
    if entrypoint.exists():
        content = entrypoint.read_text(encoding="utf-8")
        if f"{robot_name}_gazebo.xacro" in content:
            findings.append(Finding("INFO", f"main.xacro includes {robot_name}_gazebo.xacro"))
        else:
            findings.append(Finding("WARN", f"main.xacro does not include {robot_name}_gazebo.xacro"))
    else:
        findings.append(Finding("WARN", "Missing urdf/main.xacro; cannot check Gazebo xacro include"))

    return robot_name


def _diagnose_bringup(pkg_dir: Path, findings: list[Finding]) -> None:
    pkg_name = find_package_name(pkg_dir)
    findings.append(Finding("INFO", f"Bringup package: {pkg_name} ({pkg_dir})"))

    for rel_path in ("package.xml", "CMakeLists.txt"):
        if (pkg_dir / rel_path).exists():
            findings.append(Finding("INFO", f"Found bringup file: {rel_path}"))
        else:
            findings.append(Finding("ERROR", f"Bringup package missing {rel_path}"))

    launch_dir = pkg_dir / "launch"
    if launch_dir.is_dir():
        findings.append(Finding("INFO", "Found bringup launch/ directory"))
    else:
        findings.append(Finding("ERROR", "Bringup package missing launch/ directory"))

    cmake = pkg_dir / "CMakeLists.txt"
    installed_dirs: set[str] = set()
    if cmake.exists():
        installed_dirs = _installed_share_directories(cmake.read_text(encoding="utf-8"))
        if "launch" in installed_dirs:
            findings.append(Finding("INFO", "CMakeLists.txt installs launch/"))
        else:
            findings.append(
                Finding(
                    "ERROR",
                    "CMakeLists.txt must install launch/ to share/${PROJECT_NAME}",
                )
            )
        for directory in ("config", "worlds"):
            if (pkg_dir / directory).exists() and directory not in installed_dirs:
                findings.append(
                    Finding(
                        "WARN",
                        f"CMakeLists.txt does not install present {directory}/ directory",
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
    bridge = pkg_dir / "config" / "gazebo_bridge.yaml"
    if not bridge.exists():
        findings.append(Finding("WARN", "Missing Gazebo bridge: config/gazebo_bridge.yaml"))
        return

    findings.append(Finding("INFO", "Found Gazebo bridge: config/gazebo_bridge.yaml"))
    try:
        entries = _parse_bridge_yaml(bridge)
    except (OSError, ValueError) as exc:
        findings.append(Finding("ERROR", f"Invalid gazebo_bridge.yaml: {exc}"))
        return

    if not entries:
        findings.append(Finding("ERROR", "gazebo_bridge.yaml has no bridge entries"))
        return

    by_ros_topic: dict[str, dict[str, str]] = {}
    for index, entry in enumerate(entries, start=1):
        missing = sorted(REQUIRED_BRIDGE_KEYS - set(entry))
        if missing:
            findings.append(
                Finding(
                    "ERROR",
                    f"Bridge entry {index} missing required keys: {', '.join(missing)}",
                )
            )
            continue
        direction = entry["direction"]
        if direction not in VALID_DIRECTIONS:
            findings.append(
                Finding("ERROR", f"Bridge entry {index} has invalid direction: {direction}")
            )
        by_ros_topic[entry["ros_topic_name"]] = entry

    for topic, expected in EXPECTED_BRIDGES.items():
        entry = by_ros_topic.get(topic)
        if entry is None:
            findings.append(Finding("WARN", f"Bridge missing expected ROS topic: {topic}"))
            continue
        for key, expected_value in expected.items():
            actual = entry.get(key)
            if actual != expected_value:
                findings.append(
                    Finding(
                        "WARN",
                        f"Bridge {topic} expected {key}={expected_value}, found {actual}",
                    )
                )
        if topic in {"/joint_states", "/tf", "/cmd_vel"} and "/model/" not in entry.get(
            "gz_topic_name", ""
        ):
            findings.append(
                Finding("WARN", f"Bridge {topic} gz_topic_name should reference /model/<robot>")
            )


def _diagnose_launch(pkg_dir: Path, findings: list[Finding]) -> None:
    launch_dir = pkg_dir / "launch"
    if not launch_dir.is_dir():
        return

    launch_files = sorted(
        path
        for path in launch_dir.iterdir()
        if path.suffix in {".xml", ".py"} or path.name.endswith((".launch.xml", ".launch.py"))
    )
    if not launch_files:
        findings.append(Finding("WARN", "launch/ contains no XML or Python launch files"))
        return

    compliant_files: list[str] = []
    for launch_file in launch_files:
        text = launch_file.read_text(encoding="utf-8")
        rel = _relative(launch_file, pkg_dir)
        if launch_file.name.endswith(".xml"):
            try:
                ET.fromstring(text)
            except ET.ParseError as exc:
                findings.append(Finding("ERROR", f"Invalid XML launch file {rel}: {exc}"))
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
            findings.append(Finding("WARN", f"{rel} missing Gazebo launch wiring: {', '.join(missing)}"))
        else:
            compliant_files.append(rel)

    if compliant_files:
        findings.append(Finding("INFO", f"Gazebo launch wiring present in: {', '.join(compliant_files)}"))


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
        print(f"{finding.severity}: {finding.message}")
    if not findings:
        print("INFO: No findings")
    elif not any(finding.severity == "ERROR" for finding in findings):
        print("INFO: No errors found")
    else:
        print("ERROR: Errors found; fix before proceeding")
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
    parser.add_argument("path", nargs="?", help="Project root or package path")
    parser.add_argument("--description-package", help="Explicit <name>_description package path")
    parser.add_argument("--bringup-package", help="Explicit <name>_bringup package path")
    parser.add_argument("--robot-name", help="Robot/model name when package discovery is insufficient")
    parser.add_argument("--world-name", default="test_world", help="Gazebo world name for setup")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.mode == "diagnose":
        return 0 if diagnose(args) else 1
    if args.mode == "setup":
        return 0 if setup(args) else 1
    raise AssertionError(f"unhandled mode: {args.mode}")


if __name__ == "__main__":
    sys.exit(main())
