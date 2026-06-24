"""Generic package.xml mutation helpers.

These functions read and modify ``package.xml`` files without any knowledge
of skill-specific concepts.  They are shared by the ``ros2-control-pluginize``,
``description-scaffold``, and ``gazebo-simulation`` skills.
"""

from __future__ import annotations

import re
from pathlib import Path

from utils.fs import relative, write_file_if_changed

from .parsing import read_dependencies


def ensure_dependencies(
    path: Path,
    dependencies: list[str],
    tag: str = "depend",
    pkg_dir: Path | None = None,
    changed: list[str] | None = None,
) -> bool:
    """Insert missing ``<tag>`` entries for dependencies not already declared.

    New entries are inserted before ``<export>`` if present, otherwise before
    ``</package>``.  The file is written only when content changes (via
    :func:`utils.fs.write_file_if_changed`).

    Returns ``True`` when the file was written, ``False`` when unchanged.
    When *changed* is not ``None`` and the file was modified, a string of the
    form ``"Updated: <relative-path>"`` is appended.
    """
    existing = read_dependencies(path)
    missing = [dep for dep in dependencies if dep not in existing]
    if not missing:
        return False

    before = path.read_text(encoding="utf-8")
    tags = "\n".join(f"  <{tag}>{dep}</{tag}>" for dep in missing)
    export_match = re.search(r"(?m)^[ \t]*<export\b", before)
    if export_match:
        after = (
            before[: export_match.start()].rstrip()
            + "\n\n"
            + tags
            + "\n\n"
            + before[export_match.start():].lstrip()
        )
    else:
        package_end = re.search(r"(?m)^[ \t]*</package>", before)
        if not package_end:
            return False
        after = (
            before[: package_end.start()].rstrip()
            + "\n\n"
            + tags
            + "\n"
            + before[package_end.start():]
        )

    written = write_file_if_changed(path, after)
    if written and changed is not None:
        ref = pkg_dir if pkg_dir is not None else path.parent
        changed.append(f"Updated: {relative(path, ref)}")
    return written


def ensure_exec_depends(
    path: Path,
    dependencies: list[str],
    pkg_dir: Path | None = None,
    changed: list[str] | None = None,
) -> bool:
    """Convenience wrapper for :func:`ensure_dependencies` with ``tag="exec_depend"``."""
    return ensure_dependencies(
        path,
        dependencies,
        tag="exec_depend",
        pkg_dir=pkg_dir,
        changed=changed,
    )