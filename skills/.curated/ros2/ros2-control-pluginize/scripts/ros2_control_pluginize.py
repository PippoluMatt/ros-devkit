#!/usr/bin/env python3
"""Static checker for ros2_control pluginlib wiring."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SHARED_SCRIPTS))

from diagnostics import Finding as DiagnosticFinding, print_finding  # noqa: E402

SOURCE_SUFFIXES = {".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h"}
CONTROLLER_BASES = {
    "controller_interface::ChainableControllerInterface",
    "controller_interface::ControllerInterface",
}
HARDWARE_BASE = "hardware_interface::SystemInterface"


@dataclass(frozen=True)
class Finding:
    level: str
    message: str
    source: str | None = None


@dataclass(frozen=True)
class Branch:
    name: str
    suffix: str
    interface_package: str
    allowed_bases: set[str]


@dataclass(frozen=True)
class ClassCandidate:
    qualified_name: str
    base: str
    path: Path


@dataclass(frozen=True)
class ExportMacro:
    qualified_name: str
    base: str
    path: Path
    has_include: bool
    inside_namespace: bool


@dataclass(frozen=True)
class PluginClass:
    name: str
    qualified_name: str
    base: str
    declared_in_xml: bool
    source: str


@dataclass(frozen=True)
class PluginXml:
    path: Path
    library_target: str
    classes: list[PluginClass]


@dataclass(frozen=True)
class CMakeInfo:
    library_targets: list[str]
    plugin_exports: list[tuple[str, str]]
    find_packages: set[str]
    include_dependencies: set[str]
    ament_dependencies: dict[str, set[str]]
    linked_targets: dict[str, set[str]]
    installed_targets: set[str]
    target_exports: dict[str, str]
    exported_targets: set[str]
    exported_dependencies: set[str]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check static pluginlib wiring for an existing ros2_control package."
    )
    parser.add_argument("--check", metavar="PACKAGE_DIR", help="package directory to check")
    args = parser.parse_args(argv)

    if not args.check:
        parser.error("--check is required")

    return check_package(Path(args.check).expanduser().resolve())


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


def classify_branch(package_name: str) -> Branch | None:
    if package_name.endswith("_hardware"):
        return Branch(
            name="hardware",
            suffix="_hardware",
            interface_package="hardware_interface",
            allowed_bases={HARDWARE_BASE},
        )
    if package_name.endswith("_controllers"):
        return Branch(
            name="controllers",
            suffix="_controllers",
            interface_package="controller_interface",
            allowed_bases=set(CONTROLLER_BASES),
        )
    return None


def print_report(
    package_name: str,
    pkg_dir: Path,
    branch: Branch,
    plugin_xml: PluginXml | None,
    library_target: str | None,
    findings: list[Finding],
) -> None:
    print()
    print("ROS2 Control Pluginize Diagnostics")
    print(f"Package    : {package_name}")
    print(f"Path       : {pkg_dir}")
    print(f"Branch     : {branch.name}")
    print(f"Plugin XML : {relative(plugin_xml.path, pkg_dir) if plugin_xml else 'not found'}")
    print(f"Library    : {library_target or 'not found'}")
    print()
    for finding in findings:
        print_check_finding(finding)
    if not findings:
        print_finding(DiagnosticFinding("INFO", "No findings"))
    elif not any(finding.level == "ERROR" for finding in findings):
        print_finding(DiagnosticFinding("INFO", "No errors found"))
    else:
        print_finding(DiagnosticFinding("ERROR", "Errors found; fix before proceeding"))
    print()


def print_check_finding(finding: Finding) -> None:
    severity = "INFO" if finding.level == "OK" else finding.level
    print_finding(DiagnosticFinding(severity, finding.message, finding.source))


def source(package_name: str, rel_path: str | None = None) -> str:
    if rel_path:
        return f"{package_name}:{rel_path}"
    return package_name


def relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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


def read_cmake(cmake_path: Path, package_name: str, findings: list[Finding]) -> CMakeInfo:
    if not cmake_path.is_file():
        findings.append(Finding("ERROR", f"missing CMakeLists.txt: {cmake_path}", source(package_name)))
        return CMakeInfo([], [], set(), set(), {}, {}, set(), {}, set(), set())

    text = strip_cmake_comments(cmake_path.read_text(encoding="utf-8"))
    library_targets = command_first_args(text, "add_library")
    plugin_exports = plugin_export_calls(text)
    find_packages = set(command_first_args(text, "find_package"))
    include_dependencies = set_variable_args(text, "THIS_PACKAGE_INCLUDE_DEPENDS")
    ament_dependencies = dependency_commands(text, "ament_target_dependencies")
    linked_targets = dependency_commands(text, "target_link_libraries")
    installed_targets, target_exports = install_targets(text)
    exported_targets = exported_target_names(text)
    exported_dependencies = set(command_all_args(text, "ament_export_dependencies"))

    return CMakeInfo(
        library_targets=library_targets,
        plugin_exports=plugin_exports,
        find_packages=find_packages,
        include_dependencies=include_dependencies,
        ament_dependencies=ament_dependencies,
        linked_targets=linked_targets,
        installed_targets=installed_targets,
        target_exports=target_exports,
        exported_targets=exported_targets,
        exported_dependencies=exported_dependencies,
    )


def strip_cmake_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def command_calls(text: str, command: str) -> list[str]:
    pattern = re.compile(rf"\b{re.escape(command)}\s*\(", re.IGNORECASE)
    calls: list[str] = []
    for match in pattern.finditer(text):
        start = match.end()
        depth = 1
        index = start
        while index < len(text) and depth:
            char = text[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            index += 1
        if depth == 0:
            calls.append(text[start : index - 1])
    return calls


def split_cmake_args(body: str) -> list[tuple[str, str]]:
    return re.findall(r'"([^"]+)"|([^\s()]+)', body)


def cmake_args(body: str) -> list[str]:
    args: list[str] = []
    for quoted, bare in split_cmake_args(body):
        token = quoted or bare
        if token:
            args.append(token)
    return args


def command_first_args(text: str, command: str) -> list[str]:
    first_args: list[str] = []
    for body in command_calls(text, command):
        args = cmake_args(body)
        if args:
            first_args.append(args[0])
    return first_args


def command_all_args(text: str, command: str) -> list[str]:
    args: list[str] = []
    for body in command_calls(text, command):
        args.extend(cmake_args(body))
    return args


def set_variable_args(text: str, variable_name: str) -> set[str]:
    for body in command_calls(text, "set"):
        args = cmake_args(body)
        if args and args[0] == variable_name:
            return set(args[1:])
    return set()


def dependency_commands(text: str, command: str) -> dict[str, set[str]]:
    dependencies: dict[str, set[str]] = {}
    for body in command_calls(text, command):
        args = cmake_args(body)
        if not args:
            continue
        target = args[0]
        deps = {
            arg
            for arg in args[1:]
            if arg
            not in {
                "PUBLIC",
                "PRIVATE",
                "INTERFACE",
                "LINK_PUBLIC",
                "LINK_PRIVATE",
            }
        }
        dependencies.setdefault(target, set()).update(deps)
    return dependencies


def plugin_export_calls(text: str) -> list[tuple[str, str]]:
    exports: list[tuple[str, str]] = []
    for body in command_calls(text, "pluginlib_export_plugin_description_file"):
        args = cmake_args(body)
        if len(args) >= 2:
            exports.append((args[0], args[1]))
    return exports


def install_targets(text: str) -> tuple[set[str], dict[str, str]]:
    targets: set[str] = set()
    target_exports: dict[str, str] = {}
    for body in command_calls(text, "install"):
        args = cmake_args(body)
        if "TARGETS" not in args:
            continue
        start = args.index("TARGETS") + 1
        block_targets: list[str] = []
        for token in args[start:]:
            if token in {"EXPORT", "RUNTIME", "ARCHIVE", "LIBRARY", "DESTINATION", "INCLUDES"}:
                break
            targets.add(token)
            block_targets.append(token)
        if "EXPORT" in args:
            export_index = args.index("EXPORT")
            if export_index + 1 < len(args):
                for target in block_targets:
                    target_exports[target] = args[export_index + 1]
    return targets, target_exports


def exported_target_names(text: str) -> set[str]:
    exports: set[str] = set()
    for body in command_calls(text, "ament_export_targets"):
        args = cmake_args(body)
        if args:
            exports.add(args[0])
    return exports


def discover_plugin_xml(
    pkg_dir: Path,
    package_name: str,
    cmake: CMakeInfo,
    findings: list[Finding],
) -> PluginXml | None:
    if len(cmake.plugin_exports) > 1:
        findings.append(
            Finding(
                "ERROR",
                "multiple pluginlib_export_plugin_description_file calls found",
                source(package_name, "CMakeLists.txt"),
            )
        )
        return None

    if cmake.plugin_exports:
        _, rel_xml = cmake.plugin_exports[0]
        xml_path = (pkg_dir / rel_xml).resolve()
        if not xml_path.is_file():
            findings.append(
                Finding(
                    "ERROR",
                    f"missing plugin XML referenced by CMake: {rel_xml}",
                    source(package_name, "CMakeLists.txt"),
                )
            )
            return None
        if xml_path.parent != pkg_dir.resolve():
            findings.append(
                Finding(
                    "WARN",
                    f"plugin XML is outside the package root: {rel_xml}",
                    source(package_name, "CMakeLists.txt"),
                )
            )
        return read_plugin_xml(xml_path, pkg_dir, package_name, findings)

    root_xmls: list[PluginXml] = []
    for candidate in sorted(pkg_dir.glob("*.xml")):
        plugin = read_plugin_xml(candidate, pkg_dir, package_name, findings, quiet_parse_errors=True)
        if plugin is not None:
            root_xmls.append(plugin)

    if len(root_xmls) == 1:
        findings.append(
            Finding(
                "ERROR",
                "missing pluginlib_export_plugin_description_file in CMakeLists.txt",
                source(package_name, "CMakeLists.txt"),
            )
        )
        return root_xmls[0]
    if len(root_xmls) > 1:
        findings.append(
            Finding(
                "ERROR",
                "multiple package-root plugin XML files found; cannot choose one",
                source(package_name),
            )
        )
        return None

    findings.append(Finding("ERROR", "missing plugin XML", source(package_name)))
    return None


def read_plugin_xml(
    xml_path: Path,
    pkg_dir: Path,
    package_name: str,
    findings: list[Finding],
    quiet_parse_errors: bool = False,
) -> PluginXml | None:
    xml_source = source(package_name, relative(xml_path, pkg_dir))
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        if not quiet_parse_errors:
            findings.append(Finding("ERROR", f"cannot parse plugin XML: {exc}", xml_source))
        return None

    if local_name(root.tag) != "library":
        return None

    library_target = root.attrib.get("path", "").strip()
    if not library_target:
        findings.append(Finding("ERROR", "plugin XML is missing <library path>", xml_source))

    classes: list[PluginClass] = []
    for class_element in root.findall("class"):
        name = class_element.attrib.get("name", "").strip()
        qualified_name = class_element.attrib.get("type", "").strip()
        base = class_element.attrib.get("base_class_type", "").strip()
        if not name or not qualified_name or not base:
            findings.append(Finding("ERROR", "plugin XML has an incomplete <class> entry", xml_source))
            continue
        classes.append(
            PluginClass(
                name=name,
                qualified_name=qualified_name,
                base=base,
                declared_in_xml=True,
                source=xml_source,
            )
        )

    if not classes:
        findings.append(Finding("ERROR", "plugin XML does not declare any classes", xml_source))

    return PluginXml(path=xml_path, library_target=library_target, classes=classes)


def determine_library_target(
    plugin_xml: PluginXml | None,
    cmake: CMakeInfo,
    package_name: str,
    findings: list[Finding],
) -> str | None:
    if plugin_xml and plugin_xml.library_target:
        target = plugin_xml.library_target
        if target not in cmake.library_targets:
            findings.append(
                Finding(
                    "ERROR",
                    f"CMakeLists.txt does not define add_library({target} ...)",
                    source(package_name, "CMakeLists.txt"),
                )
            )
        return target

    if len(cmake.library_targets) == 1:
        findings.append(
            Finding(
                "INFO",
                f"using only CMake library target: {cmake.library_targets[0]}",
                source(package_name, "CMakeLists.txt"),
            )
        )
        return cmake.library_targets[0]
    if len(cmake.library_targets) > 1:
        findings.append(
            Finding(
                "ERROR",
                "multiple CMake library targets found; cannot choose plugin target",
                source(package_name, "CMakeLists.txt"),
            )
        )
    return None


def validate_package_dependencies(
    dependencies: set[str],
    branch: Branch,
    package_name: str,
    findings: list[Finding],
) -> None:
    package_source = source(package_name, "package.xml")
    for dependency in (branch.interface_package, "pluginlib"):
        if dependency in dependencies:
            findings.append(Finding("OK", f"package.xml depends on {dependency}", package_source))
        else:
            findings.append(Finding("ERROR", f"package.xml missing dependency: {dependency}", package_source))


def validate_cmake(
    cmake: CMakeInfo,
    cmake_path: Path,
    branch: Branch,
    library_target: str | None,
    plugin_xml: PluginXml | None,
    package_name: str,
    findings: list[Finding],
) -> None:
    if not cmake_path.is_file():
        return

    cmake_source = source(package_name, "CMakeLists.txt")
    for dependency in (branch.interface_package, "pluginlib"):
        if dependency in cmake.find_packages or dependency in cmake.include_dependencies:
            findings.append(Finding("OK", f"CMakeLists.txt finds {dependency}", cmake_source))
        else:
            findings.append(
                Finding("ERROR", f"CMakeLists.txt missing find_package({dependency} REQUIRED)", cmake_source)
            )

    if not cmake.plugin_exports:
        if plugin_xml is None:
            findings.append(
                Finding("ERROR", "missing pluginlib_export_plugin_description_file in CMakeLists.txt", cmake_source)
            )
    else:
        export_package, rel_xml = cmake.plugin_exports[0]
        if export_package != branch.interface_package:
            findings.append(
                Finding(
                    "ERROR",
                    "pluginlib_export_plugin_description_file uses "
                    f"{export_package}, expected {branch.interface_package}",
                    cmake_source,
                )
            )
        else:
            findings.append(
                Finding("OK", f"CMakeLists.txt exports plugin description for {branch.interface_package}", cmake_source)
            )
        if plugin_xml and (plugin_xml.path != (cmake_path.parent / rel_xml).resolve()):
            findings.append(Finding("ERROR", "CMake plugin XML path does not match discovered plugin XML", cmake_source))

    if library_target is None:
        return

    direct_links = cmake.linked_targets.get(library_target, set())
    ament_deps = cmake.ament_dependencies.get(library_target, set())
    uses_target_links = bool(direct_links)
    uses_ament_dependencies = bool(ament_deps)
    if uses_target_links and uses_ament_dependencies:
        findings.append(
            Finding(
                "WARN",
                f"CMake mixes target_link_libraries and ament_target_dependencies for {library_target}",
                cmake_source,
            )
        )

    for dependency in (branch.interface_package, "pluginlib"):
        imported_target = f"{dependency}::{dependency}"
        dependency_from_variable = (
            "${THIS_PACKAGE_INCLUDE_DEPENDS}" in ament_deps
            and dependency in cmake.include_dependencies
        )
        if imported_target in direct_links or dependency in ament_deps or dependency_from_variable:
            findings.append(Finding("OK", f"{library_target} links {dependency}", cmake_source))
        else:
            findings.append(Finding("ERROR", f"{library_target} missing public dependency: {dependency}", cmake_source))

    if library_target in cmake.installed_targets:
        findings.append(Finding("OK", f"{library_target} is installed", cmake_source))
    else:
        findings.append(Finding("ERROR", f"CMakeLists.txt does not install target {library_target}", cmake_source))

    target_export = cmake.target_exports.get(library_target)
    if target_export is None:
        findings.append(Finding("ERROR", f"install(TARGETS {library_target} ...) missing EXPORT", cmake_source))
    elif target_export in cmake.exported_targets:
        findings.append(Finding("OK", "CMakeLists.txt exports plugin library targets", cmake_source))
    else:
        findings.append(
            Finding("ERROR", f"CMakeLists.txt missing ament_export_targets({target_export} ...)", cmake_source)
        )

    for dependency in (branch.interface_package, "pluginlib"):
        dependency_from_variable = (
            "${THIS_PACKAGE_INCLUDE_DEPENDS}" in cmake.exported_dependencies
            and dependency in cmake.include_dependencies
        )
        if dependency in cmake.exported_dependencies or dependency_from_variable:
            findings.append(Finding("OK", f"CMakeLists.txt exports dependency {dependency}", cmake_source))
        else:
            findings.append(
                Finding("ERROR", f"CMakeLists.txt missing ament_export_dependencies for {dependency}", cmake_source)
            )


def validate_classes(
    plugin_classes: list[PluginClass],
    candidates: list[ClassCandidate],
    exports: list[ExportMacro],
    branch: Branch,
    pkg_dir: Path,
    package_name: str,
    findings: list[Finding],
) -> None:
    candidate_by_name = {candidate.qualified_name: candidate for candidate in candidates}

    for plugin_class in plugin_classes:
        if plugin_class.base not in branch.allowed_bases:
            findings.append(
                Finding(
                    "ERROR",
                    f"{plugin_class.qualified_name} XML base is {plugin_class.base}, expected {allowed_base_text(branch)}",
                    plugin_class.source,
                )
            )
        elif plugin_class.base == "controller_interface::ControllerInterface":
            findings.append(
                Finding(
                    "WARN",
                    f"{plugin_class.qualified_name} uses controller_interface::ControllerInterface, not chainable",
                    plugin_class.source,
                )
            )
        elif not plugin_class.declared_in_xml:
            findings.append(
                Finding(
                    "OK",
                    f"{plugin_class.qualified_name} candidate base matches {plugin_class.base}",
                    plugin_class.source,
                )
            )
        else:
            findings.append(
                Finding(
                    "OK",
                    f"{plugin_class.qualified_name} XML base matches {plugin_class.base}",
                    plugin_class.source,
                )
            )

        candidate = candidate_by_name.get(plugin_class.qualified_name)
        if candidate is None:
            findings.append(Finding("ERROR", f"could not find C++ class {plugin_class.qualified_name}", source(package_name)))
        elif candidate.base != plugin_class.base:
            findings.append(
                Finding(
                    "ERROR",
                    f"{plugin_class.qualified_name} C++ base {candidate.base} does not match XML base {plugin_class.base}",
                    source(package_name, relative(candidate.path, pkg_dir)),
                )
            )
        else:
            findings.append(
                Finding(
                    "OK",
                    f"found C++ class {plugin_class.qualified_name}",
                    source(package_name, relative(candidate.path, pkg_dir)),
                )
            )

        matching_exports = [
            export for export in exports if export.qualified_name == plugin_class.qualified_name
        ]
        if not matching_exports:
            findings.append(
                Finding(
                    "ERROR",
                    f"missing PLUGINLIB_EXPORT_CLASS for {plugin_class.qualified_name}",
                    source(package_name),
                )
            )
        elif len(matching_exports) > 1:
            findings.append(
                Finding(
                    "ERROR",
                    f"multiple PLUGINLIB_EXPORT_CLASS entries for {plugin_class.qualified_name}",
                    source(package_name),
                )
            )
        else:
            export = matching_exports[0]
            export_source = source(package_name, relative(export.path, pkg_dir))
            if export.base != plugin_class.base:
                findings.append(
                    Finding(
                        "ERROR",
                        f"{plugin_class.qualified_name} export base {export.base} does not match XML base {plugin_class.base}",
                        export_source,
                    )
                )
            elif not export.has_include:
                findings.append(
                    Finding(
                        "ERROR",
                        "missing include for pluginlib/class_list_macros.hpp",
                        export_source,
                    )
                )
            elif export.inside_namespace:
                findings.append(
                    Finding(
                        "ERROR",
                        f"PLUGINLIB_EXPORT_CLASS for {plugin_class.qualified_name} is inside a namespace",
                        export_source,
                    )
                )
            else:
                findings.append(
                    Finding("OK", f"found PLUGINLIB_EXPORT_CLASS for {plugin_class.qualified_name}", export_source)
                )


def infer_single_candidate(
    candidates: list[ClassCandidate],
    pkg_dir: Path,
    package_name: str,
    findings: list[Finding],
) -> list[PluginClass]:
    if len(candidates) == 1:
        candidate = candidates[0]
        candidate_source = source(package_name, relative(candidate.path, pkg_dir))
        findings.append(Finding("INFO", f"inferred plugin class {candidate.qualified_name}", candidate_source))
        return [
            PluginClass(
                name=candidate.qualified_name,
                qualified_name=candidate.qualified_name,
                base=candidate.base,
                declared_in_xml=False,
                source=candidate_source,
            )
        ]
    if len(candidates) > 1:
        findings.append(
            Finding("ERROR", "multiple C++ plugin candidates found; cannot infer plugin class", source(package_name))
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
    return []


def find_class_candidates(pkg_dir: Path, branch: Branch) -> list[ClassCandidate]:
    candidates: list[ClassCandidate] = []
    for path in source_files(pkg_dir):
        text = strip_cpp_comments(path.read_text(encoding="utf-8", errors="replace"))
        namespaces = namespace_ranges(text)
        for match in re.finditer(
            r"\b(?:class|struct)\s+([A-Za-z_]\w*)\s*(?:final\s*)?:\s*public\s+([A-Za-z_]\w*(?:::[A-Za-z_]\w*)+)",
            text,
            re.MULTILINE,
        ):
            class_name = match.group(1)
            base = match.group(2)
            if base not in branch.allowed_bases:
                continue
            namespace = namespace_at(match.start(), namespaces)
            qualified_name = f"{namespace}::{class_name}" if namespace else class_name
            candidates.append(
                ClassCandidate(
                    qualified_name=qualified_name,
                    base=base,
                    path=path,
                )
            )
    return sorted(candidates, key=lambda item: item.qualified_name)


def find_export_macros(pkg_dir: Path) -> list[ExportMacro]:
    exports: list[ExportMacro] = []
    for path in source_files(pkg_dir):
        text = strip_cpp_comments(path.read_text(encoding="utf-8", errors="replace"))
        has_include = has_pluginlib_include(text)
        namespaces = namespace_ranges(text)
        for match in re.finditer(
            r"\bPLUGINLIB_EXPORT_CLASS\s*\(\s*([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\s*,\s*([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\s*\)",
            text,
            re.MULTILINE | re.DOTALL,
        ):
            exports.append(
                ExportMacro(
                    qualified_name=match.group(1),
                    base=match.group(2),
                    path=path,
                    has_include=has_include,
                    inside_namespace=bool(namespace_at(match.start(), namespaces)),
                )
            )
    return exports


def has_pluginlib_include(text: str) -> bool:
    return bool(re.search(r"^\s*#\s*include\s*[<\"]pluginlib/class_list_macros\.hpp[>\"]", text, re.MULTILINE))


def source_files(pkg_dir: Path) -> list[Path]:
    skip_dirs = {".git", "build", "install", "log"}
    files: list[Path] = []
    for path in pkg_dir.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def strip_cpp_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def namespace_ranges(text: str) -> list[tuple[int, int, str]]:
    ranges: list[tuple[int, int, str]] = []
    pattern = re.compile(r"\bnamespace\s+([A-Za-z_]\w*)\s*\{")
    for match in pattern.finditer(text):
        open_brace = text.find("{", match.start(), match.end())
        close_brace = matching_brace(text, open_brace)
        if close_brace is not None:
            ranges.append((open_brace, close_brace, match.group(1)))
    return ranges


def matching_brace(text: str, open_brace: int) -> int | None:
    depth = 0
    for index in range(open_brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def namespace_at(index: int, ranges: list[tuple[int, int, str]]) -> str:
    active = [
        (start, name)
        for start, end, name in ranges
        if start < index < end
    ]
    active.sort()
    return "::".join(name for _, name in active)


def allowed_base_text(branch: Branch) -> str:
    return " or ".join(sorted(branch.allowed_bases))


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


if __name__ == "__main__":
    sys.exit(main())
