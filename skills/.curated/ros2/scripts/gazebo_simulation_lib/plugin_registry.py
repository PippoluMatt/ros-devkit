"""Gazebo Sim plugin registry loading and lookup."""

from __future__ import annotations

import re
from pathlib import Path
import urllib.error
import urllib.request

PLUGIN_REGISTRY_PATH = (
    Path(__file__).resolve().parents[2]
    / "gazebo-simulation"
    / "references"
    / "plugin_registry.yaml"
)
GZ_SIM_RAW_BASE = "https://raw.githubusercontent.com/gazebosim/gz-sim/main/src/systems"


def _load_plugin_registry() -> dict[str, dict[str, object]]:
    """Load the plugin registry from references/plugin_registry.yaml.

    Falls back to a simple parser if PyYAML is not installed.
    """
    if not PLUGIN_REGISTRY_PATH.exists():
        return {}
    text = PLUGIN_REGISTRY_PATH.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items() if isinstance(v, dict)}
        return {}
    except ImportError:
        return _parse_simple_plugin_registry(text)


def _parse_simple_plugin_registry(text: str) -> dict[str, dict[str, object]]:
    """Minimal YAML parser for the flat plugin registry structure."""
    registry: dict[str, dict[str, object]] = {}
    current_key: str | None = None
    current_entry: dict[str, object] = {}
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        stripped = line.strip()
        if not line.startswith(" "):
            if current_key is not None:
                registry[current_key] = current_entry
            if stripped.endswith(":"):
                current_key = stripped[:-1].strip()
                current_entry = {}
            else:
                current_key = None
                current_entry = {}
        elif current_key is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value.lower() in ("true", "false"):
                current_entry[key] = value.lower() == "true"
            else:
                current_entry[key] = value
    if current_key is not None:
        registry[current_key] = current_entry
    return registry


def _fetch_plugin_name_from_github(github_dir: str, github_file: str) -> str | None:
    """Fetch the last non-empty line of the .cc file from GitHub.

    The last line typically contains GZ_ADD_PLUGIN_ALIAS(ClassName, \"gz::sim::systems::ClassName\").
    Returns the fully-qualified name, e.g. "gz::sim::systems::DiffDrive".
    """
    url = f"{GZ_SIM_RAW_BASE}/{github_dir}/{github_file}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError):
        return None
    for line in reversed(body.splitlines()):
        line = line.strip()
        if not line:
            continue
        match = re.search(r'GZ_ADD_PLUGIN_ALIAS\s*\([^,]+,\s*"([^"]+)"\)', line)
        if match:
            return match.group(1)
    return None


def _resolve_plugin(plugin_alias: str) -> dict[str, object] | None:
    """Look up a plugin by alias in the registry, or fetch from GitHub.

    Returns a dict with keys: filename, name, category, needs_sensors_system.
    Returns None if the plugin cannot be resolved.
    """
    registry = _load_plugin_registry()
    entry = registry.get(plugin_alias)
    if entry:
        return entry
    # Try fuzzy match: replace spaces/dashes/underscores
    normalised = plugin_alias.lower().replace(" ", "_").replace("-", "_")
    for key, value in registry.items():
        if key.lower().replace(" ", "_").replace("-", "_") == normalised:
            return value
    return None


def _list_available_plugins() -> str:
    """Return a formatted, human-readable table of available plugins."""
    registry = _load_plugin_registry()
    if not registry:
        return "  (plugin registry not found at references/plugin_registry.yaml)"

    # Group by category preserving insertion order
    categories: dict[str, list[tuple[str, dict[str, object]]]] = {
        "model": [],
        "sensor": [],
        "world": [],
    }
    for alias, entry in registry.items():
        cat = str(entry.get("category", "model"))
        categories.setdefault(cat, []).append((alias, entry))

    category_titles: list[tuple[str, str, str]] = [
        ("model", "Model plugins", "added to <gazebo> in the robot xacro"),
        ("sensor", "Sensor plugins", "added as <plugin/> in the world .sdf"),
        ("world", "World plugins", "added as <plugin/> in the world .sdf"),
    ]

    lines: list[str] = []
    for cat_key, title, subtitle in category_titles:
        entries = categories.get(cat_key, [])
        if not entries:
            continue
        lines.append("")
        lines.append(f"  {title} ({subtitle})")
        lines.append("")
        # Column widths: alias | filename | name | description
        alias_w = max(len(a) for a, _ in entries)
        alias_w = max(alias_w, len("alias"))
        file_w = max(len(str(e.get("filename", ""))) for _, e in entries)
        file_w = max(file_w, len("filename"))
        name_w = max(len(str(e.get("name", ""))) for _, e in entries)
        name_w = max(name_w, len("name"))
        desc_w = max(len(str(e.get("description", ""))) for _, e in entries)
        desc_w = max(desc_w, len("description"))

        # Header
        lines.append(
            f"  {'alias':<{alias_w}}  {'filename':<{file_w}}  {'name':<{name_w}}  {'description'}"
        )
        lines.append(
            f"  {'-' * alias_w}  {'-' * file_w}  {'-' * name_w}  {'-' * desc_w}"
        )
        for alias, entry in entries:
            filename = str(entry.get("filename", ""))
            name = str(entry.get("name", ""))
            desc = str(entry.get("description", ""))
            lines.append(
                f"  {alias:<{alias_w}}  {filename:<{file_w}}  {name:<{name_w}}  {desc}"
            )

    lines.append("")
    lines.append("  Usage:  ros-devkit gazebo-simulation --add-plugin --plugin <alias>")
    return "\n".join(lines)
