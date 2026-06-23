#!/usr/bin/env python3
"""Validate a ROS2 description package structure.

Checks that a <name>_description package follows the standard modular xacro
structure and reports findings as ERROR, WARN, and INFO.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SHARED_SCRIPTS))

from cmake_lib.parsing import installed_share_directories  # noqa: E402
from cmake_lib.transforms import remove_default_lint_block  # noqa: E402
from package_xml_lib.parsing import (  # noqa: E402
    read_dependencies,
    read_package_name,
    robot_name_from_package,
)
from utils.diagnostics import Finding, format_severity, print_finding  # noqa: E402

RESOURCE_INSTALL_DIRS = ("urdf", "meshes", "rviz", "config", "launch")
DISCOVERY_SKIP_DIRS = {".git", "build", "install", "log"}


def _format_severity(severity: str, color: bool | None = None) -> str:
    return format_severity(severity, color)


def _print_finding(
    severity: str,
    message: str,
    color: bool | None = None,
    source: str | None = None,
) -> None:
    print_finding(Finding(severity, message, source), color)


def find_package_name(pkg_dir: Path) -> str:
    """Determine the package name from package.xml or directory name."""
    return read_package_name(pkg_dir / "package.xml")


def extract_includes(filepath: Path) -> list[str]:
    """Extract xacro:include filenames from a file."""
    content = filepath.read_text(encoding="utf-8")
    includes = re.findall(r'<xacro:include\s+filename="([^"]+)"', content)
    includes += re.findall(r"<xacro:include\s+filename='([^']+)'", content)
    return includes


def _basename(path_or_uri: str) -> str:
    return path_or_uri.replace("\\", "/").split("/")[-1]


def _is_sensor_xacro(filename: str, robot_name: str) -> bool:
    if not filename.endswith(".xacro"):
        return False
    non_sensor_names = {
        "main.xacro",
        "main.urdf.xacro",
        "materials.xacro",
        "sensors.xacro",
        f"{robot_name}.urdf.xacro",
    }
    if filename in non_sensor_names:
        return False
    return not filename.endswith(".urdf.xacro")


def _find_entrypoint(pkg_dir: Path, warnings: list[str], infos: list[str]) -> Path | None:
    main_xacro = pkg_dir / "urdf" / "main.xacro"
    main_urdf_xacro = pkg_dir / "urdf" / "main.urdf.xacro"

    if main_xacro.exists():
        infos.append("Found entry point: urdf/main.xacro")
        return main_xacro

    if main_urdf_xacro.exists():
        warnings.append(
            "Using urdf/main.urdf.xacro; standard entry point is urdf/main.xacro"
        )
        return main_urdf_xacro

    return None


def _extra_xacro_files_without_entrypoint(urdf_dir: Path, robot_name: str) -> list[str]:
    standard_files = {
        "main.xacro",
        "main.urdf.xacro",
        "materials.xacro",
        "sensors.xacro",
        f"{robot_name}.urdf.xacro",
    }
    return sorted(
        f.name
        for f in urdf_dir.glob("*.xacro")
        if f.name not in standard_files and not f.name.endswith(".unsplit.xacro")
    )


def _should_skip_discovery_dir(name: str) -> bool:
    return name in DISCOVERY_SKIP_DIRS or name.startswith(".")


def _find_description_packages(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not _should_skip_discovery_dir(dirname)
        ]
        if "package.xml" not in filenames:
            continue

        pkg_dir = Path(current)
        pkg_name = find_package_name(pkg_dir)
        if pkg_name.endswith("_description"):
            candidates.append(pkg_dir.resolve())

    return sorted(candidates)


def resolve_package_directory(pkg_dir: str | Path | None) -> Path | None:
    if pkg_dir:
        return Path(pkg_dir).expanduser().resolve()

    root = Path.cwd().resolve()
    candidates = _find_description_packages(root)

    if not candidates:
        _print_finding(
            "ERROR",
            f"No *_description package found under current project: {root}",
        )
        return None

    if len(candidates) > 1:
        _print_finding(
            "ERROR",
            f"Multiple *_description packages found under current project: {root}",
        )
        for candidate in candidates:
            _print_finding("INFO", f"Candidate: {candidate.relative_to(root)}")
        return None

    return candidates[0]


def _present_resource_directories(pkg_dir: Path) -> list[str]:
    return [
        directory
        for directory in RESOURCE_INSTALL_DIRS
        if (pkg_dir / directory).is_dir()
    ]


def _installed_share_directories(cmake_content: str) -> set[str]:
    return {
        d for d in installed_share_directories(cmake_content)
        if d in RESOURCE_INSTALL_DIRS
    }


def _has_generated_lint_block(cmake_content: str) -> bool:
    return remove_default_lint_block(cmake_content) != cmake_content


def _print_report(
    pkg_name: str,
    pkg_dir: Path,
    errors: list[str],
    warnings: list[str],
    infos: list[str],
) -> None:
    print()
    print("ROS2 Description Package Validator")
    print(f"Package : {pkg_name}")
    print(f"Path    : {pkg_dir}")
    print()

    for error in errors:
        _print_finding("ERROR", error, source=pkg_name)
    for warning in warnings:
        _print_finding("WARN", warning, source=pkg_name)
    for info in infos:
        _print_finding("INFO", info, source=pkg_name)

    if not errors and not warnings:
        _print_finding(
            "INFO",
            "All checks passed; package structure is compliant",
            source=pkg_name,
        )
    elif not errors:
        _print_finding(
            "INFO",
            "No errors found; review warnings for structure improvements",
            source=pkg_name,
        )
    else:
        _print_finding("ERROR", "Errors found; fix before proceeding", source=pkg_name)

    print()


def validate(pkg_dir: str | Path | None = None) -> bool:
    """Validate the description package at pkg_dir. Returns True if no errors."""
    pkg_dir = resolve_package_directory(pkg_dir)
    if pkg_dir is None:
        return False

    if not pkg_dir.is_dir():
        _print_finding("ERROR", f"Directory not found: {pkg_dir}")
        return False

    pkg_name = find_package_name(pkg_dir)
    robot_name = robot_name_from_package(pkg_name)

    errors: list[str] = []
    warnings: list[str] = []
    infos: list[str] = []

    if not pkg_name.endswith("_description"):
        warnings.append(
            f"Package name should end with _description (found {pkg_name})"
        )

    # Required files.
    for f in [
        "CMakeLists.txt",
        "package.xml",
    ]:
        if (pkg_dir / f).exists():
            infos.append(f"Found required file: {f}")
        else:
            errors.append(f"Missing required file: {f}")

    entrypoint = _find_entrypoint(pkg_dir, warnings, infos)
    if entrypoint is None:
        errors.append("Missing entry point: urdf/main.xacro or urdf/main.urdf.xacro")
        urdf_dir = pkg_dir / "urdf"
        if urdf_dir.exists():
            extra_xacros = _extra_xacro_files_without_entrypoint(urdf_dir, robot_name)
            if extra_xacros:
                warnings.append(
                    "Entry point missing; cannot verify standard includes for extra "
                    "xacro files: "
                    + ", ".join(f"urdf/{filename}" for filename in extra_xacros)
                )

    body_file = pkg_dir / "urdf" / f"{robot_name}.urdf.xacro"
    if body_file.exists():
        infos.append(f"Found robot body file: urdf/{robot_name}.urdf.xacro")
    else:
        errors.append(f"Missing robot body file: urdf/{robot_name}.urdf.xacro")
        urdf_dir = pkg_dir / "urdf"
        if urdf_dir.exists():
            candidates = sorted(
                f.name
                for f in urdf_dir.glob("*.urdf.xacro")
                if f.name not in {"main.urdf.xacro", f"{robot_name}.urdf.xacro"}
            )
            if candidates:
                infos.append(
                    "Found non-canonical robot body candidates: "
                    + ", ".join(f"urdf/{candidate}" for candidate in candidates)
                )

    # Recommended files.
    if not (pkg_dir / "urdf" / "materials.xacro").exists():
        warnings.append("Missing recommended file: urdf/materials.xacro")
    else:
        infos.append("Found recommended file: urdf/materials.xacro")

    if (pkg_dir / "urdf" / "sensors.xacro").exists():
        warnings.append(
            "urdf/sensors.xacro is present; split sensors into one <sensor>.xacro file per sensor"
        )

    rviz_dir = pkg_dir / "rviz"
    if not rviz_dir.exists():
        warnings.append("Missing recommended directory: rviz/")
    elif not list(rviz_dir.glob("*.rviz")):
        warnings.append("rviz/ directory exists but contains no .rviz files")
    else:
        infos.append("Found rviz configuration")

    meshes_dir = pkg_dir / "meshes"
    if meshes_dir.exists():
        infos.append("Found meshes/ directory")

    # Entry point include validation.
    if entrypoint is not None:
        includes = extract_includes(entrypoint)

        if not includes:
            warnings.append(
                f"{entrypoint.relative_to(pkg_dir)} has no xacro:include statements"
            )
        else:
            first_file = _basename(includes[0])
            if first_file == "materials.xacro":
                infos.append("materials.xacro is included first")
            else:
                warnings.append(
                    f"materials.xacro should be included first "
                    f"(found '{first_file}' instead)"
                )

            urdf_dir = pkg_dir / "urdf"
            xacro_files = {
                f.name
                for f in urdf_dir.glob("*.xacro")
                if f.name
                not in {
                    "main.xacro",
                    "main.urdf.xacro",
                    "sensors.xacro",
                }
                and not f.name.endswith(".unsplit.xacro")
            }
            included_names = {_basename(inc) for inc in includes}

            for xf in sorted(xacro_files - included_names):
                warnings.append(
                    f"Xacro file not included in {entrypoint.relative_to(pkg_dir)}: urdf/{xf}"
                )

            for inc in includes:
                basename = _basename(inc)
                inc_path = urdf_dir / basename
                if not inc_path.exists():
                    if _is_sensor_xacro(basename, robot_name):
                        warnings.append(f"Missing sensor xacro: urdf/{basename}")
                    else:
                        errors.append(
                            f"{entrypoint.relative_to(pkg_dir)} references non-existent file: {inc}"
                        )

    # package.xml dependencies.
    pkg_xml = pkg_dir / "package.xml"
    if pkg_xml.exists():
        try:
            deps = read_dependencies(pkg_xml)

            if "xacro" in deps:
                infos.append("package.xml lists xacro dependency")
            else:
                warnings.append("package.xml missing xacro dependency")

            if "urdf" in deps:
                infos.append("package.xml lists urdf dependency")
            else:
                warnings.append("package.xml missing urdf dependency")

        except ValueError as e:
            errors.append(f"package.xml is not valid XML: {e}")

    # CMakeLists.txt checks.
    cmake = pkg_dir / "CMakeLists.txt"
    if cmake.exists():
        cmake_content = cmake.read_text(encoding="utf-8")

        if _has_generated_lint_block(cmake_content):
            warnings.append(
                "CMakeLists.txt contains the generated ros2 pkg create dependency/lint "
                "placeholder block; suggested fix: remove that block from CMakeLists.txt"
            )

        if "find_package(ament_cmake" in cmake_content:
            infos.append("CMakeLists.txt uses ament_cmake")
        elif "find_package(catkin" in cmake_content:
            errors.append("CMakeLists.txt uses catkin (ROS1); expected ament_cmake")
        else:
            warnings.append("CMakeLists.txt does not find_package(ament_cmake)")

        present_dirs = _present_resource_directories(pkg_dir)
        installed_dirs = _installed_share_directories(cmake_content)
        missing_installs = [
            directory for directory in present_dirs if directory not in installed_dirs
        ]
        if missing_installs:
            warnings.append(
                "CMakeLists.txt does not install present package directories: "
                + ", ".join(missing_installs)
                + "; suggested fix: add them to install(DIRECTORY ... DESTINATION share/${PROJECT_NAME})"
            )
        elif present_dirs:
            infos.append(
                "CMakeLists.txt installs present package directories: "
                + ", ".join(present_dirs)
            )

    # XML well-formedness.
    urdf_dir = pkg_dir / "urdf"
    if urdf_dir.exists():
        for xf in sorted(urdf_dir.glob("*.xacro")):
            try:
                ET.parse(xf)
            except ET.ParseError as e:
                errors.append(
                    f"Invalid XML in {xf.relative_to(pkg_dir)}: {e}"
                )

    _print_report(pkg_name, pkg_dir, errors, warnings, infos)
    return len(errors) == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a ROS2 description package structure."
    )
    parser.add_argument(
        "package_directory",
        nargs="?",
        help=(
            "Path to a <name>_description package. If omitted, discover one "
            "*_description package under the current project."
        ),
    )
    args = parser.parse_args(argv)
    return 0 if validate(args.package_directory) else 1


if __name__ == "__main__":
    sys.exit(main())
