"""Create and repair ROS2 description packages."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

from cmake_lib.transforms import add_install_share_directories, remove_default_lint_block
from package_xml_lib.parsing import read_package_name, robot_name_from_package

from .templates import (
    MATERIALS_XACRO,
    RVIZ_CONFIG,
    URDF_XACRO,
    cmakelists,
    main_xacro,
    package_xml,
    sensor_xacro,
)


def edit_cmake(cmake_path: Path) -> None:
    """Remove generated lint boilerplate and add install directives."""
    content = cmake_path.read_text(encoding="utf-8")
    content = remove_default_lint_block(content)
    content = add_install_share_directories(content, ["urdf", "meshes", "rviz"])
    cmake_path.write_text(content, encoding="utf-8")


def _write_missing(pkg_dir: Path, rel_path: str, content: str, created: list[str]) -> None:
    path = pkg_dir / rel_path
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(rel_path)


def _repair_package(pkg_dir: Path, sensors: list[str]) -> int:
    pkg_dir = pkg_dir.resolve()
    if not pkg_dir.exists():
        print(f"ERROR: Package directory does not exist: {pkg_dir}")
        return 1
    if not pkg_dir.is_dir():
        print(f"ERROR: Not a directory: {pkg_dir}")
        return 1

    pkg_name = read_package_name(pkg_dir / "package.xml")
    robot_name = robot_name_from_package(pkg_name)
    created: list[str] = []

    for rel_dir in ["urdf", "meshes", "rviz"]:
        path = pkg_dir / rel_dir
        if not path.exists():
            path.mkdir(parents=True)
            created.append(f"{rel_dir}/")

    _write_missing(pkg_dir, "CMakeLists.txt", cmakelists(pkg_name), created)
    _write_missing(pkg_dir, "package.xml", package_xml(pkg_name, robot_name), created)

    if not (pkg_dir / "urdf" / "main.xacro").exists() and not (
        pkg_dir / "urdf" / "main.urdf.xacro"
    ).exists():
        _write_missing(pkg_dir, "urdf/main.xacro", main_xacro(robot_name, sensors), created)

    _write_missing(
        pkg_dir,
        "urdf/materials.xacro",
        MATERIALS_XACRO.format(name=robot_name),
        created,
    )
    _write_missing(
        pkg_dir,
        f"urdf/{robot_name}.urdf.xacro",
        URDF_XACRO.format(name=robot_name),
        created,
    )
    for sensor in sensors:
        _write_missing(
            pkg_dir,
            f"urdf/{sensor}.xacro",
            sensor_xacro(robot_name, sensor),
            created,
        )
    _write_missing(pkg_dir, f"rviz/{robot_name}.rviz", RVIZ_CONFIG, created)

    print(f"Package : {pkg_name}")
    print(f"Path    : {pkg_dir}")
    if created:
        print(f"Created : {', '.join(created)}")
    else:
        print("INFO: No missing minimal files or directories found")
    print(f"Verify  : ros-devkit description-scaffold --verify {pkg_dir}")
    return 0


def scaffold(
    name: str,
    sensors: list[str],
    destination: Path,
    maintainer: str | None,
    email: str | None,
    license_type: str | None,
) -> None:
    """Create the full package structure using ros2 pkg create."""
    pkg_name = f"{name}_description"

    if not shutil.which("ros2"):
        print("ERROR: 'ros2' command not found. Source ROS 2 first.")
        sys.exit(1)

    pkg_dir = destination / pkg_name
    if pkg_dir.exists():
        print(f"ERROR: Package directory already exists: {pkg_dir}")
        sys.exit(1)

    destination.mkdir(parents=True, exist_ok=True)

    cmd: list[str] = [
        "ros2",
        "pkg",
        "create",
        pkg_name,
        "--build-type",
        "ament_cmake",
        "--dependencies",
        "urdf",
        "xacro",
        "--description",
        f"URDF/xacro description package for {name}",
        "--destination-directory",
        str(destination),
    ]
    if maintainer:
        cmd.extend(["--maintainer-name", maintainer])
    if email:
        cmd.extend(["--maintainer-email", email])
    if license_type:
        cmd.extend(["--license", license_type])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR: ros2 pkg create failed:")
        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)
        sys.exit(1)

    created: list[str] = []
    removed: list[str] = []

    for directory in ["src", "include"]:
        path = pkg_dir / directory
        if path.exists():
            shutil.rmtree(path)
            removed.append(directory)

    edit_cmake(pkg_dir / "CMakeLists.txt")

    for directory in ["meshes", "rviz", "urdf"]:
        (pkg_dir / directory).mkdir(exist_ok=True)

    def write_new(rel_path: str, content: str) -> None:
        path = pkg_dir / rel_path
        if path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created.append(rel_path)

    write_new("urdf/main.xacro", main_xacro(name, sensors))
    write_new("urdf/materials.xacro", MATERIALS_XACRO.format(name=name))
    write_new(f"urdf/{name}.urdf.xacro", URDF_XACRO.format(name=name))
    for sensor in sensors:
        write_new(f"urdf/{sensor}.xacro", sensor_xacro(name, sensor))
    write_new(f"rviz/{name}.rviz", RVIZ_CONFIG)

    print(f"\nPackage : {pkg_name}")
    print(f"Path    : {pkg_dir}")
    print(f"Sensors : {', '.join(sensors) if sensors else 'none'}")
    if removed:
        print(f"Removed : {', '.join(directory + '/' for directory in removed)}")
    print("Modified: CMakeLists.txt (removed BUILD_TESTING, added install)")
    if created:
        print(f"Created : {', '.join(created)}")
    print("\nNext steps:")
    print(f"  1. Customize links/joints in urdf/{name}.urdf.xacro")
    print("  2. Adjust sensor positions and enable Gazebo plugins")
    print("  3. Update license in package.xml")
    print(f"  4. Validate: ros-devkit description-scaffold --verify {pkg_dir}")
