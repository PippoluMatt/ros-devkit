"""Diagnostics for ros-devkit configuration and command mappings."""

from __future__ import annotations

from pathlib import Path
import sys

from .config import ConfigError, RosDevkitConfig, load_config
from .registry import COMMANDS


def check_config(config: RosDevkitConfig) -> tuple[list[str], list[str]]:
    infos: list[str] = []
    errors: list[str] = []

    infos.append(f"Agent          : {config.agent}")
    infos.append(f"Namespace root : {config.skill_root}")
    infos.append(f"Config file    : {config.config_file}")

    if not config.skill_root.exists():
        errors.append(f"Namespace root does not exist: {config.skill_root}")
    elif not config.skill_root.is_dir():
        errors.append(f"Namespace root is not a directory: {config.skill_root}")

    infos.append("Commands    :")
    for command in COMMANDS.values():
        script = config.skill_root / command.script_path
        if script.is_file():
            infos.append(f"  {command.name}: OK")
        else:
            infos.append(f"  {command.name}: MISSING")
            errors.append(f"Missing script: {script}")

    return infos, errors


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if args in (["-h"], ["--help"]):
        print("usage: ros-devkit doctor")
        print()
        print("Check ros-devkit config and mapped skill scripts.")
        return 0
    if args:
        print(f"ERROR: doctor does not accept arguments: {' '.join(args)}", file=sys.stderr)
        return 2

    try:
        config = load_config()
        infos, errors = check_config(config)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for line in infos:
        print(line)

    if errors:
        print()
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
