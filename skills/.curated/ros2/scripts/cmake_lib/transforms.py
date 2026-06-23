"""Generic CMake text transforms for ROS2 curated skills.

These functions read and modify CMakeLists.txt text without any knowledge of
plugin-specific concepts.  They are shared by the ``cmakelists``,
``description-scaffold``, and ``gazebo-simulation`` skills.
"""

from __future__ import annotations

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


# ── internal helpers ───────────────────────────────────────────────

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