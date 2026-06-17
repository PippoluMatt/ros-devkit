#!/usr/bin/env python3
"""Mode-based CLI for the ros2-description-scaffold skill."""

from __future__ import annotations

import argparse
import copy
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from scaffold import (  # noqa: E402
    MATERIALS_XACRO,
    RVIZ_CONFIG,
    URDF_XACRO,
    main_xacro,
    scaffold,
    sensor_xacro,
)
from validate import (  # noqa: E402
    find_package_name,
    resolve_package_directory,
    robot_name_from_package,
    validate,
)


XACRO_NS = "http://www.ros.org/wiki/xacro"
ET.register_namespace("xacro", XACRO_NS)

KNOWN_SENSOR_TOKENS = {
    "camera",
    "depth",
    "gps",
    "imu",
    "laser",
    "lidar",
    "radar",
    "range",
    "sonar",
    "tof",
    "ultrasonic",
}


def _parse_sensors(value: str) -> list[str]:
    sensors: list[str] = []
    for item in value.split(","):
        sensor = item.strip()
        if sensor and sensor not in sensors:
            sensors.append(sensor)
    return sensors


def _package_xml(pkg_name: str, robot_name: str) -> str:
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


def _cmakelists(pkg_name: str) -> str:
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


def _write_missing(pkg_dir: Path, rel_path: str, content: str, created: list[str]) -> None:
    path = pkg_dir / rel_path
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(rel_path)


def _repair_package(pkg_dir: Path, sensors: list[str]) -> int:
    pkg_dir = pkg_dir.resolve()
    if not pkg_dir.exists():
        print(f"ERROR: Package directory does not exist: {pkg_dir}")
        return 1
    if not pkg_dir.is_dir():
        print(f"ERROR: Not a directory: {pkg_dir}")
        return 1

    pkg_name = find_package_name(pkg_dir)
    robot_name = robot_name_from_package(pkg_name)
    created: list[str] = []

    for rel_dir in ["urdf", "meshes", "rviz"]:
        path = pkg_dir / rel_dir
        if not path.exists():
            path.mkdir(parents=True)
            created.append(f"{rel_dir}/")

    _write_missing(pkg_dir, "CMakeLists.txt", _cmakelists(pkg_name), created)
    _write_missing(pkg_dir, "package.xml", _package_xml(pkg_name, robot_name), created)

    if not (pkg_dir / "urdf" / "main.xacro").exists() and not (
        pkg_dir / "urdf" / "main.urdf.xacro"
    ).exists():
        _write_missing(pkg_dir, "urdf/main.xacro", main_xacro(robot_name, sensors), created)

    _write_missing(
        pkg_dir,
        "urdf/materials.xacro",
        MATERIALS_XACRO.format(name=robot_name),
        created,
    )
    _write_missing(
        pkg_dir,
        f"urdf/{robot_name}.urdf.xacro",
        URDF_XACRO.format(name=robot_name),
        created,
    )
    for sensor in sensors:
        _write_missing(
            pkg_dir,
            f"urdf/{sensor}.xacro",
            sensor_xacro(robot_name, sensor),
            created,
        )
    _write_missing(pkg_dir, f"rviz/{robot_name}.rviz", RVIZ_CONFIG, created)

    print(f"Package : {pkg_name}")
    print(f"Path    : {pkg_dir}")
    if created:
        print(f"Created : {', '.join(created)}")
    else:
        print("INFO: No missing minimal files or directories found")
    print(f"Verify  : python3 {Path(__file__).name} --verify {pkg_dir}")
    return 0


def _create(target: str, args: argparse.Namespace) -> int:
    target_path = Path(target).expanduser()
    sensors = _parse_sensors(args.sensors)

    if target_path.exists():
        pkg_dir = resolve_package_directory(target_path)
        if pkg_dir is None:
            return 1
        return _repair_package(pkg_dir, sensors)

    if target_path.parent != Path("."):
        robot_name = robot_name_from_package(target_path.name)
        destination = target_path.parent
    else:
        robot_name = robot_name_from_package(target)
        destination = args.destination

    scaffold(
        name=robot_name,
        sensors=sensors,
        destination=Path(destination).expanduser(),
        maintainer=args.maintainer,
        email=args.email,
        license_type=args.license,
    )
    return 0


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _looks_include_only(path: Path) -> bool:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return False
    children = [child for child in list(root) if isinstance(child.tag, str)]
    if not children:
        return False
    return all(_local_name(child.tag) == "include" for child in children)


