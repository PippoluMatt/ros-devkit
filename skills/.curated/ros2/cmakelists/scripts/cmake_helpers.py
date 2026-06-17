#!/usr/bin/env python3
"""Compatibility imports for shared ROS2 CMakeLists.txt helpers."""

from __future__ import annotations

from pathlib import Path
import sys

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SHARED_SCRIPTS))

from cmake import (  # noqa: E402
    add_include_directories,
    add_install_share_directories,
    normalize_dir_name,
    remove_default_lint_block,
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_if_changed(path: Path, before: str, after: str) -> bool:
    if after == before:
        return False
    path.write_text(after, encoding="utf-8")
    return True
