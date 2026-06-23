"""Check workflow for ros2_control pluginlib wiring."""

from __future__ import annotations

import sys
from pathlib import Path

from .cmake import read_cmake
from .cpp_source import find_class_candidates, find_export_macros
from .models import Finding, classify_branch
from .package_xml import read_package_xml
from .plugin_xml import discover_plugin_xml
from .reporting import print_report
from utils.diagnostics import source
from .validation import (
    determine_library_target,
    infer_single_candidate,
    validate_classes,
    validate_cmake,
    validate_package_dependencies,
)

def check_package(pkg_dir: Path) -> int:
    if not pkg_dir.exists():
        print(f"ERROR: Package directory does not exist: {pkg_dir}", file=sys.stderr)
        return 2
    if not pkg_dir.is_dir():
        print(f"ERROR: Not a directory: {pkg_dir}", file=sys.stderr)
        return 2

    package_xml = pkg_dir / "package.xml"
    if not package_xml.is_file():
        print(f"ERROR: Missing package.xml: {package_xml}", file=sys.stderr)
        return 2

    try:
        package_name, package_dependencies = read_package_xml(package_xml)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    branch = classify_branch(package_name)
    if branch is None:
        print(
            f"ERROR: Unsupported package suffix for {package_name}; expected *_hardware or *_controllers",
            file=sys.stderr,
        )
        return 2

    findings: list[Finding] = []
    cmake_path = pkg_dir / "CMakeLists.txt"
    cmake = read_cmake(cmake_path, package_name, findings)
    plugin_xml = discover_plugin_xml(pkg_dir, package_name, cmake, findings)
    candidates = find_class_candidates(pkg_dir, branch)
    exports = find_export_macros(pkg_dir)

    if branch.name == "hardware" and not cmake.library_targets and plugin_xml is None:
        suggestion = f"{package_name[: -len(branch.suffix)]}_hardware_interface"
        findings.append(
            Finding(
                "INFO",
                f"conventional hardware library target would be {suggestion}",
                source(package_name),
            )
        )

    expected_target = determine_library_target(plugin_xml, cmake, package_name, findings)
    declared_classes = plugin_xml.classes if plugin_xml else []
    classes_to_validate = declared_classes or infer_single_candidate(candidates, pkg_dir, package_name, findings)

    validate_package_dependencies(package_dependencies, branch, package_name, findings)
    validate_cmake(cmake, cmake_path, branch, expected_target, plugin_xml, package_name, findings)
    validate_classes(classes_to_validate, candidates, exports, branch, pkg_dir, package_name, findings)

    print_report(package_name, pkg_dir, branch, plugin_xml, expected_target, findings)

    return 1 if any(finding.level == "ERROR" for finding in findings) else 0
