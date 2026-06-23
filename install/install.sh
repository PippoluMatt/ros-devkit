#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${ROS_DEVKIT_REPO_URL:-https://github.com/PippoluMatt/ros-devkit.git}"
ARCHIVE_BASE_URL="${ROS_DEVKIT_ARCHIVE_BASE_URL:-https://github.com/PippoluMatt/ros-devkit/archive}"
DEFAULT_REF="main"
NAMESPACE="ros2"
MARKER_FILE=".ros-devkit-source"
LOCAL_SANDBOX_MARKER=".ros-devkit-local-sandbox"

INSTALL_HOME="${ROS_DEVKIT_INSTALL_HOME:-$HOME/.local/share/ros-devkit}"
SOURCE_DIR="$INSTALL_HOME/source"
VENV_DIR="$INSTALL_HOME/venv"
BIN_DIR="${ROS_DEVKIT_BIN_DIR:-$HOME/.local/bin}"
BIN_PATH="$BIN_DIR/ros-devkit"
MANAGED_BIN_TARGET="$VENV_DIR/bin/ros-devkit"
CONFIG_FILE=""

agent=""
agent_skill_root=""
agent_skill_root_supplied=0
agent_supplied=0
REF="$DEFAULT_REF"
ref_supplied=0
interactive=0
local_sandbox=0
local_sandbox_root=""
temp_paths=()

# ---------------------------------------------------------------------------
# Source shared library
# ---------------------------------------------------------------------------

_source_common() {
  local script_dir
  local lib_path

  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || script_dir=""
  lib_path="$script_dir/lib/install_common.sh"

  if [[ -f "$lib_path" ]]; then
    source "$lib_path"
    return 0
  fi

  # Running from pipe (curl | bash); fetch library from remote.
  local lib_url="${REPO_URL%.git}/raw/${DEFAULT_REF}/install/lib/install_common.sh"
  local lib_temp
  lib_temp="$(mktemp "${TMPDIR:-/tmp}/ros-devkit-common.XXXXXX")"
  temp_paths+=("$lib_temp")

  if ! curl -fsSL "$lib_url" -o "$lib_temp" 2>/dev/null; then
    printf 'ERROR: Failed to download shared library from %s\n' "$lib_url" >&2
    rm -f "$lib_temp"
    exit 1
  fi
  source "$lib_temp"
}

_source_common
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Install-specific functions
# ---------------------------------------------------------------------------

usage() {
  cat <<'EOF'
usage: install/install.sh [--agent codex|claude|pi|custom] [--skill-root PATH] [--ref REF]
       install/install.sh --local-sandbox PATH

Install ros-devkit for an AI agent target.

Options:
  --agent          Agent target. Interactive installs ask when omitted.
  --skill-root     Parent agent skill root for --agent custom; installer creates PATH/ros2.
  --ref            Git branch, tag, or ref to install. Defaults to main.
  --local-sandbox  Install a disposable, isolated sandbox from this checkout snapshot.
  -h, --help       Show this help.

Examples:
  install/install.sh
  install/install.sh --agent codex
  install/install.sh --agent claude
  install/install.sh --agent pi
  install/install.sh --agent custom --skill-root ~/.config/my-agent/skills
  install/install.sh --local-sandbox .dev-install
EOF
}

absolute_path() {
  local path
  path="$(expand_path "$1")"
  case "$path" in
    /*)
      printf '%s\n' "$path"
      ;;
    *)
      printf '%s\n' "$PWD/$path"
      ;;
  esac
}

checkout_root() {
  local script_path
  local script_dir

  script_path="${BASH_SOURCE[0]}"
  if [[ ! -f "$script_path" ]]; then
    die "--local-sandbox requires running install/install.sh from a local checkout."
  fi

  script_dir="$(cd "$(dirname "$script_path")" && pwd)"
  cd "$script_dir/.." && pwd
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --agent)
        [[ $# -ge 2 ]] || die "--agent requires a value"
        agent="$2"
        agent_supplied=1
        shift 2
        ;;
      --skill-root)
        [[ $# -ge 2 ]] || die "--skill-root requires a value"
        agent_skill_root="$2"
        agent_skill_root_supplied=1
        shift 2
        ;;
      --ref)
        [[ $# -ge 2 ]] || die "--ref requires a value"
        REF="$2"
        ref_supplied=1
        shift 2
        ;;
      --local-sandbox)
        [[ $# -ge 2 ]] || die "--local-sandbox requires a value"
        local_sandbox=1
        local_sandbox_root="$2"
        shift 2
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

configure_local_sandbox() {
  if [[ "$local_sandbox" -eq 0 ]]; then
    return
  fi

  if [[ "$agent_supplied" -eq 1 || "$agent_skill_root_supplied" -eq 1 || "$ref_supplied" -eq 1 ]]; then
    die "--local-sandbox cannot be combined with --agent, --skill-root, or --ref"
  fi

  local_sandbox_root="$(absolute_path "$local_sandbox_root")"
  if [[ "$local_sandbox_root" == "/" ]]; then
    die "--local-sandbox cannot use / as the sandbox root"
  fi

  local checkout
  checkout="$(checkout_root)"
  if [[ "$local_sandbox_root" == "$checkout" ]]; then
    die "--local-sandbox cannot use the checkout root"
  fi

  agent="custom"
  agent_skill_root="$local_sandbox_root/skills"
  namespace_root="$agent_skill_root/$NAMESPACE"
  INSTALL_HOME="$local_sandbox_root/share/ros-devkit"
  SOURCE_DIR="$INSTALL_HOME/source"
  VENV_DIR="$INSTALL_HOME/venv"
  BIN_DIR="$local_sandbox_root/bin"
  BIN_PATH="$BIN_DIR/ros-devkit"
  MANAGED_BIN_TARGET="$VENV_DIR/bin/ros-devkit"
  CONFIG_FILE="$local_sandbox_root/config/ros-devkit/config.env"
  REF="local-sandbox"
}

select_agent() {
  if [[ -z "$agent" ]]; then
    interactive=1
    if [[ ! -r /dev/tty || ! -w /dev/tty ]]; then
      die "Interactive install requires a TTY. Pass --agent codex|claude|pi, or --agent custom --skill-root PATH."
    fi

    print_agent_menu /dev/tty
    agent="$(prompt_tty "Agent [codex/claude/pi/custom]: ")"
  fi

  normalize_agent
}

resolve_skill_root() {
  if [[ "$agent" != "custom" && "$agent_skill_root_supplied" -eq 1 ]]; then
    die "--skill-root is only supported with --agent custom"
  fi

  if [[ "$agent" != "custom" ]]; then
    agent_skill_root="$(agent_skill_root_for "$agent")"
  else
    if [[ -z "$agent_skill_root" ]]; then
      if [[ "$interactive" -eq 1 ]]; then
        agent_skill_root="$(prompt_tty "Custom parent skills directory: ")"
      else
        die "--agent custom requires --skill-root PATH"
      fi
    fi
  fi

  agent_skill_root="$(expand_path "$agent_skill_root")"
  namespace_root="$agent_skill_root/$NAMESPACE"
}

remote_is_ros_devkit() {
  case "$1" in
    "$REPO_URL"|https://github.com/PippoluMatt/ros-devkit|https://github.com/PippoluMatt/ros-devkit.git|git@github.com:PippoluMatt/ros-devkit.git)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

preflight_paths() {
  if [[ -e "$namespace_root" ]]; then
    die "Namespace root already exists: $namespace_root"
  fi

  if [[ -e "$INSTALL_HOME" && ! -d "$INSTALL_HOME" ]]; then
    die "Install home exists but is not a directory: $INSTALL_HOME"
  fi

  if [[ -e "$VENV_DIR" && ! -d "$VENV_DIR" ]]; then
    die "Managed venv path exists but is not a directory: $VENV_DIR"
  fi

  if [[ -e "$BIN_DIR" && ! -d "$BIN_DIR" ]]; then
    die "Bin directory exists but is not a directory: $BIN_DIR"
  fi

  if [[ -e "$agent_skill_root" && ! -d "$agent_skill_root" ]]; then
    die "Agent skill root exists but is not a directory: $agent_skill_root"
  fi

  if [[ -e "$BIN_PATH" || -L "$BIN_PATH" ]]; then
    if [[ -L "$BIN_PATH" ]]; then
      local target
      target="$(readlink "$BIN_PATH")"
      if [[ "$target" != "$MANAGED_BIN_TARGET" ]]; then
        die "Existing ros-devkit command is not managed by this installer: $BIN_PATH -> $target"
      fi
    else
      die "Existing ros-devkit command is not managed by this installer: $BIN_PATH"
    fi
  fi

  if [[ -e "$SOURCE_DIR" ]]; then
    if [[ ! -d "$SOURCE_DIR" ]]; then
      die "Source path exists but is not a directory: $SOURCE_DIR"
    fi

    if [[ -f "$SOURCE_DIR/$MARKER_FILE" ]]; then
      return
    fi

    if [[ -d "$SOURCE_DIR/.git" && -x "$(command -v git || true)" ]]; then
      local remote
      remote="$(git -C "$SOURCE_DIR" config --get remote.origin.url || true)"
      if remote_is_ros_devkit "$remote"; then
        return
      fi
    fi

    die "Source path exists but does not look like a managed ros-devkit checkout: $SOURCE_DIR"
  fi
}

preflight_commands() {
  need_command python3
  need_command mkdir
  need_command cp
  need_command ln
  need_command find
  need_command chmod
  need_command rm
  need_command mv
  need_command mktemp

  if [[ "$local_sandbox" -eq 0 ]]; then
    need_command readlink
    if ! command -v git >/dev/null 2>&1; then
      need_command curl
      need_command tar
    fi
  fi
}

preflight_sandbox_paths() {
  if [[ -L "$local_sandbox_root" ]]; then
    die "Local sandbox root cannot be a symlink: $local_sandbox_root"
  fi

  if [[ -e "$local_sandbox_root" ]]; then
    if [[ ! -d "$local_sandbox_root" ]]; then
      die "Local sandbox root exists but is not a directory: $local_sandbox_root"
    fi

    if [[ ! -f "$local_sandbox_root/$LOCAL_SANDBOX_MARKER" ]]; then
      die "Local sandbox root already exists without $LOCAL_SANDBOX_MARKER: $local_sandbox_root"
    fi

    log "Removing existing local sandbox: $local_sandbox_root"
    rm -rf "$local_sandbox_root"
  fi
}

preflight_python() {
  local tmp_venv
  tmp_venv="$(mktemp -d "${TMPDIR:-/tmp}/ros-devkit-venv.XXXXXX")"
  temp_paths+=("$tmp_venv")

  if ! python3 -m venv "$tmp_venv" >/dev/null 2>&1; then
    die "python3 venv support is missing. Install the platform package for python3-venv."
  fi

  if [[ ! -x "$tmp_venv/bin/python" ]]; then
    die "python3 venv did not create an executable Python interpreter."
  fi
}

print_plan() {
  if [[ "$local_sandbox" -eq 1 ]]; then
    cat <<EOF
Install ros-devkit local sandbox
  Sandbox root     : $local_sandbox_root
  Agent target     : $agent
  Agent skill root : $agent_skill_root
  Namespace root   : $namespace_root
  Source snapshot  : $SOURCE_DIR
  CLI venv         : $VENV_DIR
  CLI command      : $BIN_PATH
  Config file      : $CONFIG_FILE
EOF
    return
  fi

  cat <<EOF
Install ros-devkit
  Agent target     : $agent
  Agent skill root : $agent_skill_root
  Namespace root   : $namespace_root
  Source checkout  : $SOURCE_DIR
  CLI venv         : $VENV_DIR
  CLI command      : $BIN_PATH
  Git ref          : $REF
EOF
}

confirm_interactive() {
  if [[ "$interactive" -ne 1 ]]; then
    return
  fi

  print_plan > /dev/tty
  local answer
  answer="$(prompt_tty "Proceed with installation? [y/N] ")"
  case "$answer" in
    y|Y|yes|YES)
      ;;
    *)
      log "Installation cancelled."
      exit 0
      ;;
  esac
}

acquire_source_from_checkout() {
  local checkout
  local tmp_source

  checkout="$(checkout_root)"
  if [[ ! -d "$checkout/skills/.curated/$NAMESPACE" ]]; then
    die "Local checkout is missing skills/.curated/$NAMESPACE: $checkout"
  fi

  if [[ ! -f "$checkout/pyproject.toml" ]]; then
    die "Local checkout is missing pyproject.toml: $checkout"
  fi

  tmp_source="$(mktemp -d "${TMPDIR:-/tmp}/ros-devkit-source.XXXXXX")"
  temp_paths+=("$tmp_source")

  log "Copying local checkout snapshot..."
  cp -R "$checkout/." "$tmp_source/"
  rm -rf \
    "$tmp_source/.git" \
    "$tmp_source/.venv" \
    "$tmp_source/.pytest_cache" \
    "$tmp_source/build" \
    "$tmp_source/log"
  find "$tmp_source" -type d -name '__pycache__' -prune -exec rm -rf {} +
  find "$tmp_source" -type f -name '*.pyc' -delete

  printf 'repo=local-sandbox\nsource=%s\n' "$checkout" > "$tmp_source/$MARKER_FILE"

  mkdir -p "$INSTALL_HOME"
  printf 'source=%s\n' "$checkout" > "$local_sandbox_root/$LOCAL_SANDBOX_MARKER"
  if [[ -e "$SOURCE_DIR" ]]; then
    rm -rf "$SOURCE_DIR"
  fi
  mv "$tmp_source" "$SOURCE_DIR"
}

install_cli() {
  log "Installing ros-devkit CLI..."
  python3 -m venv "$VENV_DIR"
  write_cli_wrapper "$MANAGED_BIN_TARGET" "$local_sandbox"

  mkdir -p "$BIN_DIR"
  ln -sfn "$MANAGED_BIN_TARGET" "$BIN_PATH"
}

install_skills() {
  local source_namespace="$SOURCE_DIR/skills/.curated/$NAMESPACE"
  local tmp_namespace

  log "Installing $NAMESPACE skills..."
  mkdir -p "$agent_skill_root"
  tmp_namespace="$(mktemp -d "$agent_skill_root/.${NAMESPACE}.install.XXXXXX")"
  temp_paths+=("$tmp_namespace")

  cp -R "$source_namespace/." "$tmp_namespace/"
  clean_namespace "$tmp_namespace"

  if [[ -e "$namespace_root" ]]; then
    die "Namespace root appeared during install: $namespace_root"
  fi

  mv "$tmp_namespace" "$namespace_root"
}

configure_cli() {
  log "Configuring ros-devkit..."
  if [[ "$local_sandbox" -eq 1 ]]; then
    XDG_CONFIG_HOME="$local_sandbox_root/config" "$SOURCE_DIR/install/configure_ros_devkit.sh" --agent "$agent" --namespace-root "$namespace_root"
  else
    "$SOURCE_DIR/install/configure_ros_devkit.sh" --agent "$agent" --namespace-root "$namespace_root"
  fi
}

run_doctor() {
  log "Running ros-devkit doctor..."
  "$BIN_PATH" doctor
}

warn_path() {
  if [[ "$local_sandbox" -eq 1 ]]; then
    printf 'Run the sandbox command directly with:\n'
    printf '  %s doctor\n' "$BIN_PATH"
    printf 'Or put it first on PATH for this shell:\n'
    printf '  export PATH="%s:$PATH"\n' "$BIN_DIR"
    return
  fi

  case ":$PATH:" in
    *":$BIN_DIR:"*)
      ;;
    *)
      printf 'WARNING: %s is not on PATH.\n' "$BIN_DIR" >&2
      printf 'Run this command now, or add it to your shell profile:\n' >&2
      printf '  export PATH="%s:$PATH"\n' "$BIN_DIR" >&2
      printf 'Until then, run ros-devkit directly with:\n' >&2
      printf '  %s doctor\n' "$BIN_PATH" >&2
      ;;
  esac
}

main() {
  parse_args "$@"
  configure_local_sandbox
  if [[ "$local_sandbox" -eq 0 ]]; then
    select_agent
    resolve_skill_root
  fi
  preflight_commands
  if [[ "$local_sandbox" -eq 1 ]]; then
    preflight_sandbox_paths
  else
    preflight_paths
  fi
  preflight_python
  confirm_interactive
  if [[ "$local_sandbox" -eq 1 ]]; then
    print_plan
    acquire_source_from_checkout
  else
    print_plan
    local tmp_source
    tmp_source="$(mktemp -d "${TMPDIR:-/tmp}/ros-devkit-source.XXXXXX")"
    temp_paths+=("$tmp_source")
    acquire_source "$tmp_source"
    if [[ ! -d "$tmp_source/skills/.curated/$NAMESPACE" ]]; then
      die "Fetched source is missing skills/.curated/$NAMESPACE"
    fi
    if [[ ! -f "$tmp_source/pyproject.toml" ]]; then
      die "Fetched source is missing pyproject.toml"
    fi
    mkdir -p "$INSTALL_HOME"
    if [[ -e "$SOURCE_DIR" ]]; then
      rm -rf "$SOURCE_DIR"
    fi
    mv "$tmp_source" "$SOURCE_DIR"
  fi
  install_cli
  install_skills
  configure_cli
  run_doctor
  warn_path

  log "Installed ros-devkit."
}

main "$@"