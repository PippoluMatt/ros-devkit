# Repository Guidelines

## Project Structure & Module Organization

This repository is a dual-purpose ROS2 DevKit: a small Python CLI dispatcher plus a curated collection of installable ROS2 agent skills. Keep user-facing install and usage detail in `README.md`; keep this file focused on maintenance guidance for agents.

The CLI package lives under `src/ros_devkit/`. It reads configuration, exposes built-in `doctor` and `update` commands, and dispatches registered skill commands to Python scripts under the configured namespace root. The CLI should not contain ROS2 package-generation logic; that belongs in skill scripts and references.

Installer, updater, and development wrappers live under `install/`. A shared bash library at `install/lib/install_common.sh` provides common functions (logging, error handling, source acquisition, CLI wrapper generation, namespace cleaning) sourced by both `install/install.sh` and `install/update.sh`. Tests live under `tests/` and exercise config loading, installer behavior, local sandbox installs, and updater behavior. Domain language and preferred terms live in `CONTEXT.md`; contribution and conduct docs are `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`.

Curated skills live under `skills/.curated/ros2/<skill-name>/`. Each skill must have a `SKILL.md` with YAML frontmatter and task instructions. Use `references/` for longer optional documentation, `scripts/` for deterministic generators or mutators, `assets/` for reusable templates, and `agents/openai.yaml` for UI metadata. Skill directories use kebab-case, for example `ros2-control`, `mcu-protocol`, and `description-scaffold`.

## CLI and Installer Maintenance

Treat `src/ros_devkit/registry.py` as the public command map for skill-backed CLI commands. When adding or renaming a CLI command, keep the registry entry, `_print_help()` in `src/ros_devkit/cli.py`, relevant README CLI reference text, and tests in sync.

Use `install/dev_ros_devkit.sh` to run checkout code and checkout skills during local development. Do not validate checkout changes through a globally installed `ros-devkit` unless the task is specifically about installed behavior.

Use `install/install.sh --local-sandbox .dev-install` for isolated installer smoke tests. Local sandbox installs are self-contained and intentionally do not support `ros-devkit update`; re-run the sandbox installer after checkout changes.

Do not edit `src/ros_devkit.egg-info/` directly unless the task explicitly requires regenerating packaged metadata.

## Build, Test, and Development Commands

There is no repository-wide build step. Validate the files you change directly:

- `python3 -m unittest discover -s tests` runs the CLI, config, install, and update tests.
- `python3 -m py_compile src/ros_devkit/*.py` checks CLI package syntax.
- `python3 -m py_compile skills/.curated/ros2/<skill>/scripts/*.py` checks skill-local script syntax.
- `python3 -m py_compile skills/.curated/ros2/scripts/cmake_lib/*.py skills/.curated/ros2/scripts/ros2_control_pluginize_lib/*.py skills/.curated/ros2/scripts/utils/*.py` checks shared library syntax.
- `python3 -m unittest discover -s skills/.curated/ros2/description-scaffold/checks` runs description-scaffold validation checks.
- `python3 -m unittest discover -s skills/.curated/ros2/gazebo-simulation/checks` runs gazebo-simulation checks.
- `bash -n install/install.sh install/update.sh install/configure_ros_devkit.sh install/dev_ros_devkit.sh` checks shell script syntax.
- `install/dev_ros_devkit.sh doctor` verifies the checkout dispatcher can find curated skill scripts.
- `python3 skills/.curated/ros2/description-scaffold/scripts/validate.py <package-dir>` validates generated description packages.
- `python3 skills/.curated/ros2/ros2-dockerfile/scripts/render_dockerfile.py --target-dir /tmp/dockerfile-check` smoke-tests Dockerfile rendering.
- `git diff --check` catches trailing whitespace and patch formatting issues.

## Coding Style & Naming Conventions

Keep skill instructions concise and imperative. Put only frequently needed guidance in `SKILL.md`; move detailed variants to `references/`. Match existing Markdown style, use fenced code blocks for commands, and keep links relative within a skill directory.

Python code targets Python 3.10+, uses the standard library by default, and prefers `pathlib`, type hints for public helpers, `argparse` for CLIs, and focused `unittest` coverage. Shell scripts are Bash scripts; keep them non-interactive where tests need automation and preserve existing safety checks around managed installs and sandbox deletion.

## Testing Guidelines

Add focused tests or smoke checks when changing CLI behavior, registry mappings, installer/update logic, scripts, generators, or templates. Prefer temporary output directories under `/tmp` or `tempfile` and inspect generated files before committing.

For documentation-only skill edits, verify that referenced files exist and that frontmatter still includes `name` and `description`. For README or CLI help changes, check that command names and option names match the actual registry and scripts.

## Commit & Pull Request Guidelines

Recent commits are short, descriptive summaries of the changed area rather than strict conventional commits. Use messages such as `Add ros2 dockerfile skill` or `Update launch references`. Keep PRs focused on one skill, one CLI surface, or one shared concern. Describe the validation performed, link related issues, and note any new scripts, references, assets, or installer behavior.

## Agent-Specific Instructions

Always use the git worktree workflow for this repo. Start each new task from a separate worktree and task branch, keep the primary checkout clean, and avoid mixing unrelated changes in one worktree. If you inherit an existing dirty checkout, preserve the user’s changes and continue only when the requested edit clearly belongs to that same in-progress work.

```bash
git worktree add ../project-bugfix -b fix-X
cd ../project-bugfix
git add .
git commit -m "Critic Bug Resolved"
git push origin fix-X
cd ../project-main
git worktree remove ../project-bugfix
```

When editing skills, touch only the relevant skill unless a shared namespace concern requires more. Prefer existing scripts over manual rewrites, and do not add new generators unless deterministic output is necessary.

When editing the CLI dispatcher, avoid moving ROS2-specific behavior into `src/ros_devkit/`; dispatch to skill-owned scripts instead. When editing installer or updater behavior, preserve safeguards for unmanaged commands, local edits in installed skills, and marked local sandboxes.

## Agent Skills

### Issue Tracker

Issues and PRDs are tracked in GitHub Issues for `PippoluMatt/ros-devkit`. See `docs/agents/issue-tracker.md`.

### Triage Labels

Use the default Matt Pocock skill triage labels unchanged. See `docs/agents/triage-labels.md`.

### Domain Docs

This is a single-context repo using root `CONTEXT.md` and optional root `docs/adr/`. See `docs/agents/domain.md`.
