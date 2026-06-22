"""CLI entry point for ros2_control pluginlib wiring checks and pluginize."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .check import check_package
from .pluginize import pluginize_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check or add static pluginlib wiring for an existing ros2_control package."
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", metavar="PACKAGE_DIR", help="package directory to check")
    modes.add_argument("--pluginize", metavar="PACKAGE_DIR", help="add missing pluginlib wiring")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.check:
        return check_package(Path(args.check).expanduser().resolve())
    if args.pluginize:
        return pluginize_package(Path(args.pluginize).expanduser().resolve())
    raise AssertionError("unhandled mode")