"""Public ros-devkit command registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillCommand:
    name: str
    script_path: str


COMMANDS: dict[str, SkillCommand] = {
    "description-scaffold": SkillCommand(
        name="description-scaffold",
        script_path="description-scaffold/scripts/description_scaffold.py",
    ),
    "gazebo-simulation": SkillCommand(
        name="gazebo-simulation",
        script_path="gazebo-simulation/scripts/gazebo_simulation.py",
    ),
    "ros2-control-pluginize": SkillCommand(
        name="ros2-control-pluginize",
        script_path="scripts/ros2_control_pluginize_lib/__main__.py",
    ),
}