def _resolve_split_source(pkg_dir: Path, source: str | None) -> Path | None:
    urdf_dir = pkg_dir / "urdf"
    if source:
        source_path = Path(source).expanduser()
        if not source_path.is_absolute():
            package_relative = pkg_dir / source_path
            urdf_relative = urdf_dir / source_path
            source_path = package_relative if package_relative.exists() else urdf_relative
        if not source_path.exists():
            print(f"ERROR: Split source not found: {source}")
            return None
        return source_path.resolve()

    candidates = [
        path
        for path in sorted(urdf_dir.glob("*.xacro"))
        if not path.name.endswith(".unsplit.xacro")
        and path.name not in {"materials.xacro"}
        and not _looks_include_only(path)
    ]

    if len(candidates) == 1:
        return candidates[0].resolve()

    if not candidates:
        print("ERROR: No monolithic xacro source found under urdf/")
    else:
        print("ERROR: Multiple xacro split candidates found; pass --source")
        for candidate in candidates:
            print(f"INFO: Candidate: {candidate.relative_to(pkg_dir)}")
    return None


def _backup_path(source: Path) -> Path:
    if source.name.endswith(".xacro"):
        return source.with_name(source.name[: -len(".xacro")] + ".unsplit.xacro")
    return source.with_name(source.name + ".unsplit")


def _sensor_name_from_text(value: str | None, expected: list[str]) -> str | None:
    if not value:
        return None
    name = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()
    for suffix in ["_link", "_joint", "_sensor"]:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    tokens = expected + sorted(KNOWN_SENSOR_TOKENS)
    for token in tokens:
        token = token.lower()
        if name == token or name.endswith(f"_{token}") or f"_{token}_" in name:
            return name
    return None


def _element_sensor_name(element: ET.Element, expected: list[str]) -> str | None:
    tag = _local_name(element.tag)
    if tag == "link":
        return _sensor_name_from_text(element.attrib.get("name"), expected)
    if tag == "joint":
        sensor = _sensor_name_from_text(element.attrib.get("name"), expected)
        if sensor:
            return sensor
        for child in element:
            if _local_name(child.tag) == "child":
                return _sensor_name_from_text(child.attrib.get("link"), expected)
    if tag == "gazebo":
        sensor = _sensor_name_from_text(element.attrib.get("reference"), expected)
        if sensor:
            return sensor
    if tag == "sensor":
        return _sensor_name_from_text(
            element.attrib.get("name") or element.attrib.get("type"),
            expected,
        )
    for descendant in element.iter():
        if descendant is element:
            continue
        if _local_name(descendant.tag) == "sensor":
            sensor = _sensor_name_from_text(
                descendant.attrib.get("name") or descendant.attrib.get("type"),
                expected,
            )
            if sensor:
                return sensor
    return None


def _serialize_element(element: ET.Element) -> str:
    clone = copy.deepcopy(element)
    ET.indent(clone, space="    ")
    text = ET.tostring(clone, encoding="unicode")
    return "\n".join(f"    {line}" if line.strip() else line for line in text.splitlines())


def _wrap_robot(robot_name: str, elements: list[ET.Element]) -> str:
    if not elements:
        body = "    <!-- Add definitions here -->"
    else:
        body = "\n\n".join(_serialize_element(element) for element in elements)
    return f"""<?xml version="1.0" ?>
<robot name="{robot_name}" xmlns:xacro="{XACRO_NS}">

{body}

</robot>
"""


