#!/usr/bin/env python3
"""Run ros-devkit diagnostics."""

from __future__ import annotations

import sys

from ros_devkit.doctor import main


if __name__ == "__main__":
    sys.exit(main())
