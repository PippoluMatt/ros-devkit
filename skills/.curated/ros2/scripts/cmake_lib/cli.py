"""CLI entry point for shared CMakeLists.txt transformations."""

from __future__ import annotations

import argparse
from pathlib import Path

from utils.fs import write_file_if_changed

from .transforms import (
    add_include_directories,
    add_install_share_directories,
    normalize_dir_name,
    remove_default_lint_block,
)


def _mutate_file(path: Path, transform) -> int:
    before = path.read_text(encoding="utf-8")
    after = transform(before)
    changed = write_file_if_changed(path, after)
    print("updated" if changed else "unchanged")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    remove = subcommands.add_parser(
        "remove-default-lint-block",
        help="remove the generated ROS2 dependency/lint placeholder block",
    )
    remove.add_argument("cmakelists", type=Path)

    include = subcommands.add_parser(
        "add-include-directories",
        help="add include_directories(include) after find_package(...) rules",
    )
    include.add_argument("cmakelists", type=Path)

    install = subcommands.add_parser(
        "add-install-share-directories",
        help="add or update share-directory installation rules",
    )
    install.add_argument("cmakelists", type=Path)
    install.add_argument("directories", nargs="+")

    normalize = subcommands.add_parser(
        "normalize-dir-name",
        help="normalize and validate a package-relative directory name",
    )
    normalize.add_argument("directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "remove-default-lint-block":
        return _mutate_file(args.cmakelists, remove_default_lint_block)
    if args.command == "add-include-directories":
        return _mutate_file(args.cmakelists, add_include_directories)
    if args.command == "add-install-share-directories":
        return _mutate_file(
            args.cmakelists,
            lambda text: add_install_share_directories(text, args.directories),
        )
    if args.command == "normalize-dir-name":
        print(normalize_dir_name(args.directory))
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())