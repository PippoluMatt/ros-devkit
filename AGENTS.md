# Repository Guidelines

## Project Structure & Module Organization

This repository is a curated collection of installable Codex skills for ROS2 development. Domain language and preferred terms live in `CONTEXT.md`; contribution process and conduct are in `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`.

Curated skills live under `skills/.curated/ros2/<skill-name>/`. Each skill must have a `SKILL.md` with YAML frontmatter and task instructions. Use `references/` for longer optional documentation, `scripts/` for deterministic generators or mutators, `assets/` for reusable templates, and `agents/openai.yaml` for UI metadata. Skill directories use kebab-case, for example `ros2-control`, `mcu-protocol`, and `description-scaffold`.

## Build, Test, and Development Commands

There is no repository-wide build step. Validate the files you change directly:

- `python3 -m py_compile skills/.curated/ros2/<skill>/scripts/*.py` checks Python script syntax.
- `python3 skills/.curated/ros2/description-scaffold/scripts/validate.py <package-dir>` validates generated description packages.
- `python3 skills/.curated/ros2/ros2-dockerfile/scripts/render_dockerfile.py --target-dir /tmp/dockerfile-check` smoke-tests Dockerfile rendering.
- `git diff --check` catches trailing whitespace and patch formatting issues.

## Coding Style & Naming Conventions

Keep skill instructions concise and imperative. Put only frequently needed guidance in `SKILL.md`; move detailed variants to `references/`. Match existing Markdown style, use fenced code blocks for commands, and keep links relative within a skill directory. Python scripts use Python 3, `pathlib` where practical, type hints for public helpers, and clear CLI arguments via `argparse`.

## Testing Guidelines

Add focused tests or smoke checks when changing scripts, generators, or templates. Prefer temporary output directories under `/tmp` and inspect generated files before committing. For documentation-only skill edits, verify that referenced files exist and that frontmatter still includes `name` and `description`.

## Commit & Pull Request Guidelines

Recent commits are short, descriptive summaries of the changed area rather than strict conventional commits. Use messages such as `Add ros2 dockerfile skill` or `Update launch references`. Keep PRs focused on one skill or one shared concern, describe the validation performed, link related issues, and note any new scripts, references, or assets.

## Agent-Specific Instructions

When editing skills, touch only the relevant skill unless a shared namespace concern requires more. Prefer existing scripts over manual rewrites, and do not add new generators unless deterministic output is necessary.

## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `PippoluMatt/ros-devkit`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default Matt Pocock skill triage labels unchanged. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo using root `CONTEXT.md` and optional root `docs/adr/`. See `docs/agents/domain.md`.
