# Dockerfile Anatomy

Line-by-line walkthrough of the generated `Dockerfile`. Read this when you need to understand *why* a line is there, not *what* it does (the comments in the template already cover the what).

## Build arguments

| ARG | Default | Purpose |
| --- | --- | --- |
| `FROM_IMAGE` | `osrf/ros:${ROS_DISTRO}-ros-base` | The base image all three stages extend. Override for registry mirrors, pinned digests, or a custom underlay image. |
| `ROS_DISTRO` | `jazzy` | The ROS 2 codename. Used to compose the default `FROM_IMAGE` and to source `/opt/ros/$ROS_DISTRO/setup.bash` in builder stages. |
| `OVERLAY_WS` | `/opt/ros/overlay_ws` | Absolute path inside the image where the overlay workspace is built. |
| `OVERLAY_REPOS_URL` | *(unset)* | URL of a vcs-tool `.repos` file to clone. When set, the image builds the overlay. When unset, the image is the base image only. |
| `OVERLAY_PACKAGES` | *(unset)* | Optional space-separated list of packages to build. When set, the build is restricted via `colcon build --packages-select`. |
| `OVERLAY_MIXINS` | `release` | The `colcon` build mixin. Default is release optimization. |

## Stage 1: `cacher`

The cacher stage exists purely to create a Docker layer that contains only `package.xml` (and `COLCON_IGNORE`) manifests. This decouples dependency installation (`rosdep install`) from source-file changes, so a `.cpp` edit does not trigger a 60-second `apt-get update`.

1. `WORKDIR $OVERLAY_WS/src` then `vcs import ./ < /tmp/overlay.repos` — clone the repos listed in the `.repos` URL into the overlay's `src/`.
2. `WORKDIR /opt` then `find ./ -name "package.xml" | xargs cp --parents -t /tmp/opt` — copy every `package.xml` found under `/opt` (which now includes the overlay source at `/opt/ros/overlay_ws/src/`) into a manifest-only tree at `/tmp/opt/...`, preserving the relative path under `/opt`.

The path arithmetic works because `cp --parents` preserves the path *as `find` printed it* (relative, starting with `./`), and Docker `COPY` reads the `/tmp/opt` tree as if it were rooted there. The builder's `COPY --from=cacher /tmp/$OVERLAY_WS/src ./src` reads `/tmp/opt/ros/overlay_ws/src` — the same path the cacher wrote to.

## Stage 2: `builder`

1. First `COPY` brings in the manifest-only tree. `rosdep install --from-paths src --ignore-src` walks `./src` looking for `package.xml` files and installs only the dependencies those manifests declare. Because only manifests were copied (not source code), this layer is stable across code changes.
2. Second `COPY` brings in the full overlay source for the actual `colcon build`. The build is gated on `OVERLAY_REPOS_URL` and uses `--packages-select $OVERLAY_PACKAGES` when the build-arg is set.

## Final stage

1. `COPY --from=builder $OVERLAY_WS $OVERLAY_WS` brings the built overlay (and any source if the build was skipped) into the runtime image.
2. The `sed` appends `source "$OVERLAY_WS/install/setup.bash"` to `/ros_entrypoint.sh` *only if* the build produced `install/setup.bash` (i.e. only if an overlay was actually built). This is the line that makes the overlay packages visible to every `docker run` invocation, because the `osrf/ros` base image's `/ros_entrypoint.sh` is what every shell sources on container start.
3. `CMD ["bash"]` — the default is an interactive shell. Override at `docker run` time:

   ```bash
   docker run --rm my-image ros2 launch my_pkg my_launch.py
   docker run --rm -it my-image bash
   ```

## When the overlay is disabled

When `OVERLAY_REPOS_URL` is unset, the same Dockerfile still builds, but with empty overlay stages:

- Cacher creates `$OVERLAY_WS/src/COLCON_IGNORE` (an empty file) and skips the `vcs import`. The `find` step runs but finds nothing in the empty src.
- Builder's `COPY` lines copy an effectively empty `src/` (just the `COLCON_IGNORE` file). The gated `rosdep` and `colcon build` `RUN` blocks skip cleanly.
- Final stage copies the empty overlay. The `sed` skips because `install/setup.bash` does not exist.

The result is functionally the `osrf/ros:<distro>-ros-base` image with the `OVERLAY_WS` directory structure prepared, ready for the user to `docker run -it my-image` and `apt install` whatever extra system packages they need (or to add their own `RUN` lines in the builder for that).

## Layer caching expectations

A typical code-only edit (`*.cpp` change) invalidates only the second `COPY` in the builder and the `colcon build` step. `apt-get update` and `rosdep install` remain cached. A `package.xml` edit invalidates the manifest layer (re-runs `rosdep install`) but not `apt-get update`. Adding a new repo to the `.repos` file invalidates the cacher's `vcs import` layer, the two `COPY` lines, and `colcon build`.

## Customising the base image

For non-default images, override `FROM_IMAGE` directly:

```bash
docker build --build-arg FROM_IMAGE=my.registry.local/ros:humble-ros-base -t my-image .
```

When `FROM_IMAGE` is overridden, the `ROS_DISTRO` build-arg is still needed for the builder to source `/opt/ros/$ROS_DISTRO/setup.bash` correctly. Set both to match.
