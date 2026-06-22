"""Plugin XML discovery, parsing, and mutation helpers."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from .models import Branch, CMakeInfo, Finding, PluginClass, PluginXml
from utils.diagnostics import source
from utils.fs import relative, write_file_if_changed
from utils.xml import local_name

def plugin_xml_for_pluginize(
    pkg_dir: Path,
    package_name: str,
    cmake: CMakeInfo,
    findings: list[Finding],
) -> tuple[PluginXml | None, Path | None]:
    if len(cmake.plugin_exports) > 1:
        findings.append(
            Finding(
                "ERROR",
                "multiple pluginlib_export_plugin_description_file calls found",
                source(package_name, "CMakeLists.txt"),
            )
        )
        return None, None

    if cmake.plugin_exports:
        _, rel_xml = cmake.plugin_exports[0]
        xml_path = (pkg_dir / rel_xml).resolve()
        if xml_path.is_file():
            plugin_xml = read_plugin_xml(xml_path, pkg_dir, package_name, findings)
            if plugin_xml and len(plugin_xml.classes) > 1:
                findings.append(
                    Finding(
                        "ERROR",
                        "plugin XML has multiple classes; cannot choose which class to update",
                        source(package_name, relative(xml_path, pkg_dir)),
                    )
                )
            return plugin_xml, xml_path
        return None, xml_path

    root_xmls: list[PluginXml] = []
    for candidate in sorted(pkg_dir.glob("*.xml")):
        plugin_xml = read_plugin_xml(candidate, pkg_dir, package_name, findings, quiet_parse_errors=True)
        if plugin_xml is not None:
            root_xmls.append(plugin_xml)

    if len(root_xmls) > 1:
        findings.append(
            Finding(
                "ERROR",
                "multiple package-root plugin XML files found; cannot choose one",
                source(package_name),
            )
        )
        return None, None
    if len(root_xmls) == 1:
        plugin_xml = root_xmls[0]
        if len(plugin_xml.classes) > 1:
            findings.append(
                Finding(
                    "ERROR",
                    "plugin XML has multiple classes; cannot choose which class to update",
                    source(package_name, relative(plugin_xml.path, pkg_dir)),
                )
            )
        return plugin_xml, plugin_xml.path

    return None, pkg_dir / f"{package_name}.xml"

def write_plugin_xml(
    xml_path: Path,
    branch: Branch,
    library_target: str,
    plugin_name: str,
    qualified_name: str,
    base: str,
    pkg_dir: Path,
    changed: list[str],
) -> None:
    class_name = qualified_name.rsplit("::", 1)[-1]
    kind = "controller" if branch.name == "controllers" else "hardware interface"
    content = (
        "<?xml version=\"1.0\"?>\n"
        f"<library path=\"{library_target}\">\n"
        f"  <class name=\"{plugin_name}\"\n"
        f"         type=\"{qualified_name}\"\n"
        f"         base_class_type=\"{base}\">\n"
        f"    <description>{class_name} ros2_control {kind}.</description>\n"
        "  </class>\n"
        "</library>\n"
    )
    existed = xml_path.exists()
    if write_file_if_changed(xml_path, content):
        changed.append(f"{'Created' if not existed else 'Updated'}: {relative(xml_path, pkg_dir)}")

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
