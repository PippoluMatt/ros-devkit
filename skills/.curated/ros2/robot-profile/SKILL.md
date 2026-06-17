---
name: robot-profile
description: Interview the user about robot hardware and ROS2-relevant physical context, then create or update ROBOTS.md. Use when the user wants to document a robot, update robot characteristics, define robot type, geometry, sensors, dimensions, motors, MCU, control interfaces, frames, power, or other details that affect ROS2 packages, launch files, URDF, ros2_control, navigation, localization, or sensor integration.
---

# Robot Profile

Use this skill to grill the user for compact, ROS2-first robot facts and keep them in `ROBOTS.md`.

## Start

1. State that `ROBOTS.md` is the source of robot context and read its current contents before asking update questions. If it does not exist, say that it will be created.
2. Ask the user to list the robot or changes they want to document.
3. Query the user about the listed topics plus any missing prerequisites needed to make the robot usable in ROS2.
4. Ask one question at a time, waiting for the answer before continuing.
5. Provide a recommended answer format with each question.

If a question can be answered from files in the workspace, inspect the files instead of asking.

## Grill Order

Walk the dependency tree. Do not dump all questions at once.

1. ROS2: distro, packages, launch, URDF/xacro, TF frames, topics, QoS, ros2_control/Nav2/localization status and blockers.
2. Identity: name, version, purpose, environment.
3. MCU: board, IDE/toolchain, connected devices, firmware stack, timing, protocol, watchdog/failsafe.
4. SBC: board, OS, runtime environment, connected devices, permissions/services, non-ROS dependencies.
5. Body: robot type, kinematics, steering model, dimensions, mass/footprint if relevant.
6. Actuation: drive, steering, manipulators, motors, drivers, gearing, encoders, limits, calibration.
7. Sensors: type/model, host/bus, frame, mounting pose, message type/topic, update rate/QoS, calibration.
8. Power: battery chemistry, nominal voltage, capacity, regulators, power domains, emergency stop.

## Minimum Before Writing

Continue until the profile is adequate for the stated ROS2 task. If the user does not know a required value, record `TBD` and ask the next blocking question.

For any mobile base, ask or discover at least:

- Type/kinematics/dimensions.
- Motors, drivers, gearing, steering limits, encoder/odometry source, calibration method.
- MCU/SBC roles, runtime environments, and firmware stack.
- Power source, nominal voltage, regulators, e-stop or safety cutoff.
- Command/telemetry protocol between ROS2 compute and MCU, including transport, baud/rate, fields, units, and update rate.
- Sensors needed for navigation/localization, including model, interface, frame, rate, and calibration status.
- ROS2 packages, topics, frames, URDF, ros2_control/Nav2/localization status.

For a sensor-only update, ask model, host, bus/protocol, frame, mounting pose, message type, rate, QoS, and calibration.

For an MCU/firmware update, ask board, firmware stack, connected devices, bus/protocol, timing, packet format, units, rates, watchdog/failsafe, and ROS2 bridge.

## Updating ROBOTS.md

Keep `ROBOTS.md` token-efficient: terse bullets, no prose paragraphs, no nested bullets unless needed for multiple sensors, protocols, or actuator subsystems. Preserve existing robot entries unless the user asks to replace them.

Organize each robot by concept, with `ROS2` first. Keep ROS2 graph details only under `ROS2`; keep host/runtime facts under `SBC`; keep MCU wiring and firmware facts under `MCU`. Keep device facts under their concept sections (`Actuation`, `Sensors`) and reference host/bus or MCU connections there as needed.

When updating an existing flat entry, migrate only the robot entry being edited into the concept-section format. Preserve unrelated robot entries exactly.

Use this shape unless the existing file has a better local format:

```markdown
# ROBOTS.md

## <Robot Name>

### ROS2

- Distro:
- Workspace/packages:
- Launch:
- Topics:
- Frames/TF:
- URDF/xacro:
- ros2_control:
- Navigation/localization:
- Status/blockers:

### Identity

- Purpose:
- Environment:
- Version/status:

### MCU

#### Hardware

- Board:
- IDE/toolchain:
- Connections:

#### Firmware

- Stack/libraries:
- Timing/rates:
- Watchdog/failsafe:

#### Protocol

- Transport:
- Framing/fields/units:
- Command/telemetry rates:
- Failure behavior:

### SBC

#### Hardware

- Board:
- CPU/RAM/storage:
- Network:
- Connected devices:

#### Software

- OS:
- ROS2 install:
- Device permissions/services:
- Non-ROS dependencies:

### Body

- Type/kinematics:
- Dimensions/footprint:
- Mass:

### Actuation

- Motors/actuators:
- Drivers:
- Gearing:
- Encoders/odometry:
- Limits/calibration:

### Sensors

#### <Sensor Type> - <Model>

- Host/bus:
- Mount/frame:
- ROS2 msg/topic:
- Rate/QoS:
- Calibration/status:

### Power

- Battery/source:
- Voltage/capacity:
- Regulators/rails:
- Power domains:
- E-stop/safety cutoff:
- Runtime/status:

### Open Questions
```

Group `Sensors` by sensor type/model, with host/bus and ROS2 topic as fields. Group `Actuation` by subsystem (`Drive`, `Steering`, `Manipulator`) when there is more than one actuator class; otherwise use the compact field list.

After writing `ROBOTS.md`, summarize only what changed and the remaining ROS2-blocking questions.

## Guardrails

- Do not invent hardware facts. Infer only when source files prove them, and label inferences.
- Do not ask for all robot details at once.
- Do not overwrite existing `ROBOTS.md` sections unrelated to the current update.
- Do not document implementation plans in `ROBOTS.md`; keep it to robot facts, ROS2-relevant constraints, and open questions.
- Do not write a verbose profile when a compact field list carries the same information.
