#!/usr/bin/env python3
"""Render the ROS 2 Dockerfile and .dockerignore templates into the current directory.

The templates under assets/ carry inline ARG defaults (e.g. `ARG ROS_DISTRO=jazzy`).
This script is the single place that knows those defaults, so SKILL.md and the
template do not drift. CLI flags override the defaults at render time.

Usage:
    scripts/render_dockerfile.py [--ros-distro jazzy] [--overlay-ws /opt/ros/overlay_ws]
                                 [--from-image osrf/ros:jazzy-ros-base]
                                 [--target-dir .]

Writes:
    <target-dir>/Dockerfile
    <target-dir>/.dockerignore
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

DEFAULTS = {
    "ros_distro": "jazzy",
    "overlay_ws": "/opt/ros/overlay_ws",
    "from_image": None,  # composed from ros_distro below if not overridden
}

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_ROOT / "assets"


def render_from_image(ros_distro: str, override: str | None) -> str:
    if override:
        return override
    return f"osrf/ros:{ros_distro}-ros-base"


def substitute_defaults(text: str, ros_distro: str, overlay_ws: str, from_image: str) -> str:
    # Defaults are already in the template; we rewrite the three header
    # comment lines and the ARG defaults that mention them so a user reading
    # the rendered Dockerfile sees the values they actually invoked.
    text = text.replace(
        "  --build-arg ROS_DISTRO=jazzy",
        f"  --build-arg ROS_DISTRO={ros_distro}",
    )
    text = text.replace(
        "  --build-arg FROM_IMAGE=osrf/ros:${ROS_DISTRO:-jazzy}-ros-base",
        f"  --build-arg FROM_IMAGE={from_image}",
    )
    text = text.replace(
        "  --build-arg OVERLAY_WS=/opt/ros/overlay_ws",
        f"  --build-arg OVERLAY_WS={overlay_ws}",
    )
    # Also rewrite the inline ARG defaults that drive the FROM resolution.
    text = text.replace(
        "ARG FROM_IMAGE=osrf/ros:${ROS_DISTRO:-jazzy}-ros-base",
        f"ARG FROM_IMAGE={from_image}",
    )
    text = text.replace("ARG ROS_DISTRO=jazzy", f"ARG ROS_DISTRO={ros_distro}")
    text = text.replace("ARG OVERLAY_WS=/opt/ros/overlay_ws", f"ARG OVERLAY_WS={overlay_ws}")
    return text


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ros-distro", default=DEFAULTS["ros_distro"],
                   help=f"ROS 2 distro codename (default: {DEFAULTS['ros_distro']}).")
    p.add_argument("--overlay-ws", default=DEFAULTS["overlay_ws"],
                   help=f"Overlay workspace path inside the image (default: {DEFAULTS['overlay_ws']}).")
    p.add_argument("--from-image", default=None,
                   help="Override the base image reference. Defaults to "
                        "osrf/ros:<ros-distro>-ros-base.")
    p.add_argument("--target-dir", default=".",
                   help="Directory to write Dockerfile and .dockerignore into (default: current dir).")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    target = Path(args.target_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)

    from_image = render_from_image(args.ros_distro, args.from_image)

    dockerfile_src = (TEMPLATE_DIR / "Dockerfile.template").read_text()
    dockerfile_out = substitute_defaults(dockerfile_src, args.ros_distro, args.overlay_ws, from_image)
    (target / "Dockerfile").write_text(dockerfile_out)

    # .dockerignore has no defaults to substitute; just copy.
    shutil.copyfile(TEMPLATE_DIR / ".dockerignore.template", target / ".dockerignore")

    print(f"Wrote {target / 'Dockerfile'}")
    print(f"Wrote {target / '.dockerignore'}")
    print(f"Defaults: ROS_DISTRO={args.ros_distro}  FROM_IMAGE={from_image}  OVERLAY_WS={args.overlay_ws}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
