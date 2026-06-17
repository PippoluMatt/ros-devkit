---
name: ros2-dockerfile
description: Author a Dockerfile that builds a custom ROS 2 image from osrf/ros at a chosen distro's ros-base tag, optionally importing an overlay of git-cloned packages declared in a remote .repos file, running rosdep and colcon build, and producing a runnable image with the overlay sourced from /ros_entrypoint.sh. Use when creating a new ROS 2 Dockerfile, adding a multi-stage cacher+builder overlay pattern, choosing between ros-base and ros-desktop, wiring build-args for ROS_DISTRO/FROM_IMAGE/OVERLAY_WS/OVERLAY_REPOS_URL/OVERLAY_PACKAGES, generating a .dockerignore for a colcon workspace, or running docker build and docker run for the resulting image. Do not use for docker-compose multi-container setups, Kubernetes manifests, registry push, or running prebuilt osrf/ros images without a custom Dockerfile.
---

# ROS 2 Dockerfile

Generate a multi-stage Dockerfile that builds a custom ROS 2 image on top of `osrf/ros:${ROS_DISTRO}-ros-base`. The default template is headless (no `rviz`, `rqt`, or `gazebo`); switch to `-desktop` via `--build-arg FROM_IMAGE=osrf/ros:${ROS_DISTRO}-desktop` when those tools are needed.

## Workflow

1. Render the template into the target workspace:
   ```bash
   python3 <skill-root>/scripts/render_dockerfile.py [--ros-distro <codename>] [--target-dir <dir>]
   ```
   This writes `Dockerfile` and `.dockerignore` into the target directory. The target directory becomes the Docker build context, so point it at a colcon workspace root (or any directory where running `docker build .` is the intended operation).
2. Decide whether the image needs an overlay (custom packages layered on top of the base) or is just the base image plus some `apt install` lines.
3. If an overlay is needed, host a vcs-tool `.repos` file somewhere fetchable (typically in the same git repo as the packages, or in a dedicated "manifest" repo) and pass its URL via `OVERLAY_REPOS_URL`. Read [references/overlay-repos-format.md](references/overlay-repos-format.md) for the file syntax.
4. If only the base image is needed, leave `OVERLAY_REPOS_URL` unset. The Dockerfile builds a valid image that is functionally `osrf/ros:<distro>-ros-base` with `$OVERLAY_WS` prepared for runtime use; the user can extend it with their own `RUN` lines.
5. Build:
   ```bash
   docker build -t my-image \
     [--build-arg ROS_DISTRO=jazzy] \
     [--build-arg FROM_IMAGE=osrf/ros:jazzy-ros-base] \
     [--build-arg OVERLAY_REPOS_URL=https://example.com/overlay.repos] \
     [--build-arg OVERLAY_PACKAGES="pkg1 pkg2"] \
     .
   ```
6. Run:
   ```bash
   docker run --rm -it my-image                                          # interactive shell
   docker run --rm my-image ros2 launch my_pkg my_launch.launch.py        # one-shot
   ```
   The image's default `CMD` is `bash`. The overlay (if built) is on the ROS package path because `/ros_entrypoint.sh` sources `$OVERLAY_WS/install/setup.bash` on every container start.

## Build-arg decision tree

- **`ROS_DISTRO`**: set to the target codename (`jazzy`, `humble`, `kilted`, `rolling`, ...). Default `jazzy`. The builder stages source `/opt/ros/$ROS_DISTRO/setup.bash`, so this must match the ROS install in the base image.
- **`FROM_IMAGE`**: override only for registry mirrors, pinned digests, or to switch between `-ros-base` and `-desktop`. Default composes from `ROS_DISTRO` as `osrf/ros:${ROS_DISTRO}-ros-base`. When overridden, set `ROS_DISTRO` to match.
- **`OVERLAY_WS`**: leave at the default `/opt/ros/overlay_ws` unless the path is already occupied. Anything under `/opt/ros/` is fine; the cacher relies on the path living under `/opt` for the manifest-caching trick.
- **`OVERLAY_REPOS_URL`**: set to import a `.repos` file. Unset to build the bare base image.
- **`OVERLAY_PACKAGES`**: optional subset selector for `colcon build --packages-select`. Leave unset to build every package imported by the `.repos` file.
- **`OVERLAY_MIXINS`**: optional `colcon` build mixin. Default `release`.

## What the template does not do

- It does not push to a registry. Tag the image with a registry path (`docker build -t registry.example.com/my-image:tag .`) and run `docker push` separately.
- It does not write a `docker-compose.yml`. Multi-container ROS 2 topologies (talker + listener in separate containers, DDS discovery across containers) are out of scope.
- It does not write Kubernetes manifests.
- It does not include any `apt install` lines beyond what the base image provides. To add system packages, add `RUN apt-get update && apt-get install -y <pkg> && rm -rf /var/lib/apt/lists/*` to the builder stage.
- It does not support authenticated git clones. Private repos require a custom base image with credentials baked in, or a separate CI step.

## Reference

- [references/dockerfile-anatomy.md](references/dockerfile-anatomy.md) — line-by-line walkthrough of the generated Dockerfile, including the manifest-caching layer trick, the no-overlay path, and layer-caching expectations.
- [references/overlay-repos-format.md](references/overlay-repos-format.md) — the vcs-tool `.repos` file syntax, common patterns, and hosting options.
