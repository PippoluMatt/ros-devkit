"""CLI entry point: ``python -m gazebo_simulation_lib`` (run from the shared scripts/ directory)."""

from __future__ import annotations

import sys
from pathlib import Path

_shared_scripts = Path(__file__).resolve().parents[1]
if str(_shared_scripts) not in sys.path:
    sys.path.insert(0, str(_shared_scripts))

from gazebo_simulation_lib.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
