"""File-system helpers: conditional writes and relative paths."""

from __future__ import annotations

from pathlib import Path


def write_file_if_changed(path: Path, content: str) -> bool:
    """Write *content* to *path* only when it differs from the current file.

    Returns ``True`` when the file was written (created or updated),
    ``False`` when the content was already identical.
    """
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return False
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def relative(path: Path, root: Path) -> str:
    """Return *path* relative to *root*, falling back to the full string."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)