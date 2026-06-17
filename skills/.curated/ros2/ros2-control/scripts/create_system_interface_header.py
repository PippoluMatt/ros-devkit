#!/usr/bin/env python3
"""Create a ROS2 Jazzy hardware_interface::SystemInterface header."""

import argparse
from pathlib import Path


def guard_from_path(path: Path) -> str:
    stem = path.stem.upper()
    return f"{stem}_HPP"


def include_line(raw: str) -> str:
    if raw.startswith("<") or raw.startswith('"'):
        return f"#include {raw}"
    return f'#include "{raw}"'


def render(args: argparse.Namespace) -> str:
    guard = args.include_guard or guard_from_path(Path(args.output))
    driver_include = f"{include_line(args.driver_include)}\n" if args.driver_include else ""
    return f"""#ifndef {guard}
#define {guard}

#include <vector>

#include "hardware_interface/handle.hpp"
#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
{driver_include}#include "rclcpp/duration.hpp"
#include "rclcpp/macros.hpp"
#include "rclcpp/time.hpp"
#include "rclcpp_lifecycle/state.hpp"

namespace {args.namespace_name}
{{

class {args.class_name} : public hardware_interface::SystemInterface
{{
public:
  RCLCPP_SHARED_PTR_DEFINITIONS({args.class_name})

  hardware_interface::CallbackReturn on_init(
    const hardware_interface::HardwareInfo & info) override;

  hardware_interface::CallbackReturn on_configure(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_activate(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_deactivate(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::return_type read(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

  hardware_interface::return_type write(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

private:
  std::vector<double> hw_positions_;
  std::vector<double> hw_velocities_;
  std::vector<double> hw_efforts_;
  std::vector<double> hw_commands_;

  // Add driver-specific members here.
}};

}}  // namespace {args.namespace_name}

#endif  // {guard}
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--namespace-name")
    parser.add_argument("--class-name", default="MyRobotHardwareInterface")
    parser.add_argument("--driver-include")
    parser.add_argument("--include-guard")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    args.namespace_name = args.namespace_name or args.package_name

    output = Path(args.output)
    if output.exists() and not args.force:
        raise SystemExit(f"{output} already exists; pass --force to overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(args), encoding="utf-8")


if __name__ == "__main__":
    main()
