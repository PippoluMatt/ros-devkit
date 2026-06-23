# Shared bash library for ros-devkit install and update scripts.
#
# Contract: the caller must declare and populate these globals before
# calling library functions:
#
#   REPO_URL          git remote URL for the ros-devkit source
#   ARCHIVE_BASE_URL  base URL for source archives
#   MARKER_FILE       filename of the source marker (.ros-devkit-source)
#   REF               git ref to fetch (branch, tag, or SHA)
#   temp_paths        array; populated by acquire_source_with_archive and
#                     cleaned by cleanup on EXIT
#
# write_cli_wrapper also reads:
#   SOURCE_DIR          managed source directory path
#   VENV_DIR            managed venv directory path
#   CONFIG_FILE         config file path (sandbox mode only)
#   local_sandbox_root  sandbox root path (sandbox mode only)
# CONFIG_FILE and local_sandbox_root are only expanded when emit_sandbox is 1.
#
# normalize_agent reads and mutates the global `agent`.
# agent_skill_root_for reads $HOME only.

# ---------------------------------------------------------------------------
# General utilities
# ---------------------------------------------------------------------------

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

need_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "Missing required command: $1"
  fi
}

expand_path() {
  case "$1" in
    "~")
      printf '%s\n' "$HOME"
      ;;
    "~/"*)
      printf '%s\n' "$HOME/${1#~/}"
      ;;
    *)
      printf '%s\n' "$1"
      ;;
  esac
}

# prompt_tty <prompt>
# Read a single line from /dev/tty. Caller must verify TTY availability
# and provide an appropriate error message before calling.
prompt_tty() {
  local prompt="$1"
  local value
  printf '%s' "$prompt" > /dev/tty
  IFS= read -r value < /dev/tty || die "No input received."
  printf '%s\n' "$value"
}

# ---------------------------------------------------------------------------
# Agent target utilities
# ---------------------------------------------------------------------------

# Print the agent selection menu to the given file descriptor.
# Defaults to /dev/stdout.
print_agent_menu() {
  local fd="${1:-/dev/stdout}"
  cat > "$fd" <<'EOF'
Select the AI agent target:
  1) codex  - $HOME/.codex/skills/ros2
  2) claude - $HOME/.claude/skills/ros2
  3) pi     - $HOME/.pi/agent/skills/ros2
  4) custom - provide a parent skills directory
EOF
}

# Normalize a numeric selection to a canonical agent name, or validate an
# existing name. Reads and mutates the global `agent`. Dies on unknown input.
normalize_agent() {
  case "$agent" in
    1) agent="codex"   ;;
    2) agent="claude"  ;;
    3) agent="pi"      ;;
    4) agent="custom" ;;
  esac

  case "$agent" in
    codex|claude|pi|custom) ;;
    *) die "Unsupported agent target: $agent" ;;
  esac
}

# Resolve the default agent skill root (parent directory) for a known agent.
# Prints the path for codex/claude/pi, or an empty string for custom/unknown.
agent_skill_root_for() {
  case "$1" in
    codex)  printf '%s\n' "$HOME/.codex/skills"   ;;
    claude) printf '%s\n' "$HOME/.claude/skills"  ;;
    pi)     printf '%s\n' "$HOME/.pi/agent/skills" ;;
    *)      printf '\n'                         ;;
  esac
}

# ---------------------------------------------------------------------------
# Source acquisition
# ---------------------------------------------------------------------------

# Fetch source via git into the target directory (must already exist).
acquire_source_with_git() {
  local target="$1"
  log "Fetching ros-devkit source with git..."
  git -C "$target" init -q
  git -C "$target" remote add origin "$REPO_URL"
  git -C "$target" fetch --depth 1 origin "$REF"
  git -C "$target" checkout -q --detach FETCH_HEAD
  printf 'repo=%s\nref=%s\n' "$REPO_URL" "$REF" > "$target/$MARKER_FILE"
}

# Fetch source via archive into the target directory (must already exist).
acquire_source_with_archive() {
  local target="$1"
  local tmp_dir
  local archive_path
  local extracted=""
  local candidate

  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/ros-devkit-archive.XXXXXX")"
  temp_paths+=("$tmp_dir")
  archive_path="$tmp_dir/source.tar.gz"

  log "Fetching ros-devkit source archive..."
  curl -fsSL "$ARCHIVE_BASE_URL/$REF.tar.gz" -o "$archive_path"
  tar -xzf "$archive_path" -C "$tmp_dir"

  for candidate in "$tmp_dir"/ros-devkit-*; do
    if [[ -d "$candidate" ]]; then
      extracted="$candidate"
      break
    fi
  done

  [[ -n "$extracted" ]] || die "Downloaded archive did not contain a ros-devkit source directory."

  cp -R "$extracted/." "$target/"
  printf 'repo=%s\nref=%s\n' "$REPO_URL" "$REF" > "$target/$MARKER_FILE"
}

# Fetch source into the target directory using git or archive fallback.
acquire_source() {
  local target="$1"
  if command -v git >/dev/null 2>&1; then
    acquire_source_with_git "$target"
  else
    acquire_source_with_archive "$target"
  fi
}

# ---------------------------------------------------------------------------
# Namespace cleaning
# ---------------------------------------------------------------------------

clean_namespace() {
  local path="$1"
  find "$path" -type d -name '__pycache__' -prune -exec rm -rf {} +
  find "$path" -type f \( -name '*.pyc' -o -name '.DS_Store' \) -delete
}

# ---------------------------------------------------------------------------
# CLI wrapper generation
# ---------------------------------------------------------------------------

# write_cli_wrapper <output_path> [emit_sandbox]
#
# emit_sandbox=1 includes ROS_DEVKIT_CONFIG and ROS_DEVKIT_LOCAL_SANDBOX env
# vars in the wrapper (used by local-sandbox installs). Default is 0 (standard
# managed install wrapper without sandbox vars).
write_cli_wrapper() {
  local wrapper="$1"
  local emit_sandbox="${2:-0}"

  {
    echo '#!/usr/bin/env bash'
    echo 'set -euo pipefail'
    printf 'ROS_DEVKIT_SOURCE=%q\n' "$SOURCE_DIR"
    printf 'ROS_DEVKIT_PYTHON=%q\n' "$VENV_DIR/bin/python"
    if [[ "$emit_sandbox" -eq 1 ]]; then
      printf 'ROS_DEVKIT_CONFIG=%q\n' "$CONFIG_FILE"
      printf 'ROS_DEVKIT_LOCAL_SANDBOX=%q\n' "$local_sandbox_root"
      echo 'export ROS_DEVKIT_SOURCE ROS_DEVKIT_PYTHON ROS_DEVKIT_CONFIG ROS_DEVKIT_LOCAL_SANDBOX'
    else
      echo 'export ROS_DEVKIT_SOURCE ROS_DEVKIT_PYTHON'
    fi
    echo 'PYTHONPATH="$ROS_DEVKIT_SOURCE/src${PYTHONPATH:+:$PYTHONPATH}"'
    echo 'export PYTHONPATH'
    echo 'exec "$ROS_DEVKIT_PYTHON" -m ros_devkit.cli "$@"'
  } > "$wrapper"
  chmod +x "$wrapper"
}