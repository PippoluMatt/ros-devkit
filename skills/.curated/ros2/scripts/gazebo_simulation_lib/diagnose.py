"""Diagnostics workflow for ROS2 Gazebo simulation wiring."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from cmake_lib.parsing import installed_share_directories
from package_xml_lib.parsing import read_package_name, robot_name_from_package
from utils.diagnostics import Finding, source as _source
from utils.fs import relative as _relative
from utils.xml import local_name as _local_name

from .bridge import _diagnose_bridge
from .discovery import discover_context
from .reporting import _print_report
from .world_sdf import _resolve_gz_sim_plugin_dir


def _link_is_footprint(name: str) -> bool:
    return name == "base_footprint" or name.endswith("footprint")


def _has_direct_child(element: ET.Element, child_name: str) -> bool:
    return any(_local_name(child.tag) == child_name for child in list(element))


def _diagnose_description(pkg_dir: Path, findings: list[Finding]) -> str | None:
    pkg_name = read_package_name(pkg_dir / "package.xml")
    robot_name = robot_name_from_package(pkg_name)
    urdf_dir = pkg_dir / "urdf"

    findings.append(
        Finding("INFO", f"Description package path: {pkg_dir}", source=pkg_name)
    )

    if not urdf_dir.is_dir():
        findings.append(
            Finding(
                "ERROR",
                f"Missing description urdf/ directory: {pkg_dir / 'urdf'}",
                source=pkg_name,
            )
        )
        return robot_name

    xacro_files = sorted(urdf_dir.glob("*.xacro"))
    if not xacro_files:
        findings.append(
            Finding(
                "ERROR",
                f"No xacro files found under {_relative(urdf_dir, pkg_dir)}",
                source=pkg_name,
            )
        )

    for xacro_file in xacro_files:
        rel = _relative(xacro_file, pkg_dir)
        try:
            root = ET.parse(xacro_file).getroot()
        except ET.ParseError as exc:
            findings.append(
                Finding("ERROR", f"Invalid XML: {exc}", source=_source(pkg_name, rel))
            )
            continue
        for link in root.iter():
            if _local_name(link.tag) != "link":
                continue
            link_name = link.attrib.get("name", "").strip()
            if _link_is_footprint(link_name):
                findings.append(
                    Finding(
                        "INFO",
                        f"Footprint link exempt from physics tags: {link_name}",
                        source=_source(pkg_name, rel),
                    )
                )
                continue
            label = link_name or "unnamed link"
            if not _has_direct_child(link, "collision"):
                findings.append(
                    Finding(
                        "ERROR",
                        f"Link missing collision tag: {label}",
                        source=_source(pkg_name, rel),
                    )
                )
            if not _has_direct_child(link, "inertial"):
                findings.append(
                    Finding(
                        "ERROR",
                        f"Link missing inertial tag: {label}",
                        source=_source(pkg_name, rel),
                    )
                )

    gazebo_xacro = urdf_dir / f"{robot_name}_gazebo.xacro"
    gazebo_rel = f"urdf/{robot_name}_gazebo.xacro"
    if not gazebo_xacro.exists():
        findings.append(
            Finding("ERROR", f"Missing Gazebo xacro: {gazebo_rel}", source=pkg_name)
        )
    else:
        findings.append(
            Finding("INFO", "Found Gazebo xacro", source=_source(pkg_name, gazebo_rel))
        )
        try:
            root = ET.parse(gazebo_xacro).getroot()
            if not any(_local_name(element.tag) == "gazebo" for element in root.iter()):
                findings.append(
                    Finding(
                        "WARN",
                        "contains no <gazebo> elements",
                        source=_source(pkg_name, gazebo_rel),
                    )
                )
        except ET.ParseError as exc:
            findings.append(
                Finding(
                    "ERROR",
                    f"Invalid XML: {exc}",
                    source=_source(pkg_name, gazebo_rel),
                )
            )

    entrypoint = urdf_dir / "main.xacro"
    if entrypoint.exists():
        content = entrypoint.read_text(encoding="utf-8")
        if f"{robot_name}_gazebo.xacro" in content:
            findings.append(
                Finding(
                    "INFO",
                    f"includes {robot_name}_gazebo.xacro",
                    source=_source(pkg_name, "urdf/main.xacro"),
                )
            )
        else:
            findings.append(
                Finding(
                    "WARN",
                    f"does not include {robot_name}_gazebo.xacro",
                    source=_source(pkg_name, "urdf/main.xacro"),
                )
            )
    else:
        findings.append(
            Finding(
                "WARN",
                "Missing urdf/main.xacro; cannot check Gazebo xacro include",
                source=pkg_name,
            )
        )

    return robot_name


def _diagnose_bringup(pkg_dir: Path, findings: list[Finding]) -> None:
    pkg_name = read_package_name(pkg_dir / "package.xml")
    findings.append(Finding("INFO", f"Bringup package path: {pkg_dir}", source=pkg_name))

    for rel_path in ("package.xml", "CMakeLists.txt"):
        if (pkg_dir / rel_path).exists():
            findings.append(
                Finding("INFO", "Found bringup file", source=_source(pkg_name, rel_path))
            )
        else:
            findings.append(
                Finding("ERROR", f"Bringup package missing {rel_path}", source=pkg_name)
            )

    launch_dir = pkg_dir / "launch"
    if launch_dir.is_dir():
        findings.append(Finding("INFO", "Found bringup launch/ directory", source=pkg_name))
    else:
        findings.append(Finding("ERROR", "Bringup package missing launch/ directory", source=pkg_name))

    cmake = pkg_dir / "CMakeLists.txt"
    installed_dirs: set[str] = set()
    if cmake.exists():
        installed_dirs = installed_share_directories(cmake.read_text(encoding="utf-8"))
        if "launch" in installed_dirs:
            findings.append(
                Finding(
                    "INFO",
                    "CMakeLists.txt installs launch/",
                    source=_source(pkg_name, "CMakeLists.txt"),
                )
            )
        else:
            findings.append(
                Finding(
                    "ERROR",
                    "CMakeLists.txt must install launch/ to share/${PROJECT_NAME}",
                    source=_source(pkg_name, "CMakeLists.txt"),
                )
            )
        for directory in ("config", "worlds"):
            if (pkg_dir / directory).exists() and directory not in installed_dirs:
                findings.append(
                    Finding(
                        "WARN",
                        f"CMakeLists.txt does not install present {directory}/ directory",
                        source=pkg_name,
                    )
                )

    _diagnose_world_sdf(pkg_dir, findings)
    _diagnose_bridge(pkg_dir, findings)
    _diagnose_launch(pkg_dir, findings)


def _diagnose_world_sdf(pkg_dir: Path, findings: list[Finding]) -> None:
    """Validate <plugin filename="..."> in world .sdf files against installed .so libs."""
    pkg_name = read_package_name(pkg_dir / "package.xml")
    worlds_dir = pkg_dir / "worlds"
    if not worlds_dir.is_dir():
        return

    sdf_files = sorted(worlds_dir.glob("*.sdf"))
    if not sdf_files:
        return

    plugin_dir = _resolve_gz_sim_plugin_dir()
    if plugin_dir is None:
        findings.append(
            Finding(
                "WARN",
                "Could not locate gz-sim plugin directory; skipping SDF plugin filename validation",
                source=pkg_name,
            ),
        )
        return

    # Build a set of installed plugin basenames (e.g. "gz-sim-sensors-system")
    installed_plugins: set[str] = set()
    for so_file in plugin_dir.iterdir():
        if so_file.suffix == ".so":
            name = so_file.name
            # Strip lib prefix and .so suffix: libgz-sim-sensors-system.so -> gz-sim-sensors-system
            if name.startswith("lib"):
                name = name[3:]
            if name.endswith(".so"):
                name = name[:-3]
            installed_plugins.add(name)

    for sdf_file in sdf_files:
        rel = _relative(sdf_file, pkg_dir)
        sdf_source = _source(pkg_name, rel)
        try:
            tree = ET.parse(sdf_file)
        except ET.ParseError as exc:
            findings.append(
                Finding(
                    "ERROR",
                    f"Invalid SDF XML: {exc}",
                    source=sdf_source,
                ),
            )
            continue

        # Find all <plugin> elements anywhere in the tree
        for plugin_elem in tree.iter("plugin"):
            filename = plugin_elem.get("filename", "")
            if not filename:
                continue
            # Only check gz-sim-* style plugin filenames
            if not filename.startswith("gz-sim-"):
                continue
            if filename not in installed_plugins:
                # Try to suggest the closest match
                suggestion = None
                # Common typo: trailing 's' (e.g. 'sensors-systems' -> 'sensors-system')
                singular = filename[:-1] if filename.endswith("s") else None
                if singular and singular in installed_plugins:
                    suggestion = singular
                else:
                    # Simple substring match
                    matches = [p for p in installed_plugins if filename.replace("-", "") in p.replace("-", "") or p in filename or filename in p]
                    if len(matches) == 1:
                        suggestion = matches[0]
                detail = f"filename=\"{filename}\" not found in {plugin_dir}"
                if suggestion:
                    detail += f" — did you mean \"{suggestion}\"?"
                findings.append(
                    Finding(
                        "ERROR",
                        f"SDF plugin {detail}",
                        source=sdf_source,
                    ),
                )
            else:
                findings.append(
                    Finding(
                        "INFO",
                        f"SDF plugin filename=\"{filename}\" OK",
                        source=sdf_source,
                    ),
                )


def _diagnose_launch(pkg_dir: Path, findings: list[Finding]) -> None:
    pkg_name = read_package_name(pkg_dir / "package.xml")
    launch_dir = pkg_dir / "launch"
    if not launch_dir.is_dir():
        return

    launch_files = sorted(
        path
        for path in launch_dir.iterdir()
        if path.suffix in {".xml", ".py"} or path.name.endswith((".launch.xml", ".launch.py"))
    )
    if not launch_files:
        findings.append(
            Finding(
                "WARN",
                "launch/ contains no XML or Python launch files",
                source=pkg_name,
            )
        )
        return

    compliant_files: list[str] = []
    for launch_file in launch_files:
        text = launch_file.read_text(encoding="utf-8")
        rel = _relative(launch_file, pkg_dir)
        launch_source = _source(pkg_name, rel)
        if launch_file.name.endswith(".xml"):
            try:
                ET.fromstring(text)
            except ET.ParseError as exc:
                findings.append(
                    Finding(
                        "ERROR",
                        f"Invalid XML launch file: {exc}",
                        source=launch_source,
                    )
                )
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
            findings.append(
                Finding(
                    "WARN",
                    f"missing Gazebo launch wiring: {', '.join(missing)}",
                    source=launch_source,
                )
            )
        else:
            compliant_files.append(rel)

    if compliant_files:
        findings.append(
            Finding(
                "INFO",
                f"Gazebo launch wiring present in: {', '.join(compliant_files)}",
                source=pkg_name,
            )
        )


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
