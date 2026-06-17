"""Configuration loading for ros-devkit."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shlex


CONFIG_DIRNAME = "ros-devkit"
CONFIG_FILENAME = "config.env"


@dataclass(frozen=True)
class RosDevkitConfig:
    agent: str
    skill_root: Path
    config_file: Path


class ConfigError(RuntimeError):
    pass


def default_config_file() -> Path:
    config_override = os.environ.get("ROS_DEVKIT_CONFIG")
    if config_override:
        return Path(config_override).expanduser()

    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home).expanduser() / CONFIG_DIRNAME / CONFIG_FILENAME

    return Path.home() / ".config" / CONFIG_DIRNAME / CONFIG_FILENAME


def load_config(config_file: Path | None = None) -> RosDevkitConfig:
    path = (config_file or default_config_file()).expanduser()
    if not path.exists():
        raise ConfigError(
            f"Config file not found: {path}\n"
            "Run scripts/configure_ros_devkit.sh --agent codex"
        )

    values = _parse_env_file(path)
    agent = values.get("ROS_DEVKIT_AGENT", "").strip()
    skill_root = values.get("ROS_DEVKIT_SKILL_ROOT", "").strip()

    if not agent:
        raise ConfigError(f"Missing ROS_DEVKIT_AGENT in config file: {path}")
    if not skill_root:
        raise ConfigError(f"Missing ROS_DEVKIT_SKILL_ROOT in config file: {path}")

    return RosDevkitConfig(
        agent=agent,
        skill_root=Path(skill_root).expanduser(),
        config_file=path,
    )


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        try:
            parts = shlex.split(line, comments=True, posix=True)
        except ValueError as exc:
            raise ConfigError(f"Invalid config syntax at {path}:{line_number}: {exc}") from exc

        if len(parts) != 1 or "=" not in parts[0]:
            raise ConfigError(f"Invalid config assignment at {path}:{line_number}: {raw_line}")

        key, value = parts[0].split("=", 1)
        values[key] = value

    return values