def _split(target: str | None, args: argparse.Namespace) -> int:
    pkg_dir = resolve_package_directory(target)
    if pkg_dir is None:
        return 1

    if not pkg_dir.is_dir():
        print(f"ERROR: Package directory not found: {pkg_dir}")
        return 1

    pkg_name = find_package_name(pkg_dir)
    robot_name = robot_name_from_package(pkg_name)
    urdf_dir = pkg_dir / "urdf"
    if not urdf_dir.is_dir():
        print(f"ERROR: Missing urdf/ directory: {urdf_dir}")
        return 1

    source = _resolve_split_source(pkg_dir, args.source)
    if source is None:
        return 1

    try:
        root = ET.parse(source).getroot()
    except ET.ParseError as exc:
        print(f"ERROR: Split source is not valid XML: {exc}")
        return 1

    expected_sensors = _parse_sensors(args.sensors)
    material_elements: list[ET.Element] = []
    body_elements: list[ET.Element] = []
    sensor_elements: dict[str, list[ET.Element]] = {}

    for child in list(root):
        if not isinstance(child.tag, str):
            continue
        if _local_name(child.tag) == "material":
            material_elements.append(child)
            continue
        sensor_name = _element_sensor_name(child, expected_sensors)
        if sensor_name:
            sensor_elements.setdefault(sensor_name, []).append(child)
            continue
        body_elements.append(child)

    sensor_names = sorted(sensor_elements)
    main_path = urdf_dir / "main.xacro"
    materials_path = urdf_dir / "materials.xacro"
    body_path = urdf_dir / f"{robot_name}.urdf.xacro"
    output_paths = [main_path, materials_path, body_path]
    output_paths.extend(urdf_dir / f"{sensor}.xacro" for sensor in sensor_names)

    conflicts = [
        path.relative_to(pkg_dir)
        for path in output_paths
        if path.exists() and path.resolve() != source
    ]
    if conflicts:
        print("ERROR: Refusing to overwrite existing modular files")
        for conflict in conflicts:
            print(f"INFO: Existing file: {conflict}")
        return 1

    backup = _backup_path(source)
    if backup.exists():
        print(f"ERROR: Backup file already exists: {backup.relative_to(pkg_dir)}")
        return 1

    source.rename(backup)

    created: list[str] = []
    materials_content = (
        _wrap_robot(robot_name, material_elements)
        if material_elements
        else MATERIALS_XACRO.format(name=robot_name)
    )
    body_content = (
        _wrap_robot(robot_name, body_elements)
        if body_elements
        else URDF_XACRO.format(name=robot_name)
    )

    main_path.write_text(main_xacro(robot_name, sensor_names), encoding="utf-8")
    created.append(str(main_path.relative_to(pkg_dir)))
    materials_path.write_text(materials_content, encoding="utf-8")
    created.append(str(materials_path.relative_to(pkg_dir)))
    body_path.write_text(body_content, encoding="utf-8")
    created.append(str(body_path.relative_to(pkg_dir)))

    for sensor in sensor_names:
        path = urdf_dir / f"{sensor}.xacro"
        path.write_text(_wrap_robot(robot_name, sensor_elements[sensor]), encoding="utf-8")
        created.append(str(path.relative_to(pkg_dir)))

    print(f"Package : {pkg_name}")
    print(f"Path    : {pkg_dir}")
    print(f"Renamed : {source.relative_to(pkg_dir)} -> {backup.relative_to(pkg_dir)}")
    print(f"Created : {', '.join(created)}")
    if not sensor_names:
        print("WARN: No sensor-specific blocks detected; definitions stayed in robot body file")
    print(f"Verify  : python3 {Path(__file__).name} --verify {pkg_dir}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run ros2-description-scaffold workflows."
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--verify",
        metavar="PACKAGE_DIR",
        nargs="?",
        const="",
        help="verify package structure; discover one package when omitted",
    )
    modes.add_argument(
        "--create",
        metavar="TARGET",
        nargs="?",
        const="",
        help="create a new package or repair an existing package directory",
    )
    modes.add_argument(
        "--split",
        metavar="PACKAGE_DIR",
        nargs="?",
        const="",
        help="split a monolithic xacro; discover one package when omitted",
    )
    parser.add_argument("--sensors", default="", help="Comma-separated sensor names")
    parser.add_argument(
        "--destination-directory",
        "--dir",
        dest="destination",
        default=".",
        help="Directory where a new package is created",
    )
    parser.add_argument("--source", help="Source xacro for --split when ambiguous")
    parser.add_argument("--maintainer", default=None, help="Maintainer name for ros2 pkg create")
    parser.add_argument("--email", default=None, help="Maintainer email for ros2 pkg create")
    parser.add_argument("--license", default=None, help="License for ros2 pkg create")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.verify is not None:
        return 0 if validate(args.verify or None) else 1
    if args.create is not None:
        if args.create:
            return _create(args.create, args)
        pkg_dir = resolve_package_directory(None)
        if pkg_dir is None:
            return 1
        return _repair_package(pkg_dir, _parse_sensors(args.sensors))
    if args.split is not None:
        return _split(args.split or None, args)
    raise AssertionError("unreachable mode")


if __name__ == "__main__":
    sys.exit(main())
