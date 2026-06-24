"""CLI entry point for shared package.xml transformations."""

from __future__ import annotations

import argparse
from pathlib import Path

from .parsing import read_package_name
from .transforms import ensure_dependencies, ensure_exec_depends


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    ensure = subcommands.add_parser(
        "ensure-depends",
        help="insert missing <depend> entries into a package.xml",
    )
    ensure.add_argument("package_xml", type=Path)
    ensure.add_argument("dependencies", nargs="+")

    exec_ensure = subcommands.add_parser(
        "ensure-exec-depends",
        help="insert missing <exec_depend> entries into a package.xml",
    )
    exec_ensure.add_argument("package_xml", type=Path)
    exec_ensure.add_argument("dependencies", nargs="+")

    read_name = subcommands.add_parser(
        "read-name",
        help="print the package <name>, falling back to the directory name",
    )
    read_name.add_argument("package_xml", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "ensure-depends":
        changed = ensure_dependencies(args.package_xml, args.dependencies)
        print("updated" if changed else "unchanged")
        return 0
    if args.command == "ensure-exec-depends":
        changed = ensure_exec_depends(args.package_xml, args.dependencies)
        print("updated" if changed else "unchanged")
        return 0
    if args.command == "read-name":
        print(read_package_name(args.package_xml))
        return 0
    raise AssertionError(f"unhandled command: {args.command}")