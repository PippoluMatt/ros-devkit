# Binary Frames

Prefer explicit field-by-field serialization for small MCU links. Specify every byte of the frame contract.

## Small MCU Frame

Use this frame for UART, USB CDC, or SPI stream-style links when no better project-specific contract exists:

```text
SYNC:     2 bytes, fixed magic
VERSION:  1 byte protocol version
TYPE:     1 byte message type
SEQ:      1 byte sequence number
LEN:      2 bytes payload length, little-endian
PAYLOAD:  N bytes
CRC:      1 byte CRC-8 over VERSION..PAYLOAD
```

Scan for `SYNC`, validate `LEN` against a configured maximum, compute CRC, accept valid frames, and continue scanning after invalid frames.

## CRC And Checksums

- Use CRC-8 for compact, low-risk control/status frames when payloads are typically under about 64 bytes.
- Prefer CRC-16/CCITT or CRC-16/IBM for larger payloads, noisy links, safety-relevant commands, or retry behavior that depends strongly on corruption detection.
- Always specify polynomial, initial value, final XOR, reflection settings, covered bytes, and at least one test vector.
- Treat CRC as corruption detection only, not authentication.

## Payload Schemas

- Use fixed-size little-endian fields by default, and state byte order in the spec.
- Prefer field-by-field serialization/deserialization over C struct dumps.
- Use integer scaling for physical units when practical: millivolts, milliamps, millimeters, milliradians, millimeters per second.
- Avoid floats on the wire unless precision/range and MCU FPU cost are acceptable.
- Include a per-message schema table: field name, type, unit, scale, range, and default/error behavior.
- Include at least one golden frame vector per important message type.

## Message IDs

- Keep command, response, telemetry, and error/status ID ranges clear.
- Require status/error responses for configuration writes and mode changes.
- Reserve IDs only when there is a near-term compatibility reason.
- Document whether unknown message IDs are ignored, NACKed, or treated as protocol errors.

## ACK, NACK, And Retry

- Use `SEQ` for command/response matching.
- Commands should receive a response or ACK/NACK, with timeout and bounded retry count.
- Detect duplicate commands by repeated `SEQ` when retrying non-idempotent operations.
- Telemetry should not be ACKed per frame unless the rate is low and loss is unacceptable.
- Emergency stop and safety commands must not rely only on retry; define watchdog/fail-safe behavior separately.

## Parser Tests

Verify parser behavior with:

- valid golden frames
- bad CRC
- bad length
- unknown message type
- partial frame reads
- extra bytes before sync
- sync bytes inside payload
- back-to-back frames
- maximum-length payload
- timeout mid-frame
