"""CLI for ros2 description-scaffold workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from package_xml_lib.parsing import robot_name_from_package

from .discovery import resolve_package_directory
from .scaffold import _repair_package, scaffold
from .split import split
from .validate import validate


def _parse_sensors(value: str) -> list[str]:
    sensors: list[str] = []
    for item in value.split(","):
        sensor = item.strip()
        if sensor and sensor not in sensors:
            sensors.append(sensor)
    return sensors


def _create(target: str, args: argparse.Namespace) -> int:
    target_path = Path(target).expanduser()
    sensors = _parse_sensors(args.sensors)

    if target_path.exists():
        pkg_dir = resolve_package_directory(target_path)
        if pkg_dir is None:
            return 1
        return _repair_package(pkg_dir, sensors)

    if target_path.parent != Path("."):
        robot_name = robot_name_from_package(target_path.name)
        destination = target_path.parent
    else:
        robot_name = robot_name_from_package(target)
        destination = args.destination

    scaffold(
        name=robot_name,
        sensors=sensors,
        destination=Path(destination).expanduser(),
        maintainer=args.maintainer,
        email=args.email,
        license_type=args.license,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run ros2-description-scaffold workflows."
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--verify",
        metavar="PACKAGE_DIR",
        nargs="?",
        const="",
        help="verify package structure; discover one package when omitted",
    )
    modes.add_argument(
        "--create",
        metavar="TARGET",
        nargs="?",
        const="",
        help="create a new package or repair an existing package directory",
    )
    modes.add_argument(
        "--split",
        metavar="PACKAGE_DIR",
        nargs="?",
        const="",
        help="split a monolithic xacro; discover one package when omitted",
    )
    parser.add_argument("--sensors", default="", help="Comma-separated sensor names")
    parser.add_argument(
        "--destination-directory",
        "--dir",
        dest="destination",
        default=".",
        help="Directory where a new package is created",
    )
    parser.add_argument("--source", help="Source xacro for --split when ambiguous")
    parser.add_argument("--maintainer", default=None, help="Maintainer name for ros2 pkg create")
    parser.add_argument("--email", default=None, help="Maintainer email for ros2 pkg create")
    parser.add_argument("--license", default=None, help="License for ros2 pkg create")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.verify is not None:
        return 0 if validate(args.verify or None) else 1
    if args.create is not None:
        if args.create:
            return _create(args.create, args)
        pkg_dir = resolve_package_directory(None)
        if pkg_dir is None:
            return 1
        return _repair_package(pkg_dir, _parse_sensors(args.sensors))
    if args.split is not None:
        return split(args.split or None, _parse_sensors(args.sensors), args.source)
    raise AssertionError("unreachable mode")
