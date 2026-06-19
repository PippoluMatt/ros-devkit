# ROS2 DevKit

A dual-purpose toolkit for ROS2 development: a CLI dispatcher that both AI
agents and humans can call, plus a curated collection of installable AI-agent
skills covering the ROS2 development lifecycle — from robot profiling and
package scaffolding through sensor nodes, ros2_control, MCU firmware, and
Docker deployment.

Skills target ROS2 Jazzy as the primary distro; most guidance applies to
Humble and Rolling with minor adjustments.

## How it works

The CLI is a thin dispatcher. It reads a config file to find where skills are
installed, then forwards arguments to scripts that live inside the skill
directories. The CLI contains no ROS2 logic itself — it only routes.

```
User or AI agent
      │
      ▼
ros-devkit <command> [args]
      │
      │  reads ~/.config/ros-devkit/config.env
      │  to find the configured skill root
      ▼
<skill_root>/<command>/scripts/<script>.py [args]
```

If a command fails because the skill root or a mapped script is missing, run
`ros-devkit doctor` to diagnose the configuration.

## Installation

Install with the curl bootstrap script:

```bash
curl -fsSL https://raw.githubusercontent.com/PippoluMatt/ros-devkit/main/scripts/install.sh | bash
```

The installer asks for an agent target first, then installs the CLI and the
ROS2 skills. Supported targets are `codex` (`~/.codex/skills/ros2`), `claude`
(`~/.claude/skills/ros2`), `pi` (`~/.pi/agent/skills/ros2`), and `custom`.
For `custom`, provide the parent skills directory; the installer creates its
`ros2` namespace directory beneath it.

The installer stops before changing anything if the target `ros2` namespace
already exists. It also refuses to replace an existing `~/.local/bin/ros-devkit`
unless that command already points at the installer-managed venv.

For non-interactive installs:

```bash
curl -fsSL https://raw.githubusercontent.com/PippoluMatt/ros-devkit/main/scripts/install.sh | bash -s -- --agent codex
curl -fsSL https://raw.githubusercontent.com/PippoluMatt/ros-devkit/main/scripts/install.sh | bash -s -- --agent custom --skill-root /path/to/skills
```

To install a specific Git ref:

```bash
curl -fsSL https://raw.githubusercontent.com/PippoluMatt/ros-devkit/main/scripts/install.sh | bash -s -- --agent codex --ref v0.1.0
```

## Updating

Installer-managed installs can update the CLI, managed source checkout, command
wrapper, and installed `ros2` skills from the latest `main` branch:

```bash
ros-devkit update
```

The updater stages the new source, a fresh CLI venv, and the new skill
namespace before replacing live files. It stops if the installed `ros2`
namespace has local edits compared with the previous managed source copy.

Use a dry run to fetch and validate the update without changing the live
install:

```bash
ros-devkit update --dry-run
```

Use `--force` only when you want to replace locally edited installed skills:

```bash
ros-devkit update --force
```

### Local development install

From a local checkout:

```bash
python3 -m pip install .
mkdir -p ~/.codex/skills/ros2
cp -r skills/.curated/ros2/. ~/.codex/skills/ros2/
scripts/configure_ros_devkit.sh --agent codex
```

To configure a custom namespace root directly:

```bash
scripts/configure_ros_devkit.sh --agent custom --namespace-root /path/to/skills/ros2
```

## CLI reference

| Command | Description |
| --- | --- |
| `description-scaffold` | Dispatched to skill script — scaffold, verify, or split URDF/xacro packages |
| `gazebo-simulation` | Dispatched to skill script — set up or diagnose ROS2 Gazebo simulation wiring |
| `doctor` | Built-in — check config and validate that mapped scripts exist |
| `update` | Built-in — update an installer-managed install from latest `main` |
| `--help` | Show available commands |
| `--version` | Print version |

### description-scaffold

