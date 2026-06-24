"""Setup workflow for ROS2 Gazebo simulation scaffold files."""

from __future__ import annotations

import argparse
from pathlib import Path

from cmake_lib.transforms import add_install_share_directories
from package_xml_lib.parsing import read_package_name, robot_name_from_package
from package_xml_lib.transforms import ensure_exec_depends
from utils.diagnostics import Finding
from utils.fs import relative as _relative

from .discovery import discover_context
from .reporting import _print_report
from .templates import _bridge_yaml, _gazebo_launch_xml, _gazebo_xacro, _world_sdf


BRINGUP_INSTALL_DIRS = ("launch", "config", "worlds")


def _append_once(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def _write_missing(path: Path, content: str, created: list[str], root: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(_relative(path, root))


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
    _append_once(changed, f"Updated: " + _relative(main_xacro, root))


def _ensure_cmake_installs(
    pkg_dir: Path,
    directories: list[str],
    changed: list[str],
    root: Path,
) -> None:
    cmake = pkg_dir / "CMakeLists.txt"
    if not cmake.exists():
        pkg_name = read_package_name(pkg_dir / "package.xml")
        content = (
            "cmake_minimum_required(VERSION 3.8)\n"
            f"project({pkg_name})\n\n"
            "find_package(ament_cmake REQUIRED)\n\n"
            "ament_package()\n"
        )
        cmake.write_text(content, encoding="utf-8")
        _append_once(changed, f"Updated: " + _relative(cmake, root))

    before = cmake.read_text(encoding="utf-8")
    after = add_install_share_directories(before, directories)
    if after != before:
        cmake.write_text(after, encoding="utf-8")
        _append_once(changed, f"Updated: " + _relative(cmake, root))


def setup(args: argparse.Namespace) -> bool:
    context = discover_context(args.path, args.description_package, args.bringup_package)
    findings = [Finding("ERROR", error) for error in context.errors]
    created: list[str] = []
    changed: list[str] = []

    robot_name = args.robot_name
    if context.description_pkg is not None:
        pkg_name = read_package_name(context.description_pkg / "package.xml")
        robot_name = robot_name or robot_name_from_package(pkg_name)
        gazebo_xacro = context.description_pkg / "urdf" / f"{robot_name}_gazebo.xacro"
        _write_missing(gazebo_xacro, _gazebo_xacro(robot_name), created, context.root)
        _ensure_gazebo_include(context.description_pkg, robot_name, changed, context.root)
    else:
        findings.append(Finding("WARN", "No *_description package found; skipped Gazebo xacro setup"))

    if context.bringup_pkg is not None:
        bringup_name = read_package_name(context.bringup_pkg / "package.xml")
        robot_name = robot_name or args.robot_name or robot_name_from_package(bringup_name)
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
        ensure_exec_depends(
            context.bringup_pkg / "package.xml",
            ["ros_gz_sim", "ros_gz_bridge"],
            pkg_dir=context.bringup_pkg,
            changed=changed,
        )
    else:
        findings.append(Finding("WARN", "No *_bringup package found; skipped bridge and launch setup"))

    findings.extend(Finding("INFO", f"Created: {path}") for path in created)
    findings.extend(Finding("INFO", path) for path in changed)
    if not created and not changed:
        findings.append(Finding("INFO", "No missing Gazebo scaffold files found"))

    _print_report("ROS2 Gazebo Simulation Setup", context, findings)
    return not any(finding.severity == "ERROR" for finding in findings)
