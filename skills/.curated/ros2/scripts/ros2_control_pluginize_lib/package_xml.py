"""package.xml parsing and mutation helpers.

Generic parsing (``read_package_name``, ``read_dependencies``) and mutation
(``ensure_dependencies``) live in :mod:`package_xml_lib`.  This module keeps
the skill-specific strict wrapper :func:`read_package_xml` (which raises on
parse error or missing ``<name>``) and the :class:`Branch`-aware dependency
list computation.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from package_xml_lib.parsing import read_dependencies
from package_xml_lib.transforms import ensure_dependencies

from .models import Branch


def read_package_xml(package_xml: Path) -> tuple[str, set[str]]:
    """Strict wrapper that raises ``ValueError`` on parse error or missing ``<name>``."""
    try:
        root = ET.parse(package_xml).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Cannot parse package.xml: {exc}") from exc

    name = root.findtext("name")
    if not name or not name.strip():
        raise ValueError("package.xml is missing <name>")

    dependencies = read_dependencies(package_xml)
    return name.strip(), dependencies


def ensure_package_xml_dependencies(
    package_xml: Path,
    branch: Branch,
    pkg_dir: Path,
    changed: list[str],
) -> None:
    """Insert missing ``<depend>`` entries for the branch's interface package and pluginlib."""
    ensure_dependencies(
        package_xml,
        [branch.interface_package, "pluginlib"],
        tag="depend",
        pkg_dir=pkg_dir,
        changed=changed,
    )