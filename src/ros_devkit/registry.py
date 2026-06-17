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
}
