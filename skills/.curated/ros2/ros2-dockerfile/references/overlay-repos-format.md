# `overlay.repos` Format

The Dockerfile's `OVERLAY_REPOS_URL` build-arg points at a vcs-tool `.repos` file. The `vcs import` command (provided by the `python3-vcstool` apt package, pre-installed in `osrf/ros` images) reads the file and clones the listed repositories into the current directory.

## Schema

```yaml
repositories:
  <import-path>:
    type: git
    url: <git-url>
    version: <branch-or-tag-or-commit>
  <import-path>:
    type: git
    url: <git-url>
    version: <branch-or-tag-or-commit>
```

`<import-path>` is a relative path under the workspace `src/` directory where the repository will be cloned.

## Minimal example

```yaml
repositories:
  my_company/my_ros_pkg:
    type: git
    url: https://github.com/my_company/my_ros_pkg.git
    version: main
```

This clones `my_ros_pkg` to `<OVERLAY_WS>/src/my_company/my_ros_pkg/`.

## Common patterns

**Multiple repos for one project:**

```yaml
repositories:
  my_company/my_robot:
    type: git
    url: https://github.com/my_company/my_robot.git
    version: ${ROS_DISTRO}
  my_company/my_robot_msgs:
    type: git
    url: https://github.com/my_company/my_robot_msgs.git
    version: ${ROS_DISTRO}
```

**Pinning to a tag or commit (for reproducible builds):**

```yaml
repositories:
  my_company/my_ros_pkg:
    type: git
    url: https://github.com/my_company/my_ros_pkg.git
    version: v1.2.3
```

**Using `${ROS_DISTRO}` substitution:** `vcs import` expands `${ROS_DISTRO}` from the environment of the running `RUN` step. Since the Dockerfile sets `ARG ROS_DISTRO` and `ENV ROS_DISTRO` in the final stage, this works in the builder as well.

## Hosting the `.repos` file

The URL must be fetchable from inside the container at build time. Common options:

- **A file in the same git repo as the packages**, e.g. `https://raw.githubusercontent.com/my_company/my_ros_pkg/main/overlay.repos`. The `vcs` tool downloads the file and clones the listed repos.
- **A separate "manifest" repo** that lists all the repos for a project. Useful when one `.repos` file covers many packages from different repos.
- **A private URL** that requires credentials. The Dockerfile does not currently support authenticated clones — for private repos, bake the credentials into a custom base image or use a CI-side `git config` step.

## Relationship to `colcon build`

`vcs import` only clones. The build step (`colcon build` in the builder stage) then walks `$OVERLAY_WS/src/` and builds any package it finds. If a repo is listed in the `.repos` file but its packages are out of date or broken, the build will fail. Use `OVERLAY_PACKAGES` to build only a subset:

```bash
docker build \
  --build-arg OVERLAY_REPOS_URL=https://example.com/overlay.repos \
  --build-arg OVERLAY_PACKAGES="my_ros_pkg my_other_pkg" \
  -t my-image .
```

## Related tooling

- **`vcs`**: the tool that reads `.repos` files. CLI subcommands: `import`, `export`, `pull`, `log`, `custom`, `validate`. See `vcs --help` inside a running container.
- **`rosdistro`**: a different (and more complex) manifest format. Not used by this skill.
- **`colcon mixin`**: a separate way to set compiler flags. The Dockerfile defaults to the `release` mixin; override with `--build-arg OVERLAY_MIXINS="release ccache"`.
