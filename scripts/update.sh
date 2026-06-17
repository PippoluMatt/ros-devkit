#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${ROS_DEVKIT_REPO_URL:-https://github.com/PippoluMatt/ros-devkit.git}"
ARCHIVE_BASE_URL="${ROS_DEVKIT_ARCHIVE_BASE_URL:-https://github.com/PippoluMatt/ros-devkit/archive}"
REF="main"
NAMESPACE="ros2"
MARKER_FILE=".ros-devkit-source"

INSTALL_HOME="${ROS_DEVKIT_INSTALL_HOME:-$HOME/.local/share/ros-devkit}"
SOURCE_DIR="${ROS_DEVKIT_SOURCE:-$INSTALL_HOME/source}"
VENV_DIR="$INSTALL_HOME/venv"
BIN_DIR="${ROS_DEVKIT_BIN_DIR:-$HOME/.local/bin}"
BIN_PATH="$BIN_DIR/ros-devkit"
MANAGED_BIN_TARGET="$VENV_DIR/bin/ros-devkit"

force=0
dry_run=0
agent=""
namespace_root=""
agent_skill_root=""
staged_source=""
staged_venv=""
staged_namespace=""
temp_paths=()

usage() {
  cat <<'EOF'
usage: ros-devkit update [--dry-run] [--force]

Update an installer-managed ros-devkit install from the latest main branch.

Options:
  --dry-run  Stage and validate the update without replacing installed files.
  --force    Replace installed skills even if local edits are detected.
  -h, --help Show this help.
EOF
}

log() {
  printf '%s\n' "$*"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  local path
  for path in "${temp_paths[@]}"; do
    if [[ -n "$path" && -e "$path" ]]; then
      rm -rf "$path"
    fi
  done
}
trap cleanup EXIT

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --force)
        force=1
        shift
        ;;
      --dry-run)
        dry_run=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument: $1"
        ;;
    esac
  done
}

need_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "Missing required command: $1"
  fi
}

config_file() {
  if [[ -n "${ROS_DEVKIT_CONFIG:-}" ]]; then
    printf '%s\n' "$ROS_DEVKIT_CONFIG"
    return
  fi

  if [[ -n "${XDG_CONFIG_HOME:-}" ]]; then
    printf '%s\n' "$XDG_CONFIG_HOME/ros-devkit/config.env"
    return
  fi

  printf '%s\n' "$HOME/.config/ros-devkit/config.env"
}

load_config() {
  local path
  path="$(config_file)"
  [[ -f "$path" ]] || die "Config file not found: $path"

  # config.env is generated as shell-compatible KEY=value assignments.
  # shellcheck disable=SC1090
  source "$path"

  agent="${ROS_DEVKIT_AGENT:-}"
  namespace_root="${ROS_DEVKIT_SKILL_ROOT:-}"

  [[ -n "$agent" ]] || die "Missing ROS_DEVKIT_AGENT in config file: $path"
  [[ -n "$namespace_root" ]] || die "Missing ROS_DEVKIT_SKILL_ROOT in config file: $path"

  case "$namespace_root" in
    "~")
      namespace_root="$HOME"
      ;;
    "~/"*)
      namespace_root="$HOME/${namespace_root#~/}"
      ;;
  esac

  agent_skill_root="$(dirname "$namespace_root")"
}

preflight_commands() {
  need_command python3
  need_command mkdir
  need_command cp
  need_command chmod
  need_command diff
  need_command dirname
  need_command find
  need_command ln
  need_command mktemp
  need_command mv
  need_command readlink
  need_command rm
  need_command rmdir
  need_command sed

  if ! command -v git >/dev/null 2>&1; then
    need_command curl
    need_command tar
  fi
}

