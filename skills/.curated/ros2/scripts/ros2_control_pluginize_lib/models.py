"""Shared data models for ros2_control_pluginize."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SOURCE_SUFFIXES = {".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h"}
CPP_SOURCE_SUFFIXES = {".cpp", ".cc", ".cxx"}
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

def allowed_base_text(branch: Branch) -> str:
    return " or ".join(sorted(branch.allowed_bases))
