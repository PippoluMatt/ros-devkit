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


    def test_add_model_plugin_to_xacro(self) -> None:
        """Adding a model-level plugin inserts a <gazebo><plugin> block."""
        with tempfile.TemporaryDirectory() as tmp:
            xacro_path = Path(tmp) / "robot_gazebo.xacro"
            xacro_path.write_text(
                '<?xml version="1.0" ?>\n'
                '<robot name="robot" xmlns:xacro="http://www.ros.org/wiki/xacro">\n'
                '    <gazebo reference="base_link">\n'
                '        <material>Gazebo/Grey</material>\n'
                '    </gazebo>\n'
                '</robot>\n',
                encoding="utf-8",
            )
            changed: list[str] = []
            result = gazebo_module._add_model_plugin_to_xacro(
                xacro_path,
                "gz-sim-diff-drive-system",
                "gz::sim::systems::DiffDrive",
                changed,
                Path(tmp),
            )
            self.assertTrue(result)
            content = xacro_path.read_text(encoding="utf-8")
            self.assertIn("gz-sim-diff-drive-system", content)
            self.assertIn("gz::sim::systems::DiffDrive", content)
            self.assertIn("<gazebo>", content)
            self.assertIn("</robot>", content)

    def test_add_model_plugin_idempotent(self) -> None:
        """Adding the same model plugin twice does not duplicate the block."""
        with tempfile.TemporaryDirectory() as tmp:
            xacro_path = Path(tmp) / "robot_gazebo.xacro"
            xacro_path.write_text(
                '<?xml version="1.0" ?>\n'
                '<robot name="robot" xmlns:xacro="http://www.ros.org/wiki/xacro">\n'
                '    <gazebo reference="base_link">\n'
                '        <material>Gazebo/Grey</material>\n'
                '    </gazebo>\n'
                '</robot>\n',
                encoding="utf-8",
            )
            changed: list[str] = []
            gazebo_module._add_model_plugin_to_xacro(
                xacro_path,
                "gz-sim-diff-drive-system",
                "gz::sim::systems::DiffDrive",
                changed,
                Path(tmp),
            )
            second = gazebo_module._add_model_plugin_to_xacro(
                xacro_path,
                "gz-sim-diff-drive-system",
                "gz::sim::systems::DiffDrive",
                changed,
                Path(tmp),
            )
            self.assertFalse(second)

    def test_add_world_plugin_to_sdf(self) -> None:
        """Adding a sensor plugin inserts a <plugin> line into the world SDF."""
        with tempfile.TemporaryDirectory() as tmp:
            sdf_path = Path(tmp) / "test_world.sdf"
            sdf_path.write_text(
                '<?xml version="1.0" ?>\n'
                '<sdf version="1.9">\n'
                '  <world name="test_world">\n'
                '    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>\n'
                '  </world>\n'
                '</sdf>\n',
                encoding="utf-8",
            )
            changed: list[str] = []
            result = gazebo_module._add_world_plugin_to_sdf(
                sdf_path,
                "gz-sim-imu-system",
                "gz::sim::systems::Imu",
                changed,
                Path(tmp),
            )
            self.assertTrue(result)
            content = sdf_path.read_text(encoding="utf-8")
            self.assertIn("gz-sim-imu-system", content)
            self.assertIn("gz::sim::systems::Imu", content)

    def test_ensure_sensors_system_in_world(self) -> None:
        """Adding a rendering sensor also adds the Sensors system plugin."""
        with tempfile.TemporaryDirectory() as tmp:
            sdf_path = Path(tmp) / "test_world.sdf"
            sdf_path.write_text(
                '<?xml version="1.0" ?>\n'
                '<sdf version="1.9">\n'
                '  <world name="test_world">\n'
                '    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>\n'
                '  </world>\n'
                '</sdf>\n',
                encoding="utf-8",
            )
            changed: list[str] = []
            result = gazebo_module._ensure_sensors_system_in_world(
                sdf_path, changed, Path(tmp)
            )
            self.assertTrue(result)
            content = sdf_path.read_text(encoding="utf-8")
            self.assertIn("gz-sim-sensors-system", content)
            self.assertIn("gz::sim::systems::Sensors", content)
            self.assertIn("ogre2", content)

    def test_resolve_plugin_from_registry(self) -> None:
        """The plugin registry can resolve known aliases."""
        plugin = gazebo_module._resolve_plugin("diff_drive")
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin["filename"], "gz-sim-diff-drive-system")
        self.assertEqual(plugin["name"], "gz::sim::systems::DiffDrive")
        self.assertEqual(plugin["category"], "model")

    def test_resolve_plugin_unknown_returns_none(self) -> None:
        """Unknown plugin aliases return None."""
        plugin = gazebo_module._resolve_plugin("nonexistent_plugin_xyz")
        self.assertIsNone(plugin)

    def test_list_available_plugins(self) -> None:
        """The plugin list contains model, sensor, and world categories."""
        listing = gazebo_module._list_available_plugins()
        self.assertIn("Model plugins", listing)
        self.assertIn("Sensor plugins", listing)
        self.assertIn("World plugins", listing)
        self.assertIn("diff_drive", listing)
        self.assertIn("imu", listing)
        self.assertIn("physics", listing)


if __name__ == "__main__":
    unittest.main()
