"""CLI entry point: ``python -m package_xml_lib`` (run from the shared scripts/ directory)."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the shared scripts/ directory (parent of package_xml_lib/) is importable
# so that ``utils`` and ``package_xml_lib`` resolve correctly.
_shared_scripts = Path(__file__).resolve().parents[1]
if str(_shared_scripts) not in sys.path:
    sys.path.insert(0, str(_shared_scripts))

from package_xml_lib.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())