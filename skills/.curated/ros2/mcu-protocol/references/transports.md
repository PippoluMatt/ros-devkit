# Transports

Start with the transport's real boundary model before choosing a frame format. UART and USB CDC are stream-like; I2C, SPI, and CAN have stronger transaction or packet constraints.

## UART

- Treat UART as a byte stream with partial reads, dropped bytes, and arbitrary chunking.
- Use sync bytes, length, CRC, and resync scanning.
- Configure baud rate, read timeout, write timeout, and max frame length explicitly.
- Account for startup banners, line noise during reset, and MCU reboot while the host port stays open.

## USB CDC

- Treat USB CDC similarly to UART at the protocol layer, but expect disconnect/reconnect events.
- Re-run handshake after device reconnect or serial number/path changes.
- Avoid assuming host write completion means MCU application processed the frame.
- Expose port, VID/PID or device path selection, and reconnect policy as driver configuration.

## I2C

- Do not assume stream framing. Model traffic as controller/peripheral transactions.
- Prefer bounded request/response registers or mailbox-style reads and writes.
- Keep transactions short enough for MCU interrupt and clock-stretching limits.
- Define what the host reads when no response is ready.
- Consider CRC only over application payload if the application needs corruption detection beyond bus behavior.

## SPI

- Treat chip select as a transaction boundary unless the hardware design says otherwise.
- Account for full-duplex dummy bytes and the MCU not being ready when the host clocks data.
- Use a ready/IRQ line or status polling when response timing matters.
- Define maximum transaction length, padding bytes, and behavior after aborted chip-select windows.
- Use framing if multiple logical messages can cross transaction boundaries.

## CAN

- Use CAN message IDs deliberately: node identity, message type, priority, and direction must not collide.
- Classical CAN has small payloads; CAN FD changes the payload budget but not the need for versioning and schema discipline.
- Do not add an application CRC just because CAN already has a bus CRC; add it only when end-to-end detection is needed across gateways or reassembly.
- Use sequence counters when loss/reordering detection matters.
- Define multi-frame segmentation only when payloads cannot fit a single CAN/CAN FD frame.

## Choosing A Transport

- Prefer UART/USB CDC for simple development and debug visibility.
- Prefer I2C/SPI when the MCU is a board-local peripheral with clear controller ownership.
- Prefer CAN when multiple nodes, bus arbitration, electrical robustness, or distributed control matter.
- Let hardware topology and timing constraints drive the choice before protocol aesthetics.
