"""Add Gazebo Sim plugins to robot and world scaffold files."""

from __future__ import annotations

import argparse
from pathlib import Path

from package_xml_lib.parsing import read_package_name, robot_name_from_package
from utils.diagnostics import Finding, source as _source
from utils.fs import relative as _relative

from .discovery import discover_context
from .plugin_registry import (
    _fetch_plugin_name_from_github,
    _list_available_plugins,
    _resolve_plugin,
)
from .reporting import _print_report
from .world_sdf import _add_world_plugin_to_sdf, _ensure_sensors_system_in_world


SENSOR_PLUGIN_ALIASES = {
    "lidar", "camera", "rgbd_camera", "depth_camera", "gpu_lidar",
    "thermal_camera", "segmentation_camera", "boundingbox_camera",
}


def _append_once(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def _format_plugin_block(plugin_filename: str, plugin_name: str) -> str:
    """Render a <gazebo><plugin .../></gazebo> block for the robot xacro."""
    return (
        f'\n    <gazebo>\n'
        f'        <plugin filename="{plugin_filename}" name="{plugin_name}">\n'
        f'        </plugin>\n'
        f'    </gazebo>\n'
    )


def _add_model_plugin_to_xacro(
    gazebo_xacro_path: Path,
    plugin_filename: str,
    plugin_name: str,
    changed: list[str],
    root: Path,
) -> bool:
    """Insert (or merge) a <gazebo><plugin> block into the robot gazebo xacro.

    Returns True if the file was modified.
    """
    if not gazebo_xacro_path.exists():
        return False
    content = gazebo_xacro_path.read_text(encoding="utf-8")
    if plugin_filename in content and plugin_name in content:
        return False
    block = _format_plugin_block(plugin_filename, plugin_name)
    if "</robot>" in content:
        updated = content.replace("</robot>", f"{block}</robot>", 1)
    else:
        updated = content.rstrip() + "\n" + block
    gazebo_xacro_path.write_text(updated, encoding="utf-8")
    _append_once(changed, f"Updated: " + _relative(gazebo_xacro_path, root))
    return True


def add_plugin(args: argparse.Namespace) -> bool:
    """Add a Gazebo system plugin to the robot's gazebo xacro and/or world SDF."""
    plugin_alias = args.plugin
    context = discover_context(args.path, args.description_package, args.bringup_package)
    findings = [Finding("ERROR", error) for error in context.errors]
    changed: list[str] = []

    if args.list_plugins:
        print("Available Gazebo Sim plugins:")
        print(_list_available_plugins())
        return True

    if not plugin_alias:
        findings.append(Finding("ERROR", "No plugin specified. Use --plugin <name> or --list-plugins."))
        _print_report("ROS2 Gazebo Simulation — Add Plugin", context, findings)
        return False

    plugin = _resolve_plugin(plugin_alias)
    if plugin is None:
        findings.append(
            Finding(
                "ERROR",
                f"Unknown plugin alias '{plugin_alias}'. Use --list-plugins to see available plugins.",
            )
        )
        _print_report("ROS2 Gazebo Simulation — Add Plugin", context, findings)
        return False

    plugin_filename = str(plugin.get("filename", ""))
    plugin_name = str(plugin.get("name", ""))
    category = str(plugin.get("category", "model"))
    needs_sensors = bool(plugin.get("needs_sensors_system", False))

    # If the name is missing or generic, try to fetch from GitHub
    if not plugin_name and plugin.get("github_dir") and plugin.get("github_file"):
        fetched = _fetch_plugin_name_from_github(
            str(plugin["github_dir"]), str(plugin["github_file"])
        )
        if fetched:
            plugin_name = fetched
            findings.append(Finding("INFO", f"Fetched plugin name from GitHub: {plugin_name}"))
        else:
            findings.append(
                Finding("WARN", f"Could not fetch plugin name from GitHub for '{plugin_alias}'")
            )

    if not plugin_filename or not plugin_name:
        findings.append(
            Finding(
                "ERROR",
                f"Could not resolve filename and/or name for plugin '{plugin_alias}'",
            )
        )
        _print_report("ROS2 Gazebo Simulation — Add Plugin", context, findings)
        return False

    findings.append(
        Finding(
            "INFO",
            f"Plugin: filename='{plugin_filename}', name='{plugin_name}', category='{category}'",
        )
    )

    robot_name = args.robot_name

    # Determine robot name from description package
    if context.description_pkg is not None:
        pkg_name = read_package_name(context.description_pkg / "package.xml")
        robot_name = robot_name or robot_name_from_package(pkg_name)
    elif context.bringup_pkg is not None:
        bringup_name = read_package_name(context.bringup_pkg / "package.xml")
        robot_name = robot_name or robot_name_from_package(bringup_name)

    # Model-level plugins go in the <gazebo> tag of the robot xacro
    if category == "model":
        if context.description_pkg is None:
            findings.append(Finding("ERROR", "No *_description package found; cannot add model plugin"))
        elif not robot_name:
            findings.append(Finding("ERROR", "Could not determine robot name; pass --robot-name"))
        else:
            gazebo_xacro = context.description_pkg / "urdf" / f"{robot_name}_gazebo.xacro"
            if not gazebo_xacro.exists():
                findings.append(
                    Finding(
                        "WARN",
                        f"Gazebo xacro not found at {gazebo_xacro}; creating it with --setup first is recommended",
                        source=read_package_name(context.description_pkg / "package.xml"),
                    )
                )
            else:
                if _add_model_plugin_to_xacro(
                    gazebo_xacro, plugin_filename, plugin_name, changed, context.root
                ):
                    findings.append(
                        Finding(
                            "INFO",
                            f"Added <gazebo><plugin> block to {robot_name}_gazebo.xacro",
                            source=_source(
                                read_package_name(context.description_pkg / "package.xml"),
                                f"urdf/{robot_name}_gazebo.xacro",
                            ),
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            "INFO",
                            f"Plugin already present in {robot_name}_gazebo.xacro",
                        )
                    )

    # Sensor and world plugins go in the world .sdf
    if category in ("sensor", "world"):
        if context.bringup_pkg is None:
            findings.append(Finding("ERROR", "No *_bringup package found; cannot add world plugin"))
        else:
            world_name = args.world_name
            world_sdf = context.bringup_pkg / "worlds" / f"{world_name}.sdf"
            if not world_sdf.exists():
                findings.append(
                    Finding(
                        "WARN",
                        f"World SDF not found at {world_sdf}; creating it with --setup first is recommended",
                        source=read_package_name(context.bringup_pkg / "package.xml"),
                    )
                )
            else:
                # For sensor rendering plugins (lidar, camera, etc.), skip adding
                # the Sensors plugin itself to the world — instead we add the
                # Sensors system block below.
                skip_world_line = needs_sensors and category == "sensor"
                if not skip_world_line:
                    if _add_world_plugin_to_sdf(
                        world_sdf, plugin_filename, plugin_name, changed, context.root
                    ):
                        findings.append(
                            Finding(
                                "INFO",
                                f"Added <plugin> line to {world_name}.sdf",
                                source=_source(
                                    read_package_name(context.bringup_pkg / "package.xml"),
                                    f"worlds/{world_name}.sdf",
                                ),
                            )
                        )
                    else:
                        findings.append(
                            Finding("INFO", f"Plugin already present in {world_name}.sdf")
                        )

                if needs_sensors:
                    if _ensure_sensors_system_in_world(world_sdf, changed, context.root):
                        findings.append(
                            Finding(
                                "INFO",
                                f"Added Sensors system plugin (ogre2) to {world_name}.sdf",
                                source=_source(
                                    read_package_name(context.bringup_pkg / "package.xml"),
                                    f"worlds/{world_name}.sdf",
                                ),
                            )
                        )
                    else:
                        findings.append(
                            Finding("INFO", f"Sensors system plugin already present in {world_name}.sdf")
                        )

    findings.extend(Finding("INFO", path) for path in changed)
    if not changed:
        findings.append(Finding("INFO", "No files were modified"))

    _print_report("ROS2 Gazebo Simulation — Add Plugin", context, findings)
    return not any(finding.severity == "ERROR" for finding in findings)
