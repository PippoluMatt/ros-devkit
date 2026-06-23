"""Generic CMake text parsing primitives.

These functions operate on raw CMake source text without any knowledge of
pluginize-specific data models.  Skill-specific layers (e.g.
``ros2_control_pluginize_lib.cmake``) compose these primitives into richer
structures like ``CMakeInfo``.
"""

from __future__ import annotations

import re


# ── comment stripping ────────────────────────────────────────────────

def strip_cmake_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


# ── command-call span finding ───────────────────────────────────────

def command_call_spans(text: str, command: str) -> list[tuple[int, int, str]]:
    """Return ``(start, end, body)`` triples for every *command*(…) call.

    *start* is the index of the command name, *end* is the index just past
    the closing paren, and *body* is the raw text between the parentheses.
    """
    pattern = re.compile(rf"\b{re.escape(command)}\s*\(", re.IGNORECASE)
    calls: list[tuple[int, int, str]] = []
    for match in pattern.finditer(text):
        start = match.end()
        depth = 1
        index = start
        while index < len(text) and depth:
            char = text[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            index += 1
        if depth == 0:
            calls.append((match.start(), index, text[start : index - 1]))
    return calls


def command_calls(text: str, command: str) -> list[str]:
    """Return just the bodies of every *command*(…) call."""
    return [body for _, _, body in command_call_spans(text, command)]


# ── argument extraction ────────────────────────────────────────────

def split_cmake_args(body: str) -> list[tuple[str, str]]:
    return re.findall(r'"([^"]+)"|([^\s()]+)', body)


def cmake_args(body: str) -> list[str]:
    args: list[str] = []
    for quoted, bare in split_cmake_args(body):
        token = quoted or bare
        if token:
            args.append(token)
    return args


def command_first_args(text: str, command: str) -> list[str]:
    first_args: list[str] = []
    for body in command_calls(text, command):
        args = cmake_args(body)
        if args:
            first_args.append(args[0])
    return first_args


def command_all_args(text: str, command: str) -> list[str]:
    args: list[str] = []
    for body in command_calls(text, command):
        args.extend(cmake_args(body))
    return args


def set_variable_args(text: str, variable_name: str) -> set[str]:
    for body in command_calls(text, "set"):
        args = cmake_args(body)
        if args and args[0] == variable_name:
            return set(args[1:])
    return set()


def dependency_commands(text: str, command: str) -> dict[str, set[str]]:
    dependencies: dict[str, set[str]] = {}
    for body in command_calls(text, command):
        args = cmake_args(body)
        if not args:
            continue
        target = args[0]
        deps = {
            arg
            for arg in args[1:]
            if arg
            not in {
                "PUBLIC",
                "PRIVATE",
                "INTERFACE",
                "LINK_PUBLIC",
                "LINK_PRIVATE",
            }
        }
        dependencies.setdefault(target, set()).update(deps)
    return dependencies


# ── specialised extractors ──────────────────────────────────────────

def plugin_export_calls(text: str) -> list[tuple[str, str]]:
    exports: list[tuple[str, str]] = []
    for body in command_calls(text, "pluginlib_export_plugin_description_file"):
        args = cmake_args(body)
        if len(args) >= 2:
            exports.append((args[0], args[1]))
    return exports


def install_targets(text: str) -> tuple[set[str], dict[str, str]]:
    targets: set[str] = set()
    target_exports: dict[str, str] = {}
    for body in command_calls(text, "install"):
        args = cmake_args(body)
        if "TARGETS" not in args:
            continue
        start = args.index("TARGETS") + 1
        block_targets: list[str] = []
        for token in args[start:]:
            if token in {"EXPORT", "RUNTIME", "ARCHIVE", "LIBRARY", "DESTINATION", "INCLUDES"}:
                break
            targets.add(token)
            block_targets.append(token)
        if "EXPORT" in args:
            export_index = args.index("EXPORT")
            if export_index + 1 < len(args):
                for target in block_targets:
                    target_exports[target] = args[export_index + 1]
    return targets, target_exports


def exported_target_names(text: str) -> set[str]:
    exports: set[str] = set()
    for body in command_calls(text, "ament_export_targets"):
        args = cmake_args(body)
        if args:
            exports.add(args[0])
    return exports


# ── formatting & insertion helpers ─────────────────────────────────

def format_cmake_command(command: str, args: list[str]) -> str:
    if len(args) <= 2:
        return f"{command}({' '.join(args)})"
    return f"{command}(\n" + "".join(f"  {arg}\n" for arg in args) + ")"


def insert_after_last_find_package(text: str, block: str) -> str:
    spans = command_call_spans(text, "find_package")
    if spans:
        insert_at = spans[-1][1]
        return text[:insert_at].rstrip() + "\n" + block.rstrip() + "\n\n" + text[insert_at:].lstrip()
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def insert_after_add_library(text: str, target: str, block: str) -> str:
    for _, end, body in command_call_spans(text, "add_library"):
        args = cmake_args(body)
        if args and args[0] == target:
            return text[:end].rstrip() + "\n" + block.rstrip() + "\n\n" + text[end:].lstrip()
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def insert_before_first_install_or_ament_package(text: str, block: str) -> str:
    anchors = command_call_spans(text, "install") + command_call_spans(text, "ament_package")
    if anchors:
        insert_at = min(start for start, _, _ in anchors)
        return text[:insert_at].rstrip() + "\n\n" + block.rstrip() + "\n\n" + text[insert_at:].lstrip()
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def insert_before_ament_package(text: str, block: str) -> str:
    spans = command_call_spans(text, "ament_package")
    if spans:
        insert_at = spans[0][0]
        return text[:insert_at].rstrip() + "\n\n" + block.rstrip() + "\n\n" + text[insert_at:].lstrip()
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"