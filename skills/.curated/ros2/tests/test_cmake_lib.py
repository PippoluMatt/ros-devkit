#!/usr/bin/env python3
"""Tests for shared ROS2 CMakeLists.txt transformations."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import cmake_lib.parsing as cmake_p  # noqa: E402
import cmake_lib.transforms as cmake_t  # noqa: E402
import cmake_lib.cli as cmake_cli  # noqa: E402


GENERATED_LINT_BLOCK = """# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()
"""


class CMakeTransformTests(unittest.TestCase):
    def test_remove_default_lint_block_removes_generated_placeholder_and_lint(self) -> None:
        text = (
            "cmake_minimum_required(VERSION 3.8)\n"
            "project(example)\n\n"
            f"{GENERATED_LINT_BLOCK}\n"
            "ament_package()\n"
        )

        result = cmake_t.remove_default_lint_block(text)

        self.assertNotIn("# find_package(<dependency> REQUIRED)", result)
        self.assertNotIn("find_package(ament_lint_auto REQUIRED)", result)
        self.assertIn("ament_package()", result)

    def test_remove_default_lint_block_preserves_custom_testing_block(self) -> None:
        text = (
            "cmake_minimum_required(VERSION 3.8)\n"
            "project(example)\n\n"
            "if(BUILD_TESTING)\n"
            "  find_package(ament_cmake_gtest REQUIRED)\n"
            "  ament_add_gtest(example_test test/example_test.cpp)\n"
            "endif()\n\n"
            "ament_package()\n"
        )

        self.assertEqual(cmake_t.remove_default_lint_block(text), text)

    def test_add_include_directories_after_find_package_block(self) -> None:
        text = (
            "cmake_minimum_required(VERSION 3.8)\n"
            "project(example)\n\n"
            "find_package(ament_cmake REQUIRED)\n"
            "find_package(rclcpp REQUIRED)\n\n"
            "ament_package()\n"
        )

        result = cmake_t.add_include_directories(text)

        self.assertIn("include_directories(include)", result)
        self.assertLess(
            result.index("find_package(rclcpp REQUIRED)"),
            result.index("include_directories(include)"),
        )
        self.assertLess(
            result.index("include_directories(include)"),
            result.index("ament_package()"),
        )
        self.assertEqual(cmake_t.add_include_directories(result), result)

    def test_add_install_share_directories_inserts_and_merges(self) -> None:
        text = "find_package(ament_cmake REQUIRED)\n\nament_package()\n"

        result = cmake_t.add_install_share_directories(text, ["urdf", "meshes"])
        result = cmake_t.add_install_share_directories(result, ["rviz", "urdf"])

        self.assertIn("DIRECTORY urdf meshes rviz", result)
        self.assertEqual(result.count("install("), 1)
        self.assertLess(result.index("install("), result.index("ament_package()"))

    def test_normalize_dir_name_rejects_empty_and_parent_paths(self) -> None:
        self.assertEqual(cmake_t.normalize_dir_name("/urdf/"), "urdf")
        with self.assertRaises(ValueError):
            cmake_t.normalize_dir_name(" ")
        with self.assertRaises(ValueError):
            cmake_t.normalize_dir_name("../outside")
        with self.assertRaises(ValueError):
            cmake_t.normalize_dir_name("urdf/../outside")

    def test_installed_share_directories_extracts_directory_basenames(self) -> None:
        text = (
            "install(\n"
            "  DIRECTORY urdf meshes\n"
            "  DESTINATION share/${PROJECT_NAME}\n"
            ")\n"
        )
        result = cmake_p.installed_share_directories(text)
        self.assertEqual(result, {"urdf", "meshes"})

    def test_installed_share_directories_strips_comments(self) -> None:
        text = (
            "# install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})\n"
            "install(\n"
            "  DIRECTORY urdf  # the urdf dir\n"
            "  DESTINATION share/${PROJECT_NAME}\n"
            ")\n"
        )
        result = cmake_p.installed_share_directories(text)
        self.assertEqual(result, {"urdf"})

    def test_cli_mutates_file_and_prints_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "CMakeLists.txt"
            path.write_text(f"project(example)\n\n{GENERATED_LINT_BLOCK}\nament_package()\n")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = cmake_cli.main(["remove-default-lint-block", str(path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue().strip(), "updated")
            self.assertNotIn("ament_lint_auto", path.read_text())


if __name__ == "__main__":
    unittest.main()