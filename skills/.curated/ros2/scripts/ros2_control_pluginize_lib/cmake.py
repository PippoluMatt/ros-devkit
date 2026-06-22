"""Pluginize-specific CMake parsing and mutation helpers.

Generic CMake text primitives live in :mod:`cmake_lib.parsing`; this module
composes them into ``CMakeInfo`` objects and applies pluginize-specific
transformations.
"""

from __future__ import annotations

from pathlib import Path

from cmake_lib.parsing import (
    cmake_args,
    command_all_args,
    command_call_spans,
    command_first_args,
    command_calls,
    dependency_commands,
    exported_target_names,
    format_cmake_command,
    insert_after_add_library,
    insert_after_last_find_package,
    insert_before_ament_package,
    insert_before_first_install_or_ament_package,
    install_targets,
    plugin_export_calls,
    set_variable_args,
    strip_cmake_comments,
)

from .models import Branch, CMakeInfo, Finding
from utils.diagnostics import source
from utils.fs import relative, write_file_if_changed


def ensure_cmake_pluginization(
    cmake_path: Path,
    branch: Branch,
    package_name: str,
    library_target: str,
    plugin_xml_rel: str,
    candidate_path: Path,
    pkg_dir: Path,
    changed: list[str],
) -> None:
    before = cmake_path.read_text(encoding="utf-8")
    text = before
    dependencies = [branch.interface_package, "pluginlib"]
    source_rel = relative(candidate_path, pkg_dir)

    text = ensure_cmake_dependency_discovery(text, dependencies)
    text = ensure_cmake_library_target(text, library_target, source_rel)
    text = ensure_cmake_target_dependencies(text, library_target, dependencies)
    text = ensure_cmake_plugin_export(text, branch.interface_package, plugin_xml_rel)
    text = ensure_cmake_target_install(text, library_target)
    text = ensure_cmake_export_targets(text, library_target)
    text = ensure_cmake_export_dependencies(text, dependencies)
    existed = cmake_path.exists()
    if write_file_if_changed(cmake_path, text):
        changed.append(f"{'Updated' if existed else 'Created'}: {relative(cmake_path, pkg_dir)}")


def ensure_cmake_dependency_discovery(text: str, dependencies: list[str]) -> str:
    cmake = cmake_info_from_text(text)
    if cmake.include_dependencies:
        return ensure_this_package_include_dependencies(text, dependencies)

    missing = [dependency for dependency in dependencies if dependency not in cmake.find_packages]
    for dependency in missing:
        text = insert_after_last_find_package(text, f"find_package({dependency} REQUIRED)\n")
    return text


def ensure_this_package_include_dependencies(text: str, dependencies: list[str]) -> str:
    for start, end, body in command_call_spans(text, "set"):
        args = cmake_args(body)
        if not args or args[0] != "THIS_PACKAGE_INCLUDE_DEPENDS":
            continue
        merged = args[1:]
        for dependency in dependencies:
            if dependency not in merged:
                merged.append(dependency)
        replacement = format_cmake_command("set", ["THIS_PACKAGE_INCLUDE_DEPENDS", *merged])
        return text[:start] + replacement + text[end:]
    return text


def ensure_cmake_library_target(text: str, library_target: str, source_rel: str) -> str:
    cmake = cmake_info_from_text(text)
    if library_target in cmake.library_targets:
        return text
    block = f"add_library({library_target} SHARED\n  {source_rel}\n)\n"
    return insert_after_last_find_package(text, block)


def ensure_cmake_target_dependencies(
    text: str,
    library_target: str,
    dependencies: list[str],
) -> str:
    cmake = cmake_info_from_text(text)
    ament_deps = cmake.ament_dependencies.get(library_target, set())
    direct_links = cmake.linked_targets.get(library_target, set())
    if (
        "${THIS_PACKAGE_INCLUDE_DEPENDS}" in ament_deps
        and all(dependency in cmake.include_dependencies for dependency in dependencies)
    ):
        return text
    if ament_deps:
        return update_cmake_command_args(text, "ament_target_dependencies", library_target, dependencies)
    imported_targets = [f"{dependency}::{dependency}" for dependency in dependencies]
    if direct_links:
        return update_target_link_libraries(text, library_target, imported_targets)
    if cmake.include_dependencies:
        block = f"ament_target_dependencies({library_target}\n  ${{THIS_PACKAGE_INCLUDE_DEPENDS}}\n)\n"
    else:
        block = (
            f"target_link_libraries({library_target} PUBLIC\n"
            + "".join(f"  {target}\n" for target in imported_targets)
            + ")\n"
        )
    return insert_after_add_library(text, library_target, block)


