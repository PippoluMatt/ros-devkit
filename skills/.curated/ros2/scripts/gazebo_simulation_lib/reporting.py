"""Report formatting for Gazebo simulation workflows."""

from __future__ import annotations

from utils.diagnostics import Finding, print_finding

from .models import Context


def _print_report(title: str, context: Context, findings: list[Finding]) -> None:
    print()
    print(title)
    print(f"Root        : {context.root}")
    print(f"Description : {context.description_pkg or 'not found'}")
    print(f"Bringup     : {context.bringup_pkg or 'not found'}")
    print()
    for finding in findings:
        print_finding(finding)
    if not findings:
        print_finding(Finding("INFO", "No findings"))
    elif not any(finding.severity == "ERROR" for finding in findings):
        print_finding(Finding("INFO", "No errors found"))
    else:
        print_finding(Finding("ERROR", "Errors found; fix before proceeding"))
    print()
