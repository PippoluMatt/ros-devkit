"""Data models for Gazebo simulation workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Context:
    root: Path
    description_pkg: Path | None
    bringup_pkg: Path | None
    errors: list[str]
