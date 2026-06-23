"""XML helpers shared across skills."""

from __future__ import annotations


def local_name(tag: str) -> str:
    """Strip an XML namespace URI from an ElementTree tag."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag