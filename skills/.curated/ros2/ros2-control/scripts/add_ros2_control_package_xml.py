#!/usr/bin/env python3
"""Add common ROS2 control SystemInterface dependencies to package.xml."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


DEPS = ["hardware_interface", "pluginlib", "rclcpp", "rclcpp_lifecycle"]


def indent(elem: ET.Element, level: int = 0) -> None:
    space = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = space + "  "
        for child in elem:
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = space
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = space


def has_dep(root: ET.Element, name: str) -> bool:
    dep_tags = {"depend", "build_depend", "exec_depend", "build_export_depend"}
    return any(child.tag in dep_tags and (child.text or "").strip() == name for child in root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_xml")
    args = parser.parse_args()

    path = Path(args.package_xml)
    tree = ET.parse(path)
    root = tree.getroot()

    insert_at = len(root)
    for index, child in enumerate(root):
        if child.tag == "export":
            insert_at = index
            break
    for dep in DEPS:
        if not has_dep(root, dep):
            root.insert(insert_at, ET.Element("depend"))
            root[insert_at].text = dep
            insert_at += 1

    export = root.find("export")
    if export is None:
        export = ET.SubElement(root, "export")
    build_type = export.find("build_type")
    if build_type is None:
        build_type = ET.SubElement(export, "build_type")
    build_type.text = "ament_cmake"

    indent(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\n")


if __name__ == "__main__":
    main()