| Mode | Description |
| --- | --- |
| `--verify [path]` | Inspect a package and report ERROR/WARN/INFO findings |
| `--create <robot_name>` | Create a new `<name>_description` package from a robot name |
| `--create [existing_path]` | Repair an existing package — add only missing files, never overwrite |
| `--split [path]` | Split a monolithic xacro file into the modular structure |

```bash
ros-devkit description-scaffold --verify
ros-devkit description-scaffold --create my_robot --sensors camera,lidar --destination-directory ~/ros2_ws/src
ros-devkit description-scaffold --split
```

### gazebo-simulation

| Mode | Description |
| --- | --- |
| `--diagnose [path]` | Inspect Gazebo xacro, physics tags, bringup launch wiring, and `config/gazebo_bridge.yaml` |
| `--setup [path]` | Add only missing Gazebo scaffold files without overwriting existing files |

```bash
ros-devkit gazebo-simulation --diagnose
ros-devkit gazebo-simulation --setup ~/ros2_ws/src --robot-name my_robot
```

### doctor

```bash
ros-devkit doctor
```

Checks that the configured skill root exists and that every mapped script is
present. Exits non-zero if any error is found.

### update

```bash
ros-devkit update
ros-devkit update --dry-run
ros-devkit update --force
```

`update` is available only for installer-managed installs. Local development
installs should be updated by pulling the checkout and reinstalling locally.

## Skill catalog

| Category | Skill | Description |
| --- | --- | --- |
| **ROS2 Packages & Nodes** | [`cpp-node`](skills/.curated/ros2/cpp-node/SKILL.md) | Shared ROS2 node design and C++ patterns |
| | [`cmakelists`](skills/.curated/ros2/cmakelists/SKILL.md) | Create and normalize ROS2 CMakeLists.txt files |
| | [`launch`](skills/.curated/ros2/launch/SKILL.md) | Create and debug ROS2 launch files |
| | [`ros2-sensor`](skills/.curated/ros2/ros2-sensor/SKILL.md) | Create and review ROS2 sensor interfaces |
| **Robot Description & Control** | [`description-scaffold`](skills/.curated/ros2/description-scaffold/SKILL.md) | Scaffold and validate ROS2 URDF/xacro description packages |
| | [`gazebo-simulation`](skills/.curated/ros2/gazebo-simulation/SKILL.md) | Set up and diagnose ROS2 Gazebo simulation wiring |
| | [`ros2-control`](skills/.curated/ros2/ros2-control/SKILL.md) | Create ROS2 control plugins and xacro |
| **MCU & Embedded** | [`mcu-freertos`](skills/.curated/ros2/mcu-freertos/SKILL.md) | Build and maintain MCU RTOS firmware |
| | [`mcu-protocol`](skills/.curated/ros2/mcu-protocol/SKILL.md) | Design MCU wire protocols for ROS2 |
| **Project & Deployment** | [`robot-profile`](skills/.curated/ros2/robot-profile/SKILL.md) | Capture ROS2 robot hardware context |
| | [`ros2-dockerfile`](skills/.curated/ros2/ros2-dockerfile/SKILL.md) | Generate a custom ROS 2 Dockerfile with optional package overlay |

Each skill contains a `SKILL.md` with full instructions, optional `references/`
for detailed guidance, and `scripts/` for deterministic generators. Skills can
load each other — for example, `cmakelists` loads `cpp-node` when build rules
depend on node interfaces.

## Repository structure

```
ros-devkit/
├── src/ros_devkit/          # CLI dispatcher package
├── skills/.curated/ros2/    # Curated skill collection (11 skills)
│   ├── cmakelists/
│   ├── cpp-node/
│   ├── description-scaffold/
│   ├── gazebo-simulation/
│   ├── launch/
│   ├── mcu-freertos/
│   ├── mcu-protocol/
│   ├── robot-profile/
│   ├── ros2-control/
│   ├── ros2-dockerfile/
│   └── ros2-sensor/
├── scripts/                 # Setup & configuration scripts
├── docs/                    # Agent documentation
├── pyproject.toml           # Python package metadata
└── LICENSE
```

## License

This project is licensed under the [MIT License](LICENSE).
