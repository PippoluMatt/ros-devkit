from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path


GAZEBO_PATH = Path(__file__).resolve().parents[1] / "scripts/gazebo_simulation.py"

spec = importlib.util.spec_from_file_location("gazebo_simulation", GAZEBO_PATH)
assert spec is not None
gazebo_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = gazebo_module
spec.loader.exec_module(gazebo_module)


class GazeboSimulationChecks(unittest.TestCase):
    def test_print_report_includes_finding_sources(self) -> None:
        context = gazebo_module.Context(
            root=Path("/tmp/ws/src"),
            description_pkg=Path("/tmp/ws/src/pawy_description"),
            bringup_pkg=Path("/tmp/ws/src/pawy_bringup"),
            errors=[],
        )
        findings = [
            gazebo_module.Finding(
                "WARN",
                "CMakeLists.txt does not install present config/ directory",
                source="pawy_bringup",
            ),
            gazebo_module.Finding(
                "WARN",
                "missing Gazebo launch wiring: ros_gz_bridge parameter_bridge node",
                source="pawy_bringup:launch/display.launch.xml",
            ),
        ]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            gazebo_module._print_report(
                "ROS2 Gazebo Simulation Diagnostics",
                context,
                findings,
            )

        text = output.getvalue()
        self.assertIn(
            "WARN: [pawy_bringup] "
            "CMakeLists.txt does not install present config/ directory",
            text,
        )
        self.assertIn(
            "WARN: [pawy_bringup:launch/display.launch.xml] "
            "missing Gazebo launch wiring: ros_gz_bridge parameter_bridge node",
            text,
        )

    def test_diagnose_bringup_attaches_package_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg_dir = Path(tmp) / "pawy_bringup"
            (pkg_dir / "launch").mkdir(parents=True)
            (pkg_dir / "config").mkdir()
            (pkg_dir / "package.xml").write_text(
                """<?xml version="1.0"?>
<package format="3">
  <name>pawy_bringup</name>
</package>
""",
                encoding="utf-8",
            )
            (pkg_dir / "CMakeLists.txt").write_text(
                """cmake_minimum_required(VERSION 3.8)
project(pawy_bringup)

install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)
""",
                encoding="utf-8",
            )
            (pkg_dir / "launch" / "display.launch.xml").write_text(
                "<launch />",
                encoding="utf-8",
            )

            findings: list[gazebo_module.Finding] = []
            gazebo_module._diagnose_bringup(pkg_dir, findings)

        simplified = {
            (finding.severity, finding.message, finding.source)
            for finding in findings
        }
        self.assertIn(
            (
                "WARN",
                "CMakeLists.txt does not install present config/ directory",
                "pawy_bringup",
            ),
            simplified,
        )
        self.assertIn(
            (
                "WARN",
                "missing Gazebo launch wiring: ros_gz_sim gz_sim.launch.py include, "
                "ros_gz_sim create robot_description node, "
                "ros_gz_bridge parameter_bridge node, gazebo_bridge.yaml config_file parameter",
                "pawy_bringup:launch/display.launch.xml",
            ),
            simplified,
        )


if __name__ == "__main__":
    unittest.main()
