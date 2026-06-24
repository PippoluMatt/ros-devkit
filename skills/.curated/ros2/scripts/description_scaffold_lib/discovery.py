"""Description package discovery helpers."""

from __future__ import annotations

import os
from pathlib import Path

from package_xml_lib.parsing import read_package_name
from utils.diagnostics import Finding, print_finding


DISCOVERY_SKIP_DIRS = {".git", "build", "install", "log"}


def _should_skip_discovery_dir(name: str) -> bool:
    return name in DISCOVERY_SKIP_DIRS or name.startswith(".")


def _find_description_packages(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not _should_skip_discovery_dir(dirname)
        ]
        if "package.xml" not in filenames:
            continue

        pkg_dir = Path(current)
        pkg_name = read_package_name(pkg_dir / "package.xml")
        if pkg_name.endswith("_description"):
            candidates.append(pkg_dir.resolve())

    return sorted(candidates)


def resolve_package_directory(pkg_dir: str | Path | None) -> Path | None:
    if pkg_dir:
        return Path(pkg_dir).expanduser().resolve()

    root = Path.cwd().resolve()
    candidates = _find_description_packages(root)

    if not candidates:
        print_finding(
            Finding(
                "ERROR",
                f"No *_description package found under current project: {root}",
            )
        )
        return None

    if len(candidates) > 1:
        print_finding(
            Finding(
                "ERROR",
                f"Multiple *_description packages found under current project: {root}",
            )
        )
        for candidate in candidates:
            print_finding(Finding("INFO", f"Candidate: {candidate.relative_to(root)}"))
        return None

    return candidates[0]
