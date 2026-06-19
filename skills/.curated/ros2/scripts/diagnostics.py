#!/usr/bin/env python3
"""Shared terminal diagnostic formatting for ROS2 skill scripts."""

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
