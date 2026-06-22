"""package.xml parsing and mutation helpers."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .models import Branch
from utils.fs import relative, write_file_if_changed
from utils.xml import local_name

def read_package_xml(package_xml: Path) -> tuple[str, set[str]]:
    try:
        root = ET.parse(package_xml).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Cannot parse package.xml: {exc}") from exc

    name = root.findtext("name")
    if not name or not name.strip():
        raise ValueError("package.xml is missing <name>")

    dependencies: set[str] = set()
    for child in root:
        tag = local_name(child.tag)
        if tag == "depend" or tag.endswith("_depend"):
            if child.text and child.text.strip():
                dependencies.add(child.text.strip())

    return name.strip(), dependencies

def ensure_package_xml_dependencies(
    package_xml: Path,
    branch: Branch,
    pkg_dir: Path,
    changed: list[str],
) -> None:
    _, dependencies = read_package_xml(package_xml)
    missing = [
        dependency
        for dependency in (branch.interface_package, "pluginlib")
        if dependency not in dependencies
    ]
    if not missing:
        return

    before = package_xml.read_text(encoding="utf-8")
    tags = "\n".join(f"  <depend>{dependency}</depend>" for dependency in missing)
    export_match = re.search(r"(?m)^[ \t]*<export\b", before)
    if export_match:
        after = before[: export_match.start()].rstrip() + "\n\n" + tags + "\n\n" + before[export_match.start():].lstrip()
    else:
        package_end = re.search(r"(?m)^[ \t]*</package>", before)
        if not package_end:
            return
        after = before[: package_end.start()].rstrip() + "\n\n" + tags + "\n" + before[package_end.start():]
    if write_file_if_changed(package_xml, after):
        changed.append(f"Updated: {relative(package_xml, pkg_dir)}")