preflight_managed_install() {
  [[ -d "$INSTALL_HOME" ]] || die "Install home does not exist: $INSTALL_HOME"
  [[ -d "$SOURCE_DIR" ]] || die "Managed source does not exist: $SOURCE_DIR"
  [[ -f "$SOURCE_DIR/$MARKER_FILE" ]] || die "update is only available for installer-managed installs."
  [[ -d "$SOURCE_DIR/skills/.curated/$NAMESPACE" ]] || die "Managed source is missing skills/.curated/$NAMESPACE"
  [[ -d "$VENV_DIR" ]] || die "Managed venv does not exist: $VENV_DIR"
  [[ -d "$namespace_root" ]] || die "Configured namespace root does not exist: $namespace_root"
  [[ -d "$agent_skill_root" ]] || die "Agent skill root does not exist: $agent_skill_root"

  if [[ ! -L "$BIN_PATH" ]]; then
    die "ros-devkit command is not managed by this installer: $BIN_PATH"
  fi

  local target
  target="$(readlink "$BIN_PATH")"
  if [[ "$target" != "$MANAGED_BIN_TARGET" ]]; then
    die "ros-devkit command is not managed by this installer: $BIN_PATH -> $target"
  fi
}

new_temp_dir() {
  local template="$1"
  local path
  path="$(mktemp -d "$template")"
  temp_paths+=("$path")
  printf '%s\n' "$path"
}

acquire_source_with_git() {
  staged_source="$(new_temp_dir "$INSTALL_HOME/.source.update.XXXXXX")"

  log "Fetching latest ros-devkit main with git..."
  git -C "$staged_source" init -q
  git -C "$staged_source" remote add origin "$REPO_URL"
  git -C "$staged_source" fetch --depth 1 origin "$REF"
  git -C "$staged_source" checkout -q --detach FETCH_HEAD

  printf 'repo=%s\nref=%s\n' "$REPO_URL" "$REF" > "$staged_source/$MARKER_FILE"
}

acquire_source_with_archive() {
  local archive_dir
  local archive_path
  local extracted=""
  local candidate

  archive_dir="$(new_temp_dir "$INSTALL_HOME/.archive.update.XXXXXX")"
  archive_path="$archive_dir/source.tar.gz"

  log "Fetching latest ros-devkit main archive..."
  curl -fsSL "$ARCHIVE_BASE_URL/$REF.tar.gz" -o "$archive_path"
  tar -xzf "$archive_path" -C "$archive_dir"

  for candidate in "$archive_dir"/ros-devkit-*; do
    if [[ -d "$candidate" ]]; then
      extracted="$candidate"
      break
    fi
  done

  [[ -n "$extracted" ]] || die "Downloaded archive did not contain a ros-devkit source directory."

  staged_source="$(new_temp_dir "$INSTALL_HOME/.source.update.XXXXXX")"
  cp -R "$extracted/." "$staged_source/"
  printf 'repo=%s\nref=%s\n' "$REPO_URL" "$REF" > "$staged_source/$MARKER_FILE"
}

acquire_source() {
  if command -v git >/dev/null 2>&1; then
    acquire_source_with_git
  else
    acquire_source_with_archive
  fi
}

clean_namespace() {
  local path="$1"
  find "$path" -type d -name '__pycache__' -prune -exec rm -rf {} +
  find "$path" -type f \( -name '*.pyc' -o -name '.DS_Store' \) -delete
}

check_local_skill_edits() {
  local diff_output
  diff_output="$(mktemp "${TMPDIR:-/tmp}/ros-devkit-diff.XXXXXX")"
  temp_paths+=("$diff_output")

  if diff -qr -x '__pycache__' -x '*.pyc' -x '.DS_Store' \
    "$SOURCE_DIR/skills/.curated/$NAMESPACE" "$namespace_root" > "$diff_output"; then
    return
  fi

  if [[ "$force" -eq 1 ]]; then
    log "Local skill edits detected; --force will replace the installed namespace."
    return
  fi

  printf 'ERROR: Local changes detected in installed namespace: %s\n' "$namespace_root" >&2
  sed -n '1,20p' "$diff_output" >&2
  printf 'Run ros-devkit update --force to replace the installed skills anyway.\n' >&2
  exit 1
}

stage_namespace() {
  staged_namespace="$(new_temp_dir "$agent_skill_root/.${NAMESPACE}.update.XXXXXX")"
  cp -R "$staged_source/skills/.curated/$NAMESPACE/." "$staged_namespace/"
  clean_namespace "$staged_namespace"
}

write_cli_wrapper() {
  local wrapper="$1"
  {
    echo '#!/usr/bin/env bash'
    echo 'set -euo pipefail'
    printf 'ROS_DEVKIT_SOURCE=%q\n' "$SOURCE_DIR"
    printf 'ROS_DEVKIT_PYTHON=%q\n' "$VENV_DIR/bin/python"
    echo 'export ROS_DEVKIT_SOURCE ROS_DEVKIT_PYTHON'
    echo 'PYTHONPATH="$ROS_DEVKIT_SOURCE/src${PYTHONPATH:+:$PYTHONPATH}"'
    echo 'export PYTHONPATH'
    echo 'exec "$ROS_DEVKIT_PYTHON" -m ros_devkit.cli "$@"'
  } > "$wrapper"
  chmod +x "$wrapper"
}

stage_venv() {
  staged_venv="$(new_temp_dir "$INSTALL_HOME/.venv.update.XXXXXX")"
  python3 -m venv "$staged_venv"
  write_cli_wrapper "$staged_venv/bin/ros-devkit"
}

validate_staged_source() {
  [[ -f "$staged_source/pyproject.toml" ]] || die "Fetched source is missing pyproject.toml"
  [[ -d "$staged_source/skills/.curated/$NAMESPACE" ]] || die "Fetched source is missing skills/.curated/$NAMESPACE"
  [[ -f "$staged_source/scripts/update.sh" ]] || die "Fetched source is missing scripts/update.sh"

  PYTHONPATH="$staged_source/src" "$staged_venv/bin/python" -m py_compile "$staged_source"/src/ros_devkit/*.py
  PYTHONPATH="$staged_source/src" "$staged_venv/bin/python" -m ros_devkit.cli --version >/dev/null
  ROS_DEVKIT_SKILL_ROOT="$staged_namespace" \
    PYTHONPATH="$staged_source/src" \
    "$staged_venv/bin/python" -m ros_devkit.cli doctor >/dev/null
}

python_package_version() {
  local source="$1"
  PYTHONPATH="$source/src" python3 - <<'PY'
import ros_devkit
print(ros_devkit.__version__)
PY
}

git_short_sha() {
  local source="$1"
  if [[ -d "$source/.git" ]] && command -v git >/dev/null 2>&1; then
    git -C "$source" rev-parse --short HEAD 2>/dev/null || true
  fi
}

print_summary() {
  local old_version
  local new_version
  local old_sha
  local new_sha

  old_version="$(python_package_version "$SOURCE_DIR" 2>/dev/null || printf 'unknown')"
  new_version="$(python_package_version "$staged_source" 2>/dev/null || printf 'unknown')"
  old_sha="$(git_short_sha "$SOURCE_DIR")"
  new_sha="$(git_short_sha "$staged_source")"

  log "Update plan"
  log "  Source checkout  : $SOURCE_DIR"
  log "  CLI venv         : $VENV_DIR"
  log "  CLI command      : $BIN_PATH"
  log "  Namespace root   : $namespace_root"
  log "  Ref              : $REF"
  log "  Version          : $old_version -> $new_version"
  if [[ -n "$old_sha" || -n "$new_sha" ]]; then
    log "  Commit           : ${old_sha:-unknown} -> ${new_sha:-unknown}"
  fi
}

replace_dir() {
  local target="$1"
  local replacement="$2"
  local label="$3"
  local old_path

  old_path="$(mktemp -d "$(dirname "$target")/.${label}.old.XXXXXX")"
  rmdir "$old_path"
  mv "$target" "$old_path"
  mv "$replacement" "$target"
  rm -rf "$old_path"
}

apply_update() {
  log "Applying update..."
  replace_dir "$VENV_DIR" "$staged_venv" "venv"
  ln -sfn "$MANAGED_BIN_TARGET" "$BIN_PATH"
  replace_dir "$namespace_root" "$staged_namespace" "$NAMESPACE"
  replace_dir "$SOURCE_DIR" "$staged_source" "source"

  "$BIN_PATH" doctor >/dev/null
  log "Updated ros-devkit from latest main."
}

main() {
  parse_args "$@"
  preflight_commands
  load_config
  preflight_managed_install
  acquire_source
  check_local_skill_edits
  stage_namespace
  stage_venv
  validate_staged_source
  print_summary

  if [[ "$dry_run" -eq 1 ]]; then
    log "Dry run: no changes made."
    return
  fi

  apply_update
}

main "$@"
