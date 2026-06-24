#!/usr/bin/env python3
"""Tests for shared package.xml parsing and mutation helpers."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import package_xml_lib.cli as pkg_cli  # noqa: E402
from package_xml_lib.parsing import (  # noqa: E402
    read_dependencies,
    read_package_name,
    robot_name_from_package,
)
from package_xml_lib.transforms import (  # noqa: E402
    ensure_dependencies,
    ensure_exec_depends,
)


PACKAGE_XML_TEMPLATE = """<?xml version="1.0"?>
<package format="3">
  <name>{name}</name>
  <version>0.0.0</version>
  <description>Test package</description>
  <maintainer email="test@test.com">Test</maintainer>
  <license>MIT</license>

  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend>
  <exec_depend>launch_ros</exec_depend>
  <build_depend>urdf</build_depend>
  <test_depend>ament_lint_auto</test_depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
"""


class ReadPackageNameTests(unittest.TestCase):
    def test_reads_name_from_package_xml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "my_pkg" / "package.xml"
            path.parent.mkdir()
            path.write_text(PACKAGE_XML_TEMPLATE.format(name="my_robot_description"))
            self.assertEqual(read_package_name(path), "my_robot_description")

    def test_falls_back_to_directory_name_on_missing_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fallback_pkg" / "package.xml"
            path.parent.mkdir()
            path.write_text(
                '<?xml version="1.0"?>\n<package format="3">\n'
                "  <version>0.0.0</version>\n</package>\n"
            )
            self.assertEqual(read_package_name(path), "fallback_pkg")

    def test_falls_back_to_directory_name_on_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken_pkg" / "package.xml"
            path.parent.mkdir()
            path.write_text("not valid xml <<")
            self.assertEqual(read_package_name(path), "broken_pkg")

    def test_falls_back_to_directory_name_on_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ghost_pkg" / "package.xml"
            self.assertEqual(read_package_name(path), "ghost_pkg")


class ReadDependenciesTests(unittest.TestCase):
    def test_returns_all_declared_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.xml"
            path.write_text(PACKAGE_XML_TEMPLATE.format(name="test_pkg"))
            deps = read_dependencies(path)
            self.assertEqual(
                deps,
                {"ament_cmake", "rclcpp", "launch_ros", "urdf", "ament_lint_auto"},
            )

    def test_raises_on_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.xml"
            path.write_text("not xml <")
            with self.assertRaises(ValueError):
                read_dependencies(path)

    def test_returns_empty_set_when_no_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.xml"
            path.write_text(
                '<?xml version="1.0"?>\n<package format="3">\n'
                "  <name>empty</name>\n</package>\n"
            )
            self.assertEqual(read_dependencies(path), set())


class RobotNameFromPackageTests(unittest.TestCase):
    def test_strips_description_suffix_by_default(self) -> None:
        self.assertEqual(robot_name_from_package("my_robot_description"), "my_robot")

    def test_strips_bringup_suffix_by_default(self) -> None:
        self.assertEqual(robot_name_from_package("my_robot_bringup"), "my_robot")

    def test_strips_hardware_suffix_by_default(self) -> None:
        self.assertEqual(robot_name_from_package("my_robot_hardware"), "my_robot")

    def test_strips_controllers_suffix_by_default(self) -> None:
        self.assertEqual(robot_name_from_package("my_robot_controllers"), "my_robot")

    def test_returns_unchanged_when_no_known_suffix(self) -> None:
        self.assertEqual(robot_name_from_package("my_robot"), "my_robot")

    def test_explicit_suffix_strips_only_that_suffix(self) -> None:
        self.assertEqual(
            robot_name_from_package("my_robot_bringup", suffix="_description"),
            "my_robot_bringup",
        )
        self.assertEqual(
            robot_name_from_package("my_robot_description", suffix="_description"),
            "my_robot",
        )

    def test_custom_suffix(self) -> None:
        self.assertEqual(robot_name_from_package("my_robot_gazebo", suffix="_gazebo"), "my_robot")


class EnsureDependenciesTests(unittest.TestCase):
    def _write_package_xml(self, path: Path, name: str = "test_pkg", deps: list[str] | None = None) -> None:
        dep_tags = "".join(f"  <depend>{d}</depend>\n" for d in (deps or []))
        path.write_text(
            f"""<?xml version="1.0"?>
<package format="3">
  <name>{name}</name>
  <version>0.0.0</version>
  <description>Test</description>
  <maintainer email="t@t.com">T</maintainer>
  <license>MIT</license>

  <buildtool_depend>ament_cmake</buildtool_depend>
{dep_tags}
  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
"""
        )

    def test_inserts_missing_deps_before_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.xml"
            self._write_package_xml(path, deps=["rclcpp"])
            changed = ensure_dependencies(path, ["rclcpp", "pluginlib", "hardware_interface"])
            self.assertTrue(changed)
            content = path.read_text()
            self.assertIn("<depend>pluginlib</depend>", content)
            self.assertIn("<depend>hardware_interface</depend>", content)
            # rclcpp was already present and must not be duplicated
            self.assertEqual(content.count("<depend>rclcpp</depend>"), 1)

    def test_inserts_before_closing_package_when_no_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.xml"
            path.write_text(
                '<?xml version="1.0"?>\n<package format="3">\n'
                "  <name>test</name>\n"
                "  <depend>rclcpp</depend>\n"
                "</package>\n"
            )
            changed = ensure_dependencies(path, ["pluginlib"])
            self.assertTrue(changed)
            content = path.read_text()
            self.assertIn("<depend>pluginlib</depend>", content)
            self.assertLess(content.index("<depend>pluginlib</depend>"), content.index("</package>"))

    def test_no_change_when_all_deps_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.xml"
            self._write_package_xml(path, deps=["rclcpp", "pluginlib"])
            changed = ensure_dependencies(path, ["rclcpp", "pluginlib"])
            self.assertFalse(changed)

    def test_appends_to_changed_list_with_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg_dir = Path(tmp)
            path = pkg_dir / "package.xml"
            self._write_package_xml(path, deps=["rclcpp"])
            changed: list[str] = []
            ensure_dependencies(path, ["pluginlib"], pkg_dir=pkg_dir, changed=changed)
            self.assertEqual(len(changed), 1)
            self.assertTrue(changed[0].startswith("Updated: "))
            self.assertIn("package.xml", changed[0])

    def test_exec_depends_uses_exec_depend_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.xml"
            self._write_package_xml(path, deps=["rclcpp"])
            changed = ensure_exec_depends(path, ["ros_gz_sim", "ros_gz_bridge"])
            self.assertTrue(changed)
            content = path.read_text()
            self.assertIn("<exec_depend>ros_gz_sim</exec_depend>", content)
            self.assertIn("<exec_depend>ros_gz_bridge</exec_depend>", content)

    def test_does_not_duplicate_dep_already_in_other_depend_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.xml"
            path.write_text(
                '<?xml version="1.0"?>\n<package format="3">\n'
                "  <name>test</name>\n"
                "  <exec_depend>rclcpp</exec_depend>\n"
                "  <export>\n    <build_type>ament_cmake</build_type>\n  </export>\n"
                "</package>\n"
            )
            changed = ensure_dependencies(path, ["rclcpp"], tag="depend")
            self.assertFalse(changed)


class CLITests(unittest.TestCase):
    def test_read_name_prints_package_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "my_pkg" / "package.xml"
            path.parent.mkdir()
            path.write_text(PACKAGE_XML_TEMPLATE.format(name="cli_test_pkg"))
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = pkg_cli.main(["read-name", str(path)])
            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue().strip(), "cli_test_pkg")

    def test_ensure_depends_prints_updated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.xml"
            path.write_text(
                '<?xml version="1.0"?>\n<package format="3">\n'
                "  <name>test</name>\n"
                "  <depend>rclcpp</depend>\n"
                "</package>\n"
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = pkg_cli.main(["ensure-depends", str(path), "pluginlib"])
            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue().strip(), "updated")
            self.assertIn("<depend>pluginlib</depend>", path.read_text())

    def test_ensure_depends_prints_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.xml"
            path.write_text(
                '<?xml version="1.0"?>\n<package format="3">\n'
                "  <name>test</name>\n"
                "  <depend>rclcpp</depend>\n"
                "  <depend>pluginlib</depend>\n"
                "</package>\n"
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = pkg_cli.main(["ensure-depends", str(path), "pluginlib"])
            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue().strip(), "unchanged")

    def test_ensure_exec_depends_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.xml"
            path.write_text(
                '<?xml version="1.0"?>\n<package format="3">\n'
                "  <name>test</name>\n"
                "  <depend>rclcpp</depend>\n"
                "</package>\n"
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = pkg_cli.main(["ensure-exec-depends", str(path), "ros_gz_sim"])
            self.assertEqual(exit_code, 0)
            self.assertIn("<exec_depend>ros_gz_sim</exec_depend>", path.read_text())


if __name__ == "__main__":
    unittest.main()