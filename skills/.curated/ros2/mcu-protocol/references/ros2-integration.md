# ROS2 Integration

Keep raw protocol handling inside the driver layer. ROS2 application nodes and controllers should see typed ROS interfaces, not frames.

## Driver Boundary

- Let one driver node or hardware interface own the transport, parser, handshake state, retries, reconnect policy, and diagnostics.
- Do not parse raw frames in launch files, controllers, or high-level application nodes.
- Keep message schemas close to the driver package docs or generated protocol spec.
- Make the driver fail closed when handshake, CRC, frame length, or version checks fail.

## Actuators And Joints

- Use `ros2_control` hardware interfaces when the MCU exposes joints, actuators, encoders, or combined robot hardware.
- Keep command serialization in the hardware interface or its private driver object.
- Map protocol timeouts and stale telemetry to `hardware_interface::return_type::ERROR` or degraded state according to package conventions.
- Do not let controllers depend on protocol message IDs or raw payload layouts.

## Sensors

- Publish standard `sensor_msgs` where possible: IMU, JointState, Range, LaserScan, PointCloud2, BatteryState, Temperature, FluidPressure, or NavSatFix as appropriate.
- Use `rclcpp::SensorDataQoS` or package conventions for high-rate sensor streams.
- Preserve timestamps carefully: distinguish MCU sample time, host receive time, and ROS publish time when it matters.
- Keep unit conversion and integer scaling inside the driver.

## Diagnostics And Parameters

Expose diagnostics for:

- link state and handshake state
- firmware/protocol version
- CRC failures
- parser resync count
- timeout/retry count
- dropped or unknown frames
- heartbeat age
- reconnect count

Expose parameters for:

- port, baud rate, bus address, CAN interface, or device selector
- read/write timeout
- heartbeat timeout
- max frame length
- retry count
- diagnostics rate

## Testing

- Unit test frame encode/decode without ROS2 where possible.
- Add driver tests for handshake success/failure, timeout, reconnect, and invalid frames.
- Use ROS2 diagnostics or logs to verify failure modes during hardware bringup.
