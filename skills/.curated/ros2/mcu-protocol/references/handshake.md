# Handshake

Use a handshake to prevent silent host/firmware mismatch before normal traffic starts.

## Default Sequence

1. Host opens the transport and waits for the MCU to be ready, or sends `HELLO` after a conservative startup delay.
2. Host sends `HELLO` with supported protocol version range and desired feature bits.
3. MCU responds with firmware ID/version, selected protocol version, capabilities bitmask, max frame size, reset reason if available, and transport limits if relevant.
4. Host refuses normal operation if the selected protocol version or required capabilities are incompatible.
5. Host starts heartbeat/watchdog policy after successful handshake.

Repeat the handshake after reconnect, MCU reset, host parser resync that discards state, or protocol error severe enough to invalidate assumptions.

## Versioning

- Use a protocol version distinct from firmware version.
- Require host and MCU to agree on exactly one protocol version for the session.
- Treat incompatible major protocol versions as a hard failure.
- Allow minor feature additions only when capability bits or message availability make behavior explicit.
- Keep reserved fields zeroed and verify they are ignored or rejected according to the spec.

## Heartbeat And Reset

- Use heartbeat to detect dead links, wedged parsers, and unexpected MCU reset.
- Include uptime, boot count, or reset reason when available.
- On heartbeat timeout, mark the driver degraded, stop sending non-idempotent commands, close/reopen transport if appropriate, and repeat handshake.
- Do not treat heartbeat as a safety mechanism by itself; pair it with actuator watchdog behavior where needed.

## Failure Handling

- Expose handshake failure reason in logs and diagnostics.
- Bound handshake attempts and retry intervals.
- Keep normal traffic disabled until handshake succeeds.
- Avoid accepting telemetry from an unknown or incompatible protocol version.
