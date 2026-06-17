#!/usr/bin/env python3
"""Add or update share-directory installation rules."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SHARED_SCRIPTS))

from cmake import add_install_share_directories  # noqa: E402


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_if_changed(path: Path, before: str, after: str) -> bool:
    if after == before:
        return False
    path.write_text(after, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cmakelists", type=Path)
    parser.add_argument("directories", nargs="+")
    args = parser.parse_args()

    before = read_text(args.cmakelists)
    after = add_install_share_directories(before, args.directories)
    changed = write_if_changed(args.cmakelists, before, after)
    print("updated" if changed else "unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
