#!/usr/bin/env python3
"""Idempotently add pluginlib export code to a SystemInterface .cpp file."""

import argparse
from pathlib import Path


INCLUDE = '#include "pluginlib/class_list_macros.hpp"'


def insert_include(text: str) -> str:
    if INCLUDE in text:
        return text
    lines = text.splitlines()
    last_include = -1
    for index, line in enumerate(lines):
        if line.startswith("#include "):
            last_include = index
    if last_include >= 0:
        lines.insert(last_include + 1, INCLUDE)
    else:
        lines.insert(0, INCLUDE)
        lines.insert(1, "")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--namespace-name", required=True)
    parser.add_argument("--class-name", default="MyRobotHardwareInterface")
    args = parser.parse_args()

    path = Path(args.source)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    text = insert_include(text)
    export = (
        "PLUGINLIB_EXPORT_CLASS(\n"
        f"  {args.namespace_name}::{args.class_name},\n"
        "  hardware_interface::SystemInterface)\n"
    )
    if "PLUGINLIB_EXPORT_CLASS" not in text:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n" + export
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
