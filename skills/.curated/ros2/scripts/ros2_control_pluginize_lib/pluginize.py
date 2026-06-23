"""Pluginize workflow for ros2_control pluginlib wiring."""

from __future__ import annotations

import sys
from pathlib import Path

from .check import check_package
from .cmake import ensure_cmake_pluginization, read_cmake
from .cpp_source import ensure_source_export, find_class_candidates
from .models import Branch, CPP_SOURCE_SUFFIXES, ClassCandidate, CMakeInfo, Finding, PluginXml, classify_branch
from .package_xml import ensure_package_xml_dependencies, read_package_xml
from .plugin_xml import plugin_xml_for_pluginize, write_plugin_xml
from .reporting import print_pluginize_report
from utils.diagnostics import source
from utils.fs import relative

def pluginize_package(pkg_dir: Path) -> int:
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
        package_name, _ = read_package_xml(package_xml)
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
    changed: list[str] = []
    cmake_path = pkg_dir / "CMakeLists.txt"
    cmake_findings: list[Finding] = []
    cmake = read_cmake(cmake_path, package_name, cmake_findings)
    findings.extend(finding for finding in cmake_findings if finding.level == "ERROR")

    candidates = find_class_candidates(pkg_dir, branch)
    candidate = single_plugin_candidate(candidates, pkg_dir, package_name, findings)
    plugin_xml, plugin_xml_path = plugin_xml_for_pluginize(pkg_dir, package_name, cmake, findings)
    library_target = library_target_for_pluginize(
        plugin_xml,
        cmake,
        branch,
        package_name,
        candidate,
        pkg_dir,
        findings,
    )

    if any(finding.level == "ERROR" for finding in findings):
        print_pluginize_report(package_name, pkg_dir, branch, findings)
        return 2

    assert candidate is not None
    assert library_target is not None
    assert plugin_xml_path is not None

    class_name = candidate.qualified_name.rsplit("::", 1)[-1]
    plugin_name = (
        plugin_xml.classes[0].name
        if plugin_xml and plugin_xml.classes
        else default_plugin_name(branch, package_name, library_target, class_name)
    )
    plugin_xml_rel = relative(plugin_xml_path, pkg_dir)

    write_plugin_xml(
        plugin_xml_path,
        branch,
        library_target,
        plugin_name,
        candidate.qualified_name,
        candidate.base,
        pkg_dir,
        changed,
    )
    ensure_source_export(pkg_dir, candidate, changed)
    ensure_package_xml_dependencies(package_xml, branch, pkg_dir, changed)
    ensure_cmake_pluginization(
        cmake_path,
        branch,
        package_name,
        library_target,
        plugin_xml_rel,
        candidate.path,
        pkg_dir,
        changed,
    )

    if changed:
        findings.extend(Finding("INFO", path) for path in changed)
    else:
        findings.append(Finding("INFO", "No files were modified"))
    print_pluginize_report(package_name, pkg_dir, branch, findings)

    return check_package(pkg_dir)

def single_plugin_candidate(
    candidates: list[ClassCandidate],
    pkg_dir: Path,
    package_name: str,
    findings: list[Finding],
) -> ClassCandidate | None:
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        findings.append(
            Finding("ERROR", "multiple C++ plugin candidates found; cannot choose plugin class", source(package_name))
        )
        for candidate in candidates:
            findings.append(
                Finding(
                    "INFO",
                    f"candidate: {candidate.qualified_name}",
                    source(package_name, relative(candidate.path, pkg_dir)),
                )
            )
    else:
        findings.append(Finding("ERROR", "no C++ plugin candidate found", source(package_name)))
    return None

def library_target_for_pluginize(
    plugin_xml: PluginXml | None,
    cmake: CMakeInfo,
    branch: Branch,
    package_name: str,
    candidate: ClassCandidate | None,
    pkg_dir: Path,
    findings: list[Finding],
) -> str | None:
    if len(cmake.library_targets) == 1:
        return cmake.library_targets[0]
    if len(cmake.library_targets) > 1:
        if plugin_xml and plugin_xml.library_target in cmake.library_targets:
            return plugin_xml.library_target
        findings.append(
            Finding(
                "ERROR",
                "multiple CMake library targets found; cannot choose plugin target",
                source(package_name, "CMakeLists.txt"),
            )
        )
        return None

    if plugin_xml and plugin_xml.library_target:
        return plugin_xml.library_target

    if branch.name == "hardware" and candidate is not None:
        if candidate.path.suffix not in CPP_SOURCE_SUFFIXES:
            findings.append(
                Finding(
                    "ERROR",
                    "no CMake library target exists and the plugin candidate is not a C++ source file",
                    source(package_name, relative(candidate.path, pkg_dir)),
                )
            )
            return None
        return f"{package_name[: -len(branch.suffix)]}_hardware_interface"

    findings.append(
        Finding(
            "ERROR",
            "no CMake library target found; cannot choose controller plugin target",
            source(package_name, "CMakeLists.txt"),
        )
    )
    return None

def default_plugin_name(
    branch: Branch,
    package_name: str,
    library_target: str,
    class_name: str,
) -> str:
    if branch.name == "controllers":
        return f"{library_target}/{class_name}"
    return f"{package_name}/{class_name}"
