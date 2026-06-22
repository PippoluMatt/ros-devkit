from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO_ROOT
    / "skills"
    / ".curated"
    / "ros2"
    / "ros2-control-pluginize"
    / "scripts"
    / "ros2_control_pluginize.py"
)


class Ros2ControlPluginizeCheckTest(unittest.TestCase):
    def test_dev_runner_doctor_reports_registered_command(self) -> None:
        completed = subprocess.run(
            [str(REPO_ROOT / "scripts" / "dev_ros_devkit.sh"), "doctor"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("ros2-control-pluginize: OK", completed.stdout)

    def test_valid_hardware_package_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            pkg = Path(root) / "demo_hardware"
            self._write_hardware_package(pkg)

            completed = self._run_check(pkg)

            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            self.assertIn("ROS2 Control Pluginize Diagnostics", completed.stdout)
            self.assertIn("Package    : demo_hardware", completed.stdout)
            self.assertIn("Branch     : hardware", completed.stdout)
            self.assertIn("Plugin XML : demo_hardware.xml", completed.stdout)
            self.assertIn("Library    : demo_hardware_interface", completed.stdout)
            self.assertIn("INFO: [demo_hardware:package.xml] package.xml depends on hardware_interface", completed.stdout)
            self.assertIn("INFO: No errors found", completed.stdout)

    def test_valid_chainable_controller_package_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            pkg = Path(root) / "demo_controllers"
            self._write_controller_package(
                pkg,
                base="controller_interface::ChainableControllerInterface",
            )

            completed = self._run_check(pkg)

            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            self.assertIn("Branch     : controllers", completed.stdout)
            self.assertIn("INFO: [demo_controllers:demo_controllers.xml]", completed.stdout)
            self.assertIn("INFO: No errors found", completed.stdout)

    def test_non_chainable_controller_warns_but_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            pkg = Path(root) / "demo_controllers"
            self._write_controller_package(
                pkg,
                base="controller_interface::ControllerInterface",
            )

            completed = self._run_check(pkg)

            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            self.assertIn("WARN: [demo_controllers:demo_controllers.xml]", completed.stdout)
            self.assertIn("ControllerInterface, not chainable", completed.stdout)
            self.assertIn("INFO: No errors found", completed.stdout)

    def test_common_cmake_dependency_styles_are_accepted(self) -> None:
        cases = [
            ("ament", False),
            ("mixed", True),
            ("this_package_include_depends", False),
        ]
        for dependency_style, has_warning in cases:
            with self.subTest(dependency_style=dependency_style):
                with tempfile.TemporaryDirectory() as root:
                    pkg = Path(root) / "demo_hardware"
                    self._write_hardware_package(pkg, cmake_dependency_style=dependency_style)

                    completed = self._run_check(pkg)

                    self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
                    self.assertIn("INFO: No errors found", completed.stdout)
                    if has_warning:
                        self.assertIn("WARN: [demo_hardware:CMakeLists.txt]", completed.stdout)
                        self.assertIn("mixes target_link_libraries and ament_target_dependencies", completed.stdout)
                    else:
                        self.assertNotIn("WARN:", completed.stdout)

    def test_missing_pluginization_pieces_exit_one(self) -> None:
        cases = [
            ("missing xml", {"include_xml": False}, "missing plugin XML"),
            ("missing export", {"include_export": False}, "missing PLUGINLIB_EXPORT_CLASS"),
            (
                "missing pluginlib include",
                {"include_pluginlib_header": False},
                "missing include for pluginlib/class_list_macros.hpp",
            ),
            (
                "export inside namespace",
                {"export_inside_namespace": True},
                "inside a namespace",
            ),
            ("missing dependencies", {"include_package_dependencies": False}, "package.xml missing dependency"),
            (
                "missing cmake export",
                {"include_cmake_plugin_export": False},
                "missing pluginlib_export_plugin_description_file",
            ),
        ]
        for label, options, expected in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as root:
                    pkg = Path(root) / "demo_hardware"
                    self._write_hardware_package(pkg, **options)

                    completed = self._run_check(pkg)

                    self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
                    self.assertIn("ERROR:", completed.stdout)
                    self.assertIn("ERROR: Errors found; fix before proceeding", completed.stdout)
                    self.assertIn(expected, completed.stdout)

    def test_xml_export_base_mismatch_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            pkg = Path(root) / "demo_hardware"
            self._write_hardware_package(
                pkg,
                export_base="controller_interface::ControllerInterface",
            )

            completed = self._run_check(pkg)

            self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
            self.assertIn("export base controller_interface::ControllerInterface", completed.stdout)
            self.assertIn("does not match XML base hardware_interface::SystemInterface", completed.stdout)

    def test_multiple_inferred_candidates_without_xml_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            pkg = Path(root) / "demo_hardware"
            self._write_hardware_package(
                pkg,
                include_xml=False,
                include_cmake_plugin_export=False,
                extra_candidate=True,
            )

            completed = self._run_check(pkg)

            self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
            self.assertIn("multiple C++ plugin candidates", completed.stdout)

    def test_unsupported_package_suffix_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            pkg = Path(root) / "demo_control"
            self._write_hardware_package(pkg, package_name="demo_control")

            completed = self._run_check(pkg)

            self.assertEqual(2, completed.returncode, completed.stdout + completed.stderr)
            self.assertIn("Unsupported package suffix", completed.stderr)

    def _run_check(self, pkg: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--check", str(pkg)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def _write_hardware_package(
        self,
        pkg: Path,
        package_name: str = "demo_hardware",
        include_xml: bool = True,
        include_export: bool = True,
        include_package_dependencies: bool = True,
        include_cmake_plugin_export: bool = True,
        include_pluginlib_header: bool = True,
        export_inside_namespace: bool = False,
        export_base: str = "hardware_interface::SystemInterface",
        extra_candidate: bool = False,
        cmake_dependency_style: str = "target",
    ) -> None:
        self._write_package(
            pkg=pkg,
            package_name=package_name,
            library_target="demo_hardware_interface",
            interface_package="hardware_interface",
            class_name="DemoHardware",
            namespace="demo_hardware",
            base="hardware_interface::SystemInterface",
            include_xml=include_xml,
            include_export=include_export,
            include_package_dependencies=include_package_dependencies,
            include_cmake_plugin_export=include_cmake_plugin_export,
            include_pluginlib_header=include_pluginlib_header,
            export_inside_namespace=export_inside_namespace,
            export_base=export_base,
            extra_candidate=extra_candidate,
            cmake_dependency_style=cmake_dependency_style,
        )

    def _write_controller_package(self, pkg: Path, base: str) -> None:
        self._write_package(
            pkg=pkg,
            package_name="demo_controllers",
            library_target="demo_controllers",
            interface_package="controller_interface",
            class_name="DemoController",
            namespace="demo_controllers",
            base=base,
            include_xml=True,
            include_export=True,
            include_package_dependencies=True,
            include_cmake_plugin_export=True,
            include_pluginlib_header=True,
            export_inside_namespace=False,
            export_base=base,
            extra_candidate=False,
            cmake_dependency_style="target",
        )

    def _write_package(
        self,
        pkg: Path,
        package_name: str,
        library_target: str,
        interface_package: str,
        class_name: str,
        namespace: str,
        base: str,
        include_xml: bool,
        include_export: bool,
        include_package_dependencies: bool,
        include_cmake_plugin_export: bool,
        include_pluginlib_header: bool,
        export_inside_namespace: bool,
        export_base: str,
        extra_candidate: bool,
        cmake_dependency_style: str,
    ) -> None:
        (pkg / "src").mkdir(parents=True)
        dependency_tags = (
            textwrap.dedent(
                f"""\
                  <depend>{interface_package}</depend>
                  <depend>pluginlib</depend>
                """
            )
            if include_package_dependencies
            else ""
        )
        package_xml = textwrap.dedent(
            f"""\
            <?xml version="1.0"?>
            <package format="3">
              <name>{package_name}</name>
              <version>0.0.0</version>
              <description>Demo package</description>
              <maintainer email="dev@example.com">Dev</maintainer>
              <license>MIT</license>
              <buildtool_depend>ament_cmake</buildtool_depend>
            {dependency_tags.rstrip()}
              <export>
                <build_type>ament_cmake</build_type>
              </export>
            </package>
            """
        ).lstrip()
        (pkg / "package.xml").write_text(package_xml, encoding="utf-8")
        plugin_export = (
            textwrap.dedent(
                f"""\
                pluginlib_export_plugin_description_file(
                  {interface_package} {package_name}.xml
                )
                """
            )
            if include_cmake_plugin_export
            else ""
        )
        if cmake_dependency_style == "target":
            find_packages = f"find_package({interface_package} REQUIRED)\nfind_package(pluginlib REQUIRED)"
            target_dependencies = textwrap.dedent(
                f"""\
                target_link_libraries({library_target} PUBLIC
                  {interface_package}::{interface_package}
                  pluginlib::pluginlib
                )
                """
            )
            export_dependencies = f"ament_export_dependencies({interface_package} pluginlib)"
        elif cmake_dependency_style == "ament":
            find_packages = f"find_package({interface_package} REQUIRED)\nfind_package(pluginlib REQUIRED)"
            target_dependencies = f"ament_target_dependencies({library_target} {interface_package} pluginlib)"
            export_dependencies = f"ament_export_dependencies({interface_package} pluginlib)"
        elif cmake_dependency_style == "mixed":
            find_packages = f"find_package({interface_package} REQUIRED)\nfind_package(pluginlib REQUIRED)"
            target_dependencies = textwrap.dedent(
                f"""\
                target_link_libraries({library_target} PUBLIC
                  {interface_package}::{interface_package}
                )
                ament_target_dependencies({library_target} pluginlib)
                """
            )
            export_dependencies = f"ament_export_dependencies({interface_package} pluginlib)"
        elif cmake_dependency_style == "this_package_include_depends":
            find_packages = textwrap.dedent(
                f"""\
                set(THIS_PACKAGE_INCLUDE_DEPENDS {interface_package} pluginlib)
                foreach(Dependency IN ITEMS ${{THIS_PACKAGE_INCLUDE_DEPENDS}})
                  find_package(${{Dependency}} REQUIRED)
                endforeach()
                """
            ).rstrip()
            target_dependencies = f"ament_target_dependencies({library_target} ${{THIS_PACKAGE_INCLUDE_DEPENDS}})"
            export_dependencies = "ament_export_dependencies(${THIS_PACKAGE_INCLUDE_DEPENDS})"
        else:
            raise AssertionError(f"unknown CMake dependency style: {cmake_dependency_style}")
        (pkg / "CMakeLists.txt").write_text(
            textwrap.dedent(
                f"""\
                cmake_minimum_required(VERSION 3.8)
                project({package_name})

                find_package(ament_cmake REQUIRED)
                {find_packages}

                add_library({library_target} SHARED
                  src/plugin.cpp
                )
                {target_dependencies.rstrip()}
                {plugin_export.rstrip()}
                install(
                  TARGETS {library_target}
                  EXPORT export_{library_target}
                  RUNTIME DESTINATION bin
                  ARCHIVE DESTINATION lib
                  LIBRARY DESTINATION lib
                )
                ament_export_targets(export_{library_target} HAS_LIBRARY_TARGET)
                {export_dependencies}
                ament_package()
                """
            ),
            encoding="utf-8",
        )
        if include_xml:
            plugin_xml = textwrap.dedent(
                f"""\
                <?xml version="1.0"?>
                <library path="{library_target}">
                  <class name="{package_name}/{class_name}"
                         type="{namespace}::{class_name}"
                         base_class_type="{base}">
                    <description>Demo plugin.</description>
                  </class>
                </library>
                """
            ).lstrip()
            (pkg / f"{package_name}.xml").write_text(plugin_xml, encoding="utf-8")

        second_class = ""
        if extra_candidate:
            second_class = textwrap.dedent(
                f"""\

                class OtherPlugin : public {base}
                {{
                }};
                """
            )
        export_macro = (
            textwrap.dedent(
                f"""\

                PLUGINLIB_EXPORT_CLASS(
                  {namespace}::{class_name},
                  {export_base})
                """
            )
            if include_export
            else ""
        )
        inside_export_macro = export_macro if export_inside_namespace else ""
        outside_export_macro = "" if export_inside_namespace else export_macro
        include_line = '#include "pluginlib/class_list_macros.hpp"' if include_pluginlib_header else ""
        (pkg / "src" / "plugin.cpp").write_text(
            textwrap.dedent(
                f"""\
                {include_line}

                namespace {namespace}
                {{

                class {class_name} : public {base}
                {{
                }};
                {second_class.rstrip()}
                {inside_export_macro.rstrip()}

                }}  // namespace {namespace}
                {outside_export_macro.rstrip()}
                """
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
