---
name: mcu-protocol
description: Design, review, and implement MCU host/firmware communication contracts for ROS2 robots. Use when working on handshakes, binary frame formats, CRC/checksum choices, UART, USB CDC, I2C, SPI, CAN, ACK/NACK, retries, timeouts, resync, message IDs, payload schemas, protocol documentation, or driver-layer ROS2 integration. Do not use for RTOS task scheduling, queues, semaphores, timers, heap, or MCU runtime architecture unless protocol communication is the main issue.
---

# MCU Protocol

Use this skill to help design or maintain the wire contract between an MCU firmware image and a ROS2 host driver.

Keep this skill focused on protocol behavior and driver boundaries. Use `mcu-freertos` for task scheduling, queues, semaphores, timers, heap, and RTOS runtime design.

## Questionnaire

Ask 3 to 5 questions before changing code or protocol docs unless the user already gave enough context:

1. Which MCU, host language/package, and transport are in use: UART, USB CDC, I2C, SPI, CAN, or something else?
2. Is the link command/response, telemetry-only, bidirectional streaming, or mixed?
3. What are the frame size, latency, reliability, memory, and CPU constraints?
4. What already exists: frame layout, message ID table, CRC parameters, handshake, parser, transport driver, or protocol spec?
5. Which ROS2 boundary should own the protocol: a driver node, `ros2_control` hardware interface, or sensor package?

After the answers, restate the assumptions and choose the smallest relevant reference set.

## Workflow

1. Identify the transport model, frame boundaries, MCU limits, host driver boundary, and failure modes.
2. Define or inspect the handshake before normal traffic. Require version/capability negotiation for any non-trivial link.
3. Define or inspect the frame format: sync, version, type, sequence, length, payload, checksum/CRC, byte order, and resync behavior.
4. Define message IDs, payload schemas, units, scaling, status/error codes, and timeout/retry rules.
5. Keep protocol parsing and retries inside the driver layer. Higher-level ROS2 nodes, controllers, launch files, and application code should not parse raw frames.
6. Create or update a compact protocol spec when protocol behavior changes.
7. Verify with parser tests, golden frame vectors, corrupted-frame tests, timeout tests, reconnect tests, and ROS2 diagnostics when available.

## Small MCU Default

Use this default for small MCU UART, USB CDC, or SPI stream-style links unless project constraints point elsewhere:

```text
SYNC:     2 bytes, fixed magic
VERSION:  1 byte protocol version
TYPE:     1 byte message type
SEQ:      1 byte sequence number
LEN:      2 bytes payload length, little-endian
PAYLOAD:  N bytes
CRC:      1 byte CRC-8 over VERSION..PAYLOAD
```

Default resync strategy: scan for `SYNC`, validate `LEN`, reject frames with bad CRC, and continue scanning. Reconsider the default for I2C, CAN, very tight MCUs, large payloads, noisy links, or safety-relevant commands.

Default ACK policy: use explicit ACK/NACK for command/response traffic only. Do not ACK every high-rate telemetry frame.

## Protocol Spec

Create or update a compact spec such as `docs/protocol.md` when no existing protocol document exists. Include:

- frame layout
- byte order
- CRC/checksum parameters and test vector
- message ID table
- per-message payload schema
- handshake sequence
- timeout/retry rules
- transport assumptions
- error/status code table
- compatibility/versioning rules

## Load References

Load only the references needed for the user request:

- Handshake and versioning: [references/handshake.md](references/handshake.md)
- Binary frames, CRC, payload schemas, and resync: [references/binary-frames.md](references/binary-frames.md)
- UART, USB CDC, I2C, SPI, and CAN transport constraints: [references/transports.md](references/transports.md)
- ROS2 driver boundaries and diagnostics: [references/ros2-integration.md](references/ros2-integration.md)

## Guardrails

- Do not use JSON by default for tight MCU links when binary framing is required for latency, memory, or CPU budget.
- Do not dump C structs as the wire format unless packing, alignment, endian, compiler, and golden-vector tests are explicit.
- Do not present CRC, sequence numbers, or handshake as authentication, authorization, confidentiality, or tamper resistance.
- Do not hide protocol behavior in launch files, controllers, or application nodes.
