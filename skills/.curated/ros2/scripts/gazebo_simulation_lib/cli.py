"""Command line interface for Gazebo simulation workflows."""

from __future__ import annotations

import argparse

from .add_plugin import add_plugin
from .diagnose import diagnose
from .setup import setup


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ROS2 Gazebo simulation workflows.")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--diagnose",
        dest="mode",
        action="store_const",
        const="diagnose",
        help="inspect Gazebo simulation wiring",
    )
    modes.add_argument(
        "--setup",
        dest="mode",
        action="store_const",
        const="setup",
        help="create missing Gazebo simulation scaffold files",
    )
    modes.add_argument(
        "--add-plugin",
        dest="mode",
        action="store_const",
        const="add_plugin",
        help="add a Gazebo system plugin to the robot xacro and/or world SDF",
    )
    parser.add_argument("path", nargs="?", help="Project root or package path")
    parser.add_argument("--description-package", help="Explicit <name>_description package path")
    parser.add_argument("--bringup-package", help="Explicit <name>_bringup package path")
    parser.add_argument("--robot-name", help="Robot/model name when package discovery is insufficient")
    parser.add_argument("--world-name", default="test_world", help="Gazebo world name for setup")
    parser.add_argument("--plugin", help="Plugin alias to add (use --list-plugins to see available)")
    parser.add_argument(
        "--list-plugins",
        action="store_true",
        help="List all available Gazebo Sim plugin aliases",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.mode == "diagnose":
        return 0 if diagnose(args) else 1
    if args.mode == "setup":
        return 0 if setup(args) else 1
    if args.mode == "add_plugin":
        return 0 if add_plugin(args) else 1
    raise AssertionError(f"unhandled mode: {args.mode}")
