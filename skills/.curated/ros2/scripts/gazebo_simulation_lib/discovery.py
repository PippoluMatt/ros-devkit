"""Package discovery for Gazebo simulation workflows."""

from __future__ import annotations

import os
from pathlib import Path

from package_xml_lib.parsing import read_package_name

from .models import Context


DISCOVERY_SKIP_DIRS = {".git", ".venv", "__pycache__", "build", "install", "log"}


def _should_skip_dir(dirname: str) -> bool:
    return dirname in DISCOVERY_SKIP_DIRS or dirname.startswith(".")


def _find_packages(root: Path, suffix: str) -> list[Path]:
    candidates: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [dirname for dirname in dirnames if not _should_skip_dir(dirname)]
        if "package.xml" not in filenames:
            continue
        pkg_dir = Path(current)
        if read_package_name(pkg_dir / "package.xml").endswith(suffix):
            candidates.append(pkg_dir.resolve())
    return sorted(candidates)


def _resolve_optional_package(value: str | None, suffix: str, label: str) -> tuple[Path | None, list[str]]:
    if not value:
        return None, []
    path = Path(value).expanduser().resolve()
    errors: list[str] = []
    if not path.is_dir():
        errors.append(f"{label} package path is not a directory: {path}")
        return None, errors
    pkg_name = read_package_name(path / "package.xml")
    if not pkg_name.endswith(suffix):
        errors.append(f"{label} package should end with {suffix}: {pkg_name}")
    return path, errors


def _choose_discovered(candidates: list[Path], label: str, root: Path) -> tuple[Path | None, list[str]]:
    if len(candidates) == 1:
        return candidates[0], []
    if not candidates:
        return None, []
    errors = [f"Multiple {label} packages found under {root}; pass --{label.replace(' ', '-')}-package"]
    errors.extend(f"Candidate: {candidate}" for candidate in candidates)
    return None, errors


def discover_context(
    target: str | None,
    description_package: str | None,
    bringup_package: str | None,
) -> Context:
    target_path = Path(target).expanduser().resolve() if target else Path.cwd().resolve()
    root = target_path
    errors: list[str] = []

    explicit_description, explicit_errors = _resolve_optional_package(
        description_package, "_description", "description"
    )
    errors.extend(explicit_errors)
    explicit_bringup, explicit_errors = _resolve_optional_package(
        bringup_package, "_bringup", "bringup"
    )
    errors.extend(explicit_errors)

    description_pkg = explicit_description
    bringup_pkg = explicit_bringup

    if target_path.is_dir() and (target_path / "package.xml").exists():
        pkg_name = read_package_name(target_path / "package.xml")
        root = target_path.parent
        if pkg_name.endswith("_description") and description_pkg is None:
            description_pkg = target_path
        elif pkg_name.endswith("_bringup") and bringup_pkg is None:
            bringup_pkg = target_path

    if not target_path.exists():
        errors.append(f"Target path does not exist: {target_path}")
        return Context(target_path, description_pkg, bringup_pkg, errors)

    search_root = root if root.exists() else target_path
    if description_pkg is None:
        discovered, discovered_errors = _choose_discovered(
            _find_packages(search_root, "_description"), "description", search_root
        )
        description_pkg = discovered
        errors.extend(discovered_errors)
    if bringup_pkg is None:
        discovered, discovered_errors = _choose_discovered(
            _find_packages(search_root, "_bringup"), "bringup", search_root
        )
        bringup_pkg = discovered
        errors.extend(discovered_errors)

    return Context(search_root, description_pkg, bringup_pkg, errors)
