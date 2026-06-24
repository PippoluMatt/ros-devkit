"""Validate ROS2 description package structure."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from cmake_lib.parsing import installed_share_directories
from cmake_lib.transforms import remove_default_lint_block
from package_xml_lib.parsing import (
    read_dependencies,
    read_package_name,
    robot_name_from_package,
)
from utils.diagnostics import Finding, print_finding

from .discovery import resolve_package_directory


RESOURCE_INSTALL_DIRS = ("urdf", "meshes", "rviz", "config", "launch")


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
        file.name
        for file in urdf_dir.glob("*.xacro")
        if file.name not in standard_files and not file.name.endswith(".unsplit.xacro")
    )


def _present_resource_directories(pkg_dir: Path) -> list[str]:
    return [
        directory
        for directory in RESOURCE_INSTALL_DIRS
        if (pkg_dir / directory).is_dir()
    ]


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
        print_finding(Finding("ERROR", error, pkg_name))
    for warning in warnings:
        print_finding(Finding("WARN", warning, pkg_name))
    for info in infos:
        print_finding(Finding("INFO", info, pkg_name))

    if not errors and not warnings:
        print_finding(
            Finding("INFO", "All checks passed; package structure is compliant", pkg_name)
        )
    elif not errors:
        print_finding(
            Finding(
                "INFO",
                "No errors found; review warnings for structure improvements",
                pkg_name,
            )
        )
    else:
        print_finding(Finding("ERROR", "Errors found; fix before proceeding", pkg_name))

    print()


def validate(pkg_dir: str | Path | None = None) -> bool:
    """Validate the description package at pkg_dir. Returns True if no errors."""
    pkg_dir = resolve_package_directory(pkg_dir)
    if pkg_dir is None:
        return False

    if not pkg_dir.is_dir():
        print_finding(Finding("ERROR", f"Directory not found: {pkg_dir}"))
        return False

    pkg_name = read_package_name(pkg_dir / "package.xml")
    robot_name = robot_name_from_package(pkg_name)

    errors: list[str] = []
    warnings: list[str] = []
    infos: list[str] = []

    if not pkg_name.endswith("_description"):
        warnings.append(
            f"Package name should end with _description (found {pkg_name})"
        )

    for filename in [
        "CMakeLists.txt",
        "package.xml",
    ]:
        if (pkg_dir / filename).exists():
            infos.append(f"Found required file: {filename}")
        else:
            errors.append(f"Missing required file: {filename}")

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
                file.name
                for file in urdf_dir.glob("*.urdf.xacro")
                if file.name not in {"main.urdf.xacro", f"{robot_name}.urdf.xacro"}
            )
            if candidates:
                infos.append(
                    "Found non-canonical robot body candidates: "
                    + ", ".join(f"urdf/{candidate}" for candidate in candidates)
                )

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
                    "materials.xacro should be included first "
                    f"(found '{first_file}' instead)"
                )

            urdf_dir = pkg_dir / "urdf"
            xacro_files = {
                file.name
                for file in urdf_dir.glob("*.xacro")
                if file.name
                not in {
                    "main.xacro",
                    "main.urdf.xacro",
                    "sensors.xacro",
                }
                and not file.name.endswith(".unsplit.xacro")
            }
            included_names = {_basename(include) for include in includes}

            for xacro_file in sorted(xacro_files - included_names):
                warnings.append(
                    f"Xacro file not included in {entrypoint.relative_to(pkg_dir)}: urdf/{xacro_file}"
                )

            for include in includes:
                basename = _basename(include)
                inc_path = urdf_dir / basename
                if not inc_path.exists():
                    if _is_sensor_xacro(basename, robot_name):
                        warnings.append(f"Missing sensor xacro: urdf/{basename}")
                    else:
                        errors.append(
                            f"{entrypoint.relative_to(pkg_dir)} references non-existent file: {include}"
                        )

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

        except ValueError as error:
            errors.append(f"package.xml is not valid XML: {error}")

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
        installed_dirs = {
            directory
            for directory in installed_share_directories(cmake_content)
            if directory in RESOURCE_INSTALL_DIRS
        }
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

    urdf_dir = pkg_dir / "urdf"
    if urdf_dir.exists():
        for xacro_file in sorted(urdf_dir.glob("*.xacro")):
            try:
                ET.parse(xacro_file)
            except ET.ParseError as error:
                errors.append(
                    f"Invalid XML in {xacro_file.relative_to(pkg_dir)}: {error}"
                )

    _print_report(pkg_name, pkg_dir, errors, warnings, infos)
    return len(errors) == 0