def ensure_cmake_plugin_export(text: str, interface_package: str, plugin_xml_rel: str) -> str:
    export_args = [interface_package, plugin_xml_rel]
    spans = command_call_spans(text, "pluginlib_export_plugin_description_file")
    if spans:
        start, end, body = spans[0]
        if cmake_args(body)[:2] == export_args:
            return text
        replacement = format_cmake_command("pluginlib_export_plugin_description_file", export_args)
        return text[:start] + replacement + text[end:]
    block = format_cmake_command("pluginlib_export_plugin_description_file", export_args) + "\n"
    return insert_before_first_install_or_ament_package(text, block)


def ensure_cmake_target_install(text: str, library_target: str) -> str:
    cmake = cmake_info_from_text(text)
    if library_target in cmake.installed_targets:
        return ensure_install_target_export(text, library_target, f"export_{library_target}")
    block = (
        "install(\n"
        f"  TARGETS {library_target}\n"
        f"  EXPORT export_{library_target}\n"
        "  RUNTIME DESTINATION bin\n"
        "  ARCHIVE DESTINATION lib\n"
        "  LIBRARY DESTINATION lib\n"
        ")\n"
    )
    return insert_before_ament_package(text, block)


def ensure_install_target_export(text: str, library_target: str, export_name: str) -> str:
    for start, end, body in command_call_spans(text, "install"):
        args = cmake_args(body)
        if "TARGETS" not in args or library_target not in args:
            continue
        if "EXPORT" in args:
            return text
        target_index = args.index(library_target)
        updated_args = args[: target_index + 1] + ["EXPORT", export_name] + args[target_index + 1 :]
        replacement = format_cmake_command("install", updated_args)
        return text[:start] + replacement + text[end:]
    return text


def ensure_cmake_export_targets(text: str, library_target: str) -> str:
    cmake = cmake_info_from_text(text)
    export_name = f"export_{library_target}"
    if export_name in cmake.exported_targets:
        return text
    block = f"ament_export_targets({export_name} HAS_LIBRARY_TARGET)\n"
    return insert_before_ament_package(text, block)


def ensure_cmake_export_dependencies(text: str, dependencies: list[str]) -> str:
    cmake = cmake_info_from_text(text)
    if (
        "${THIS_PACKAGE_INCLUDE_DEPENDS}" in cmake.exported_dependencies
        and all(dependency in cmake.include_dependencies for dependency in dependencies)
    ):
        return text
    missing = [dependency for dependency in dependencies if dependency not in cmake.exported_dependencies]
    if not missing:
        return text
    export_args = ["${THIS_PACKAGE_INCLUDE_DEPENDS}"] if cmake.include_dependencies else missing
    spans = command_call_spans(text, "ament_export_dependencies")
    if spans:
        start, end, body = spans[0]
        args = cmake_args(body)
        if "${THIS_PACKAGE_INCLUDE_DEPENDS}" in args:
            return text
        merged = args[:]
        for dependency in missing:
            if dependency not in merged:
                merged.append(dependency)
        replacement = format_cmake_command("ament_export_dependencies", merged)
        return text[:start] + replacement + text[end:]
    block = format_cmake_command("ament_export_dependencies", export_args) + "\n"
    return insert_before_ament_package(text, block)


def update_cmake_command_args(
    text: str,
    command: str,
    target: str,
    additions: list[str],
) -> str:
    for start, end, body in command_call_spans(text, command):
        args = cmake_args(body)
        if not args or args[0] != target:
            continue
        if "${THIS_PACKAGE_INCLUDE_DEPENDS}" in args:
            return text
        merged = args[:]
        for addition in additions:
            if addition not in merged:
                merged.append(addition)
        replacement = format_cmake_command(command, merged)
        return text[:start] + replacement + text[end:]
    return text


def update_target_link_libraries(
    text: str,
    target: str,
    imported_targets: list[str],
) -> str:
    for start, end, body in command_call_spans(text, "target_link_libraries"):
        args = cmake_args(body)
        if not args or args[0] != target:
            continue
        existing = args[1:]
        missing = [imported for imported in imported_targets if imported not in existing]
        if not missing:
            return text
        if "PUBLIC" in existing:
            index = existing.index("PUBLIC") + 1
            merged = [target, *existing[:index], *missing, *existing[index:]]
        else:
            merged = [target, "PUBLIC", *missing, *existing]
        replacement = format_cmake_command("target_link_libraries", merged)
        return text[:start] + replacement + text[end:]
    return text


def read_cmake(cmake_path: Path, package_name: str, findings: list[Finding]) -> CMakeInfo:
    if not cmake_path.is_file():
        findings.append(Finding("ERROR", f"missing CMakeLists.txt: {cmake_path}", source(package_name)))
        return CMakeInfo([], [], set(), set(), {}, {}, set(), {}, set(), set())

    return cmake_info_from_text(cmake_path.read_text(encoding="utf-8"))


def cmake_info_from_text(text: str) -> CMakeInfo:
    text = strip_cmake_comments(text)
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