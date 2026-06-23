"""CLI entry point: ``python -m ros2_control_pluginize_lib`` (run from the shared scripts/ directory)."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the shared scripts/ directory (parent of ros2_control_pluginize_lib/)
# is importable so that ``utils`` and sibling packages resolve correctly.
_shared_scripts = Path(__file__).resolve().parents[1]
if str(_shared_scripts) not in sys.path:
    sys.path.insert(0, str(_shared_scripts))

from ros2_control_pluginize_lib.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())