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
    if os.environ.get("ROS_DEVKIT_LOCAL_SANDBOX"):
        print(
            "ERROR: update is disabled for local sandbox installs. "
            "Re-run scripts/install.sh --local-sandbox PATH instead.",
            file=sys.stderr,
        )
        return 1

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
    print(f"ros-devkit {__version__} — ROS 2 development toolkit")
    print()
    print("USAGE")
    print("  ros-devkit <command> [args...]")
    print()
    print("GLOBAL OPTIONS")
    print("  -h, --help     Show this help message")
    print("  --version      Print ros-devkit version")
    print()
    print("COMMANDS")
    print()
    print("  description-scaffold    Scaffold, verify, or modularise URDF/xacro packages")
    print("  gazebo-simulation       Diagnose and set up Gazebo simulation wiring")
    print("  doctor                  Check ros-devkit config and skill script health")
    print("  update                  Update an installer-managed install to latest main")
    print()
    print("  Run 'ros-devkit <command> --help' for command-specific options.")
    print()
    print("description-scaffold")
    print("  Scaffold, verify, or split a URDF/xacro description package.")
    print()
    print("  Modes (mutually exclusive, one required):")
    print("    --verify [PACKAGE_DIR]     Verify package structure (auto-discovers if omitted)")
    print("    --create [TARGET]          Create a new package or repair an existing directory")
    print("    --split [PACKAGE_DIR]      Split a monolithic xacro into modular files")
    print()
    print("  Options:")
    print("    --sensors SENSOR,SENSOR      Comma-separated sensor names (e.g. lidar,camera)")
    print("    --destination-directory DIR  Directory for new package (default: current dir)")
    print("    --source FILE                Source xacro for --split when ambiguous")
    print("    --maintainer NAME            Maintainer name for ros2 pkg create")
    print("    --email EMAIL                Maintainer email for ros2 pkg create")
    print("    --license LICENSE            License for ros2 pkg create")
    print()
    print("  Examples:")
    print("    ros-devkit description-scaffold --verify")
    print("    ros-devkit description-scaffold --verify my_robot_description")
    print("    ros-devkit description-scaffold --create my_robot_description --sensors lidar,camera")
    print("    ros-devkit description-scaffold --create my_robot_description --dir ~/ros2_ws/src")
    print("    ros-devkit description-scaffold --split")
    print("    ros-devkit description-scaffold --split my_robot_description --source urdf/robot.urdf.xacro")
    print()
    print("gazebo-simulation")
    print("  Diagnose or set up Gazebo simulation wiring for ROS 2 packages.")
    print()
    print("  Modes (mutually exclusive, one required):")
    print("    --diagnose    Inspect Gazebo simulation wiring (description + bringup)")
    print("    --setup       Create missing Gazebo scaffold files (bridge, world, launch)")
    print()
    print("  Options:")
    print("    [PATH]                     Project root or package path (default: current dir)")
    print("    --description-package DIR  Explicit *_description package path")
    print("    --bringup-package DIR      Explicit *_bringup package path")
    print("    --robot-name NAME          Robot/model name (auto-detected if omitted)")
    print("    --world-name NAME          Gazebo world name (default: test_world)")
    print()
    print("  Examples:")
    print("    ros-devkit gazebo-simulation --diagnose")
    print("    ros-devkit gazebo-simulation --diagnose ~/ros2_ws/src")
    print("    ros-devkit gazebo-simulation --setup --world-name my_world")
    print("    ros-devkit gazebo-simulation --setup --bringup-package ~/ros2_ws/src/my_robot_bringup")
    print()
    print("doctor")
    print("  Check ros-devkit configuration and mapped skill script health.")
    print()
    print("  Examples:")
    print("    ros-devkit doctor")
    print()
    print("update")
    print("  Update an installer-managed ros-devkit from the latest main branch.")
    print()
    print("  Options:")
    print("    --dry-run    Stage and validate without replacing installed files")
    print("    --force      Replace installed skills even if local edits are detected")
    print("    -h, --help   Show update help")
    print()
    print("  Examples:")
    print("    ros-devkit update")
    print("    ros-devkit update --dry-run")
    print("    ros-devkit update --force")


if __name__ == "__main__":
    sys.exit(main())
