"""Split monolithic xacro files into the standard modular layout."""

from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from package_xml_lib.parsing import read_package_name, robot_name_from_package
from utils.fs import relative
from utils.xml import local_name

from .discovery import resolve_package_directory
from .templates import MATERIALS_XACRO, URDF_XACRO, main_xacro


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


def _looks_include_only(path: Path) -> bool:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return False
    children = [child for child in list(root) if isinstance(child.tag, str)]
    if not children:
        return False
    return all(local_name(child.tag) == "include" for child in children)


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
            print(f"INFO: Candidate: {relative(candidate, pkg_dir)}")
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
    tag = local_name(element.tag)
    if tag == "link":
        return _sensor_name_from_text(element.attrib.get("name"), expected)
    if tag == "joint":
        sensor = _sensor_name_from_text(element.attrib.get("name"), expected)
        if sensor:
            return sensor
        for child in element:
            if local_name(child.tag) == "child":
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
        if local_name(descendant.tag) == "sensor":
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


def split(target: str | None, sensors: list[str], source: str | None) -> int:
    pkg_dir = resolve_package_directory(target)
    if pkg_dir is None:
        return 1

    if not pkg_dir.is_dir():
        print(f"ERROR: Package directory not found: {pkg_dir}")
        return 1

    pkg_name = read_package_name(pkg_dir / "package.xml")
    robot_name = robot_name_from_package(pkg_name)
    urdf_dir = pkg_dir / "urdf"
    if not urdf_dir.is_dir():
        print(f"ERROR: Missing urdf/ directory: {urdf_dir}")
        return 1

    split_source = _resolve_split_source(pkg_dir, source)
    if split_source is None:
        return 1

    try:
        root = ET.parse(split_source).getroot()
    except ET.ParseError as error:
        print(f"ERROR: Split source is not valid XML: {error}")
        return 1

    material_elements: list[ET.Element] = []
    body_elements: list[ET.Element] = []
    sensor_elements: dict[str, list[ET.Element]] = {}

    for child in list(root):
        if not isinstance(child.tag, str):
            continue
        if local_name(child.tag) == "material":
            material_elements.append(child)
            continue
        sensor_name = _element_sensor_name(child, sensors)
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
        if path.exists() and path.resolve() != split_source
    ]
    if conflicts:
        print("ERROR: Refusing to overwrite existing modular files")
        for conflict in conflicts:
            print(f"INFO: Existing file: {conflict}")
        return 1

    backup = _backup_path(split_source)
    if backup.exists():
        print(f"ERROR: Backup file already exists: {backup.relative_to(pkg_dir)}")
        return 1

    split_source.rename(backup)

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
    print(f"Renamed : {split_source.relative_to(pkg_dir)} -> {backup.relative_to(pkg_dir)}")
    print(f"Created : {', '.join(created)}")
    if not sensor_names:
        print("WARN: No sensor-specific blocks detected; definitions stayed in robot body file")
    print(f"Verify  : ros-devkit description-scaffold --verify {pkg_dir}")
    return 0
