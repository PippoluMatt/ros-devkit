#!/usr/bin/env python3
"""Shared CMakeLists.txt transformations for ROS2 curated skills."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


def remove_default_lint_block(text: str) -> str:
    lines = text.splitlines(keepends=True)
    start = _find_dependency_placeholder_start(lines)
    if start is None:
        return text

    if_index = _next_nonblank(lines, start + 1)
    while if_index is not None and not _is_build_testing_start(lines[if_index]):
        if _is_dependency_placeholder_line(lines[if_index]) or not lines[if_index].strip():
            if_index = _next_nonblank(lines, if_index + 1)
            continue
        return text

    if if_index is None:
        return text

    end = _find_matching_endif(lines, if_index)
    if end is None:
        return text

    block = "".join(lines[if_index : end + 1])
    required = [
        "find_package(ament_lint_auto REQUIRED)",
        "set(ament_cmake_copyright_FOUND TRUE)",
        "set(ament_cmake_cpplint_FOUND TRUE)",
        "ament_lint_auto_find_test_dependencies()",
    ]
    compact_block = re.sub(r"\s+", "", block)
    if not all(re.sub(r"\s+", "", item) in compact_block for item in required):
        return text

    replacement = "\n" if start > 0 and end + 1 < len(lines) else ""
    return "".join(lines[:start]).rstrip() + replacement + "".join(lines[end + 1 :]).lstrip()


def normalize_dir_name(directory: str) -> str:
    directory = directory.strip().strip("/")
    if not directory:
        raise ValueError("directory names must not be empty")
    if directory.startswith("..") or "/.." in directory:
        raise ValueError(f"directory must stay inside the package: {directory}")
    return directory


def add_include_directories(text: str) -> str:
    if re.search(r"(?m)^[ \t]*include_directories\([ \t]*include[ \t]*\)", text):
        return text

    lines = text.splitlines(keepends=True)
    find_package_lines = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^[ \t]*find_package\([^)]*\)[ \t]*(?:#.*)?(?:\r?\n)?$", line)
    ]
    if not find_package_lines:
        raise ValueError("no find_package(...) line found")

    insert_at = find_package_lines[-1] + 1
    while insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1

    newline = "\n"
    if lines and lines[0].endswith("\r\n"):
        newline = "\r\n"
    lines.insert(insert_at, f"include_directories(include){newline}{newline}")
    return "".join(lines)


def add_install_share_directories(text: str, directories: list[str]) -> str:
    normalized = []
    for directory in directories:
        directory = normalize_dir_name(directory)
        if directory not in normalized:
            normalized.append(directory)

    if not normalized:
        raise ValueError("at least one directory is required")

    install_block_re = re.compile(
        r"install\(\s*DIRECTORY\s+(?P<dirs>.*?)\s+DESTINATION\s+share/\$\{PROJECT_NAME\}\s*\)",
        re.DOTALL,
    )
    match = install_block_re.search(text)
    if match:
        existing = [item for item in re.split(r"\s+", match.group("dirs").strip()) if item]
        merged = existing[:]
        for directory in normalized:
            if directory not in merged:
                merged.append(directory)
        replacement = (
            "install(\n"
            f"  DIRECTORY {' '.join(merged)}\n"
            "  DESTINATION share/${PROJECT_NAME}\n"
            ")"
        )
        return text[: match.start()] + replacement + text[match.end() :]

    block = (
        "install(\n"
        f"  DIRECTORY {' '.join(normalized)}\n"
        "  DESTINATION share/${PROJECT_NAME}\n"
        ")\n"
    )
    anchor = re.search(r"(?m)^[ \t]*ament_package\(\)[ \t]*(?:#.*)?$", text)
    if anchor:
        start = anchor.start()
        prefix = text[:start].rstrip() + "\n\n"
        suffix = text[start:]
        return prefix + block + "\n" + suffix
    return text.rstrip() + "\n\n" + block


def _find_dependency_placeholder_start(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if line.strip() == "# uncomment the following section in order to fill in":
            return index
    return None


def _is_dependency_placeholder_line(line: str) -> bool:
    return line.strip() in {
        "# uncomment the following section in order to fill in",
        "# further dependencies manually.",
        "# find_package(<dependency> REQUIRED)",
    }


def _next_nonblank(lines: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        if lines[index].strip():
            return index
    return None


def _is_build_testing_start(line: str) -> bool:
    return re.match(r"^[ \t]*if[ \t]*\([ \t]*BUILD_TESTING[ \t]*\)", line) is not None


def _find_matching_endif(lines: list[str], start: int) -> int | None:
    depth = 0
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if re.match(r"^if[ \t]*\(", stripped):
            depth += 1
        elif re.match(r"^endif[ \t]*\(", stripped) or stripped == "endif()":
            depth -= 1
            if depth == 0:
                return index
    return None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_if_changed(path: Path, before: str, after: str) -> bool:
    if after == before:
        return False
    path.write_text(after, encoding="utf-8")
    return True


def _mutate_file(path: Path, transform) -> int:
    before = _read_text(path)
    after = transform(before)
    changed = _write_if_changed(path, before, after)
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
