"""Console reporting for ros2_control_pluginize."""

from __future__ import annotations

from pathlib import Path

from .models import Branch, Finding, PluginXml
from utils.diagnostics import Finding as DiagnosticFinding, print_finding
from utils.fs import relative


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

def print_pluginize_report(
    package_name: str,
    pkg_dir: Path,
    branch: Branch,
    findings: list[Finding],
) -> None:
    print()
    print("ROS2 Control Pluginize")
    print(f"Package : {package_name}")
    print(f"Path    : {pkg_dir}")
    print(f"Branch  : {branch.name}")
    print()
    for finding in findings:
        print_check_finding(finding)
    if not findings:
        print_finding(DiagnosticFinding("INFO", "No findings"))
    elif not any(finding.level == "ERROR" for finding in findings):
        print_finding(DiagnosticFinding("INFO", "Pluginize complete; running --check"))
    else:
        print_finding(DiagnosticFinding("ERROR", "Pluginize blocked; fix errors before proceeding"))
    print()