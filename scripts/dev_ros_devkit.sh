#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "update" ]]; then
  printf '%s\n' "ERROR: update is disabled for the local checkout runner. Use the installer-managed ros-devkit command for updates." >&2
  exit 1
fi

export ROS_DEVKIT_AGENT="${ROS_DEVKIT_AGENT:-custom}"
export ROS_DEVKIT_SKILL_ROOT="${ROS_DEVKIT_SKILL_ROOT:-$repo_root/skills/.curated/ros2}"
export PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}"

exec "${ROS_DEVKIT_DEV_PYTHON:-python3}" -m ros_devkit.cli "$@"
