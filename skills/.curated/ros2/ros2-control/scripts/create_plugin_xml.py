#!/usr/bin/env python3
"""Create a pluginlib XML description for a SystemInterface plugin."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--library-target", required=True)
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--namespace-name")
    parser.add_argument("--class-name", default="MyRobotHardwareInterface")
    parser.add_argument("--description", default="ROS2 control hardware interface.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    namespace = args.namespace_name or args.package_name

    output = Path(args.output)
    if output.exists() and not args.force:
        raise SystemExit(f"{output} already exists; pass --force to overwrite")

    library = ET.Element("library", {"path": args.library_target})
    plugin_class = ET.SubElement(
        library,
        "class",
        {
            "name": f"{args.package_name}/{args.class_name}",
            "type": f"{namespace}::{args.class_name}",
            "base_class_type": "hardware_interface::SystemInterface",
        },
    )
    description = ET.SubElement(plugin_class, "description")
    description.text = args.description
    indent(library)

    output.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(library)
    tree.write(output, encoding="utf-8", xml_declaration=True)
    with output.open("a", encoding="utf-8") as stream:
        stream.write("\n")


if __name__ == "__main__":
    main()
