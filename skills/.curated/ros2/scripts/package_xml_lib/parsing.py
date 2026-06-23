"""Read-only package.xml parsing primitives.

These functions operate on ``package.xml`` files without any knowledge of
skill-specific data models (e.g. ``Branch``).  Skill-specific layers
compose these primitives into richer behaviour.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from utils.xml import local_name


# Known ROS2 package-name suffixes used by ``robot_name_from_package``
# when no explicit suffix is provided.
_KNOWN_SUFFIXES = ("_description", "_bringup", "_hardware", "_controllers")


def read_package_name(path: Path) -> str:
    """Read the ``<name>`` element from *path* (a ``package.xml`` file).

    Falls back to the parent directory name when the file is missing,
    unparseable, or has no ``<name>`` element.
    """
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, FileNotFoundError, OSError):
        return path.parent.name
    name = root.findtext("name")
    if not name or not name.strip():
        return path.parent.name
    return name.strip()


def read_dependencies(path: Path) -> set[str]:
    """Return every declared dependency across all ``*_depend`` tags and ``<depend>``.

    Raises ``ValueError`` when *path* cannot be parsed as XML.
    """
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Cannot parse package.xml: {exc}") from exc

    dependencies: set[str] = set()
    for child in root:
        tag = local_name(child.tag)
        if tag == "depend" or tag.endswith("_depend"):
            if child.text and child.text.strip():
                dependencies.add(child.text.strip())
    return dependencies


def robot_name_from_package(pkg_name: str, suffix: str | None = None) -> str:
    """Strip *suffix* (or a known suffix when ``None``) from *pkg_name*.

    When *suffix* is ``None`` the function tries every suffix in
    :data:`_KNOWN_SUFFIXES` and strips the first match.
    """
    suffixes: tuple[str, ...]
    if suffix is not None:
        suffixes = (suffix,)
    else:
        suffixes = _KNOWN_SUFFIXES
    for candidate in suffixes:
        if pkg_name.endswith(candidate):
            return pkg_name[: -len(candidate)]
    return pkg_name