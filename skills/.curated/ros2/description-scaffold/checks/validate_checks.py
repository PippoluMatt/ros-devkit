from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path


VALIDATE_PATH = Path(__file__).resolve().parents[1] / "scripts/validate.py"

spec = importlib.util.spec_from_file_location(
    "description_scaffold_validate", VALIDATE_PATH
)
assert spec is not None
validate_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = validate_module
spec.loader.exec_module(validate_module)


class DescriptionScaffoldValidateChecks(unittest.TestCase):
    def test_missing_entrypoint_warns_about_extra_xacro_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg_dir = Path(tmp) / "my_robot_description"
            self._write_package(pkg_dir)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                valid = validate_module.validate(pkg_dir)

            self.assertFalse(valid)
            self.assertIn(
                "WARN: Entry point missing; cannot verify standard includes for "
                "extra xacro files: urdf/base.xacro, urdf/common.xacro, "
                "urdf/wheels.xacro",
                output.getvalue(),
            )

    def test_format_severity_uses_requested_colors(self) -> None:
        self.assertEqual(
            validate_module._format_severity("ERROR", color=True),
            "\033[31mERROR\033[0m",
        )
        self.assertEqual(
            validate_module._format_severity("WARN", color=True),
            "\033[33mWARN\033[0m",
        )
        self.assertEqual(
            validate_module._format_severity("INFO", color=True),
            "\033[32mINFO\033[0m",
        )
        self.assertEqual(
            validate_module._format_severity("ERROR", color=False),
            "ERROR",
        )

    def _write_package(self, pkg_dir: Path) -> None:
        (pkg_dir / "urdf").mkdir(parents=True)
        (pkg_dir / "meshes").mkdir()
        (pkg_dir / "rviz").mkdir()
        (pkg_dir / "rviz/display.rviz").write_text("", encoding="utf-8")
        (pkg_dir / "CMakeLists.txt").write_text(
            """cmake_minimum_required(VERSION 3.8)
project(my_robot_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY urdf meshes rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
""",
            encoding="utf-8",
        )
        (pkg_dir / "package.xml").write_text(
            """<?xml version="1.0"?>
<package format="3">
  <name>my_robot_description</name>
  <version>0.0.0</version>
  <description>Test package</description>
  <maintainer email="user@example.com">TODO</maintainer>
  <license>TODO</license>
  <depend>urdf</depend>
  <depend>xacro</depend>
</package>
""",
            encoding="utf-8",
        )
        for name in [
            "base.xacro",
            "common.xacro",
            "materials.xacro",
            "my_robot.urdf.xacro",
            "wheels.xacro",
        ]:
            (pkg_dir / "urdf" / name).write_text(
                '<?xml version="1.0"?>'
                '<robot xmlns:xacro="http://www.ros.org/wiki/xacro"/>',
                encoding="utf-8",
            )


if __name__ == "__main__":
    unittest.main()
