"""World SDF helpers for Gazebo simulation workflows."""

from __future__ import annotations

import os
from pathlib import Path

from utils.fs import relative as _relative


def _append_once(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def _resolve_gz_sim_plugin_dir() -> Path | None:
    """Return the directory containing gz-sim plugin .so files, if found."""
    candidates = [
        Path("/opt/ros/jazzy/opt/gz_sim_vendor/lib/gz-sim-8/plugins"),
        Path("/usr/lib/gz-sim-8/plugins"),
        Path("/usr/local/lib/gz-sim-8/plugins"),
    ]
    # Also check GZ_SIM_SYSTEM_PLUGIN_PATH
    env_path = os.environ.get("GZ_SIM_SYSTEM_PLUGIN_PATH", "")
    if env_path:
        candidates.insert(0, Path(env_path))
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _world_plugin_line(plugin_filename: str, plugin_name: str) -> str:
    """Render a self-closing <plugin> line for the world SDF."""
    return f'    <plugin filename="{plugin_filename}" name="{plugin_name}"/>'


def _world_sensors_system_block() -> str:
    """Render the Sensors system plugin block with ogre2 render engine."""
    return (
        '    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">\n'
        '      <render_engine>ogre2</render_engine>\n'
        '    </plugin>'
    )


def _add_world_plugin_to_sdf(
    world_sdf_path: Path,
    plugin_filename: str,
    plugin_name: str,
    changed: list[str],
    root: Path,
) -> bool:
    """Add a <plugin> line inside the <world> tag of the world SDF.

    Returns True if the file was modified.
    """
    if not world_sdf_path.exists():
        return False
    content = world_sdf_path.read_text(encoding="utf-8")
    if plugin_filename in content and plugin_name in content:
        return False
    plugin_line = _world_plugin_line(plugin_filename, plugin_name)
    # Insert after the last existing <plugin .../> line inside <world>,
    # otherwise right after the opening <world ...> tag.
    lines = content.splitlines()
    insert_at = None
    in_world = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("<world") or stripped.startswith("<world "):
            in_world = True
        if in_world and "<plugin " in line and "/>" in line:
            insert_at = index + 1
        if in_world and stripped.startswith("</world>"):
            break
    if insert_at is None:
        for index, line in enumerate(lines):
            if "<world" in line:
                insert_at = index + 1
                break
    if insert_at is None:
        return False
    lines.insert(insert_at, plugin_line)
    world_sdf_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _append_once(changed, f"Updated: " + _relative(world_sdf_path, root))
    return True


def _ensure_sensors_system_in_world(
    world_sdf_path: Path,
    changed: list[str],
    root: Path,
) -> bool:
    """Ensure the Sensors system plugin (with ogre2 render engine) is in the world SDF.

    Returns True if the file was modified.
    """
    if not world_sdf_path.exists():
        return False
    content = world_sdf_path.read_text(encoding="utf-8")
    if "gz-sim-sensors-system" in content and "gz::sim::systems::Sensors" in content:
        return False
    block = _world_sensors_system_block()
    lines = content.splitlines()
    insert_at = None
    in_world = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("<world") or stripped.startswith("<world "):
            in_world = True
        if in_world and "<plugin " in line and "/>" in line:
            insert_at = index + 1
        if in_world and stripped.startswith("</world>"):
            break
    if insert_at is None:
        for index, line in enumerate(lines):
            if "<world" in line:
                insert_at = index + 1
                break
    if insert_at is None:
        return False
    lines.insert(insert_at, block)
    world_sdf_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _append_once(changed, f"Updated: " + _relative(world_sdf_path, root))
    return True
