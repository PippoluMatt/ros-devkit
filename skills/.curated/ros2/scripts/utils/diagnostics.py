"""Diagnostic output formatting: findings, severity colours, and source labels."""

from __future__ import annotations

from dataclasses import dataclass
import os
import sys
from typing import TextIO


SEVERITY_COLORS = {
    "ERROR": "\033[31m",
    "WARN": "\033[33m",
    "INFO": "\033[32m",
}
RESET_COLOR = "\033[0m"


@dataclass(frozen=True)
class Finding:
    severity: str
    message: str
    source: str | None = None


def should_colorize(stream: TextIO | None = None) -> bool:
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb":
        return False
    return (stream or sys.stdout).isatty()


def format_severity(severity: str, color: bool | None = None) -> str:
    use_color = should_colorize() if color is None else color
    if use_color:
        return f"{SEVERITY_COLORS[severity]}{severity}{RESET_COLOR}"
    return severity


def format_finding(finding: Finding, color: bool | None = None) -> str:
    prefix = f"{format_severity(finding.severity, color)}:"
    if finding.source:
        prefix += f" [{finding.source}]"
    return f"{prefix} {finding.message}"


def print_finding(finding: Finding, color: bool | None = None) -> None:
    print(format_finding(finding, color))


def source(package_name: str, rel_path: str | None = None) -> str:
    """Format a diagnostic source label as ``package:rel_path``."""
    if rel_path:
        return f"{package_name}:{rel_path}"
    return package_name