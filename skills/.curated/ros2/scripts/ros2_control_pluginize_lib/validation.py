"""Validation checks for ros2_control pluginlib wiring."""

from __future__ import annotations

from pathlib import Path

from .models import Branch, ClassCandidate, CMakeInfo, ExportMacro, Finding, PluginClass, PluginXml, allowed_base_text
from utils.diagnostics import source
from utils.fs import relative

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
