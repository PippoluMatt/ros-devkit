#!/usr/bin/env python3
"""Add common ROS2 control SystemInterface CMake wiring."""

import argparse
from pathlib import Path


DEPS = ["hardware_interface", "pluginlib", "rclcpp", "rclcpp_lifecycle"]


def insert_before_ament_package(text: str, block: str) -> str:
    marker = "ament_package()"
    if marker in text:
        return text.replace(marker, block.rstrip() + "\n\n" + marker, 1)
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def ensure_find_packages(text: str) -> str:
    missing = [dep for dep in DEPS if f"find_package({dep} REQUIRED)" not in text]
    if not missing:
        return text
    lines = text.splitlines()
    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith("project(") or line.startswith("find_package("):
            insert_at = index + 1
    package_lines = [f"find_package({dep} REQUIRED)" for dep in missing]
    lines[insert_at:insert_at] = package_lines
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cmakelists")
    parser.add_argument("--target", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--plugin-xml", required=True)
    args = parser.parse_args()

    path = Path(args.cmakelists)
    text = path.read_text(encoding="utf-8")
    text = ensure_find_packages(text)

    block = f"""
add_library({args.target} SHARED
  {args.source}
)
target_include_directories({args.target} PUBLIC
  $<BUILD_INTERFACE:${{CMAKE_CURRENT_SOURCE_DIR}}/include>
  $<INSTALL_INTERFACE:include>
)
ament_target_dependencies({args.target}
  hardware_interface
  pluginlib
  rclcpp
  rclcpp_lifecycle
)
pluginlib_export_plugin_description_file(
  hardware_interface {args.plugin_xml})
install(DIRECTORY include/ DESTINATION include)
install(TARGETS {args.target}
  EXPORT export_${{PROJECT_NAME}}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
ament_export_targets(export_${{PROJECT_NAME}} HAS_LIBRARY_TARGET)
ament_export_dependencies(
  hardware_interface
  pluginlib
  rclcpp
  rclcpp_lifecycle
)
"""
    if f"add_library({args.target}" not in text:
        text = insert_before_ament_package(text, block)
    if f"pluginlib_export_plugin_description_file(\n  hardware_interface {args.plugin_xml})" not in text:
        raise SystemExit("CMake target exists; inspect manually before adding plugin export wiring")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
