"""C++ source scanning and pluginlib export mutation helpers."""

from __future__ import annotations

import re
from pathlib import Path

from .models import Branch, ClassCandidate, ExportMacro, SOURCE_SUFFIXES
from utils.fs import relative, write_file_if_changed

def ensure_source_export(pkg_dir: Path, candidate: ClassCandidate, changed: list[str]) -> None:
    exports = [
        export
        for export in find_export_macros(pkg_dir)
        if export.qualified_name == candidate.qualified_name
    ]
    correct = [
        export
        for export in exports
        if export.base == candidate.base and not export.inside_namespace and export.has_include
    ]
    if len(exports) == 1 and correct:
        return

    export_paths = sorted({export.path for export in exports})
    target_path = export_paths[0] if len(export_paths) == 1 else candidate.path

    for export_path in export_paths:
        before = export_path.read_text(encoding="utf-8")
        after = remove_export_macros(before, candidate.qualified_name)
        if write_file_if_changed(export_path, after):
            changed.append(f"Updated: {relative(export_path, pkg_dir)}")

    before = target_path.read_text(encoding="utf-8")
    after = ensure_pluginlib_include(before)
    after = remove_export_macros(after, candidate.qualified_name).rstrip()
    after += "\n\n" + export_macro(candidate.qualified_name, candidate.base)
    if write_file_if_changed(target_path, after + "\n"):
        changed.append(f"Updated: {relative(target_path, pkg_dir)}")

def remove_export_macros(text: str, qualified_name: str) -> str:
    pattern = re.compile(
        r"\n?[ \t]*PLUGINLIB_EXPORT_CLASS\s*\(\s*"
        + re.escape(qualified_name)
        + r"\s*,\s*[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*\s*\)[ \t]*\n?",
        re.MULTILINE | re.DOTALL,
    )
    return pattern.sub("\n", text)

def export_macro(qualified_name: str, base: str) -> str:
    return f"PLUGINLIB_EXPORT_CLASS(\n  {qualified_name},\n  {base})"

def ensure_pluginlib_include(text: str) -> str:
    if has_pluginlib_include(text):
        return text

    include_line = '#include "pluginlib/class_list_macros.hpp"'
    newline = "\r\n" if "\r\n" in text[:200] else "\n"
    lines = text.splitlines(keepends=True)
    last_include = -1
    for index, line in enumerate(lines):
        if re.match(r"^\s*#\s*include\b", line):
            last_include = index
    if last_include >= 0:
        lines.insert(last_include + 1, include_line + newline)
        return "".join(lines)
    return include_line + newline + newline + text.lstrip()

def find_class_candidates(pkg_dir: Path, branch: Branch) -> list[ClassCandidate]:
    candidates: list[ClassCandidate] = []
    for path in source_files(pkg_dir):
        text = strip_cpp_comments(path.read_text(encoding="utf-8", errors="replace"))
        namespaces = namespace_ranges(text)
        for match in re.finditer(
            r"\b(?:class|struct)\s+([A-Za-z_]\w*)\s*(?:final\s*)?:\s*public\s+([A-Za-z_]\w*(?:::[A-Za-z_]\w*)+)",
            text,
            re.MULTILINE,
        ):
            class_name = match.group(1)
            base = match.group(2)
            if base not in branch.allowed_bases:
                continue
            namespace = namespace_at(match.start(), namespaces)
            qualified_name = f"{namespace}::{class_name}" if namespace else class_name
            candidates.append(
                ClassCandidate(
                    qualified_name=qualified_name,
                    base=base,
                    path=path,
                )
            )
    return sorted(candidates, key=lambda item: item.qualified_name)

def find_export_macros(pkg_dir: Path) -> list[ExportMacro]:
    exports: list[ExportMacro] = []
    for path in source_files(pkg_dir):
        text = strip_cpp_comments(path.read_text(encoding="utf-8", errors="replace"))
        has_include = has_pluginlib_include(text)
        namespaces = namespace_ranges(text)
        for match in re.finditer(
            r"\bPLUGINLIB_EXPORT_CLASS\s*\(\s*([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\s*,\s*([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\s*\)",
            text,
            re.MULTILINE | re.DOTALL,
        ):
            exports.append(
                ExportMacro(
                    qualified_name=match.group(1),
                    base=match.group(2),
                    path=path,
                    has_include=has_include,
                    inside_namespace=bool(namespace_at(match.start(), namespaces)),
                )
            )
    return exports

def has_pluginlib_include(text: str) -> bool:
    return bool(re.search(r"^\s*#\s*include\s*[<\"]pluginlib/class_list_macros\.hpp[>\"]", text, re.MULTILINE))

def source_files(pkg_dir: Path) -> list[Path]:
    skip_dirs = {".git", "build", "install", "log"}
    files: list[Path] = []
    for path in pkg_dir.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        files.append(path)
    return sorted(files)

def strip_cpp_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)

def namespace_ranges(text: str) -> list[tuple[int, int, str]]:
    ranges: list[tuple[int, int, str]] = []
    pattern = re.compile(r"\bnamespace\s+([A-Za-z_]\w*)\s*\{")
    for match in pattern.finditer(text):
        open_brace = text.find("{", match.start(), match.end())
        close_brace = matching_brace(text, open_brace)
        if close_brace is not None:
            ranges.append((open_brace, close_brace, match.group(1)))
    return ranges

def matching_brace(text: str, open_brace: int) -> int | None:
    depth = 0
    for index in range(open_brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None

def namespace_at(index: int, ranges: list[tuple[int, int, str]]) -> str:
    active = [
        (start, name)
        for start, end, name in ranges
        if start < index < end
    ]
    active.sort()
    return "::".join(name for _, name in active)
