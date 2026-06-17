#!/usr/bin/env python3
"""Create and include a minimal ros2_control xacro file."""

import argparse
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

XACRO_NS = "http://www.ros.org/wiki/xacro"
SYSTEM_INTERFACE = "hardware_interface::SystemInterface"


def find_main_xacro(root: Path) -> Path:
    for name in ("main.urdf.xacro", "main.xacro"):
        candidate = root / name
        if candidate.exists():
            return candidate
    raise SystemExit("Could not find main.urdf.xacro or main.xacro; pass --main-xacro")


def find_plugin_xml(root: Path) -> Path:
    matches = []
    for candidate in root.glob("*.xml"):
        try:
            tree = ET.parse(candidate)
        except ET.ParseError:
            continue
        for plugin_class in tree.findall(".//class"):
            if plugin_class.get("base_class_type") == SYSTEM_INTERFACE:
                matches.append(candidate)
                break

    if not matches:
        raise SystemExit("Could not find a SystemInterface plugin XML; pass --plugin-xml")
    if len(matches) > 1:
        names = ", ".join(str(match) for match in matches)
        raise SystemExit(f"Multiple SystemInterface plugin XML files found: {names}; pass --plugin-xml")
    return matches[0]


def plugin_name(plugin_xml: Path) -> str:
    tree = ET.parse(plugin_xml)
    for plugin_class in tree.findall(".//class"):
        if plugin_class.get("base_class_type") == SYSTEM_INTERFACE:
            name = plugin_class.get("name")
            if not name:
                raise SystemExit(f"{plugin_xml} has a SystemInterface <class> without a name attribute")
            return name
    raise SystemExit(f"{plugin_xml} does not contain a SystemInterface <class>")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def robot_name(main_xacro: Path) -> str:
    content = read_text(main_xacro)
    match = re.search(r"<robot\b[^>]*\bname\s*=\s*(['\"])(?P<name>[^'\"]+)\1", content, re.DOTALL)
    if not match:
        raise SystemExit(f"Could not find <robot name=\"...\"> in {main_xacro}")
    return match.group("name")


def robot_opening_tag_span(content: str) -> tuple[int, int]:
    match = re.search(r"<robot\b[^>]*>", content, re.DOTALL)
    if not match:
        raise SystemExit("Could not find opening <robot ...> tag")
    return match.span()


def ensure_xacro_namespace(opening_tag: str) -> str:
    if "xmlns:xacro" in opening_tag:
        return opening_tag
    return opening_tag[:-1].rstrip() + f' xmlns:xacro="{XACRO_NS}">'


def include_line(output_xacro: Path, main_xacro: Path) -> str:
    filename = Path(os.path.relpath(output_xacro.resolve(), start=main_xacro.parent.resolve()))
    return f'<xacro:include filename="{filename.as_posix()}" />'


def ensure_include(main_xacro: Path, output_xacro: Path) -> bool:
    content = read_text(main_xacro)
    include = include_line(output_xacro, main_xacro)
    if include in content:
        return False

    start, end = robot_opening_tag_span(content)
    opening_tag = ensure_xacro_namespace(content[start:end])
    insertion = "\n  " + include
    updated = content[:start] + opening_tag + insertion + content[end:]
    write_text(main_xacro, updated)
    return True


def create_output_xacro(output_xacro: Path, hardware_name: str, plugin: str) -> bool:
    if output_xacro.exists():
        return False

    content = f"""<?xml version="1.0" ?>
<robot xmlns:xacro="{XACRO_NS}">
  <ros2_control name="{hardware_name}" type="system">
    <hardware>
      <plugin>{plugin}</plugin>
    </hardware>
  </ros2_control>
</robot>
"""
    output_xacro.parent.mkdir(parents=True, exist_ok=True)
    write_text(output_xacro, content)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-xacro")
    parser.add_argument("--plugin-xml")
    parser.add_argument("--output-xacro")
    parser.add_argument("--hardware-name", default="MyRobotHardwareInterface")
    args = parser.parse_args()

    root = Path.cwd()
    main_xacro = Path(args.main_xacro) if args.main_xacro else find_main_xacro(root)
    plugin_xml = Path(args.plugin_xml) if args.plugin_xml else find_plugin_xml(root)
    name = robot_name(main_xacro)
    output_xacro = Path(args.output_xacro) if args.output_xacro else main_xacro.parent / f"{name}.ros2_control.xacro"
    plugin = plugin_name(plugin_xml)

    created = create_output_xacro(output_xacro, args.hardware_name, plugin)
    included = ensure_include(main_xacro, output_xacro)

    if created:
        print(f"Created {output_xacro}")
    else:
        print(f"Kept existing {output_xacro}")
    if included:
        print(f"Updated {main_xacro}")
    else:
        print(f"Include already present in {main_xacro}")


if __name__ == "__main__":
    main()
