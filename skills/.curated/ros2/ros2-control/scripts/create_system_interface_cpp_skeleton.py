#!/usr/bin/env python3
"""Create an optional minimal SystemInterface .cpp skeleton."""

import argparse
from pathlib import Path


def render(args: argparse.Namespace) -> str:
    return f"""#include "{args.header_include}"

namespace {args.namespace_name}
{{

hardware_interface::CallbackReturn {args.class_name}::on_init(
  const hardware_interface::HardwareInfo & info)
{{
  if (hardware_interface::SystemInterface::on_init(info) !=
    hardware_interface::CallbackReturn::SUCCESS)
  {{
    return hardware_interface::CallbackReturn::ERROR;
  }}

  hw_positions_.assign(info_.joints.size(), 0.0);
  hw_velocities_.assign(info_.joints.size(), 0.0);
  hw_efforts_.assign(info_.joints.size(), 0.0);
  hw_commands_.assign(info_.joints.size(), 0.0);

  return hardware_interface::CallbackReturn::SUCCESS;
}}

hardware_interface::CallbackReturn {args.class_name}::on_configure(
  const rclcpp_lifecycle::State & previous_state)
{{
  (void)previous_state;
  return hardware_interface::CallbackReturn::SUCCESS;
}}

hardware_interface::CallbackReturn {args.class_name}::on_activate(
  const rclcpp_lifecycle::State & previous_state)
{{
  (void)previous_state;
  return hardware_interface::CallbackReturn::SUCCESS;
}}

hardware_interface::CallbackReturn {args.class_name}::on_deactivate(
  const rclcpp_lifecycle::State & previous_state)
{{
  (void)previous_state;
  return hardware_interface::CallbackReturn::SUCCESS;
}}

hardware_interface::return_type {args.class_name}::read(
  const rclcpp::Time & time, const rclcpp::Duration & period)
{{
  (void)time;
  (void)period;
  return hardware_interface::return_type::OK;
}}

hardware_interface::return_type {args.class_name}::write(
  const rclcpp::Time & time, const rclcpp::Duration & period)
{{
  (void)time;
  (void)period;
  return hardware_interface::return_type::OK;
}}

}}  // namespace {args.namespace_name}
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--header-include", required=True)
    parser.add_argument("--namespace-name", required=True)
    parser.add_argument("--class-name", default="MyRobotHardwareInterface")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    if output.exists() and not args.force:
        raise SystemExit(f"{output} already exists; pass --force to overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(args), encoding="utf-8")


if __name__ == "__main__":
    main()
