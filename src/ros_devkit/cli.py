"""Command-line entrypoint for ros-devkit."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, load_config
from .doctor import main as doctor_main
from .registry import COMMANDS


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args[0] in {"-h", "--help", "--helpt"}:
        _print_help()
        return 0

    if args[0] == "--version":
        print(f"ros-devkit {__version__}")
        return 0

    command_name = args[0]
    command_args = args[1:]

    if command_name == "doctor":
        return doctor_main(command_args)

    if command_name == "update":
        return _run_update(command_args)

    command = COMMANDS.get(command_name)
    if command is None:
        print(f"ERROR: Unknown command: {command_name}", file=sys.stderr)
        print("Run 'ros-devkit --help' to see available commands.", file=sys.stderr)
        return 2

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    script = config.skill_root / command.script_path
    if not script.is_file():
        print(f"ERROR: Missing script: {script}", file=sys.stderr)
        print("Run 'ros-devkit doctor' to inspect the configured skill root.", file=sys.stderr)
        return 1

    completed = subprocess.run([sys.executable, str(script), *command_args])
    return completed.returncode


def _run_update(args: list[str]) -> int:
    source_dir = os.environ.get("ROS_DEVKIT_SOURCE")
    if not source_dir:
        candidate_source = Path(__file__).resolve().parents[2]
        if (candidate_source / "scripts" / "update.sh").is_file():
            source_dir = str(candidate_source)

    if not source_dir:
        print(
            "ERROR: update is only available for installer-managed installs.",
            file=sys.stderr,
        )
        return 1

    script = Path(source_dir).expanduser() / "scripts" / "update.sh"
    if not script.is_file():
        print(f"ERROR: Missing updater script: {script}", file=sys.stderr)
        return 1

    completed = subprocess.run(["bash", str(script), *args])
    return completed.returncode


def _print_help() -> None:
    print("usage: ros-devkit <command> [args...]")
    print()
    print("Commands:")
    for command_name in sorted(COMMANDS):
        print(f"  {command_name}")
    print("  doctor")
    print("  update")
    print()
    print("Examples:")
    print("  ros-devkit description-scaffold --verify")
    print("  ros-devkit description-scaffold --split")
    print("  ros-devkit description-scaffold --create my_robot")
    print("  ros-devkit gazebo-simulation --diagnose")
    print("  ros-devkit gazebo-simulation --setup")
    print("  ros-devkit doctor")
    print("  ros-devkit update")
    print("  ros-devkit update --dry-run")
    print("  ros-devkit update --force")


if __name__ == "__main__":
    sys.exit(main())
