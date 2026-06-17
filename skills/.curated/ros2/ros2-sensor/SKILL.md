---
name: ros2-sensor
description: Create, edit, and review ROS2 C++ sensor nodes and sensor interfaces using standard sensor_msgs message types, conventional ROS topic names, REP-2003-aware QoS guidance, and rclcpp::SensorDataQoS. Use when working on lidar, camera, IMU, GPS, depth, point cloud, range, temperature, pressure, or other sensor publishers/subscribers in C++.
---

# ROS2 Sensor

Use this skill to create or review C++ ROS2 sensor code that follows common ROS interfaces instead of inventing custom topics or messages.

## Workflow

1. Identify the sensor kind and whether the node is a driver/source, a first-stage consumer, or a later processing stage.
2. Prefer the standard `sensor_msgs` message and conventional topic name before creating custom interfaces.
3. For 2D lidar, IMU, or GPS code creation, edits, or reviews, load the matching first-class reference below before deciding field semantics.
4. Use `rclcpp::SensorDataQoS{}` for sensor data subscriptions and for publishers when the user explicitly requests SensorDataQoS interoperability.
5. If implementing a strict REP-2003 sensor driver publisher, note that REP-2003 currently specifies `SystemDefaultsQoS` for sensor data providers and `SensorDataQoS` for consumers; follow the user's requested policy only after surfacing that distinction.
6. Populate `std_msgs/Header` fields on stamped sensor messages: `header.stamp` from the valid device/acquisition timestamp and `header.frame_id` as the physical sensor frame.
7. Keep units and coordinate frames consistent with ROS conventions: SI units, right-handed frames, optical frames for cameras, antenna frames for GNSS, and stable TF frame names.
8. Keep calibration, covariance, status, synchronization, and filtering behavior explicit when they affect downstream interpretation.
9. Load the `ros2-cpp-node` shared node module for node responsibility, graph interface, lifecycle/API, and C++ implementation details. Load the `ros2-cmakelists` skill when build files need edits.

## First-Class References

Load these concise references whenever creating, editing, or reviewing the matching modality:

- 2D lidar: [references/2d-lidar.md](references/2d-lidar.md)
- IMU: [references/imu.md](references/imu.md)
- GPS/GNSS: [references/gps.md](references/gps.md)

## Standard Interfaces

Prefer these defaults unless the package or device documentation already establishes a different standard:

| Sensor | Topic | Message |
| --- | --- | --- |
| 2D lidar | `/scan` | `sensor_msgs::msg::LaserScan` |
| 3D lidar/depth cloud | `/points` | `sensor_msgs::msg::PointCloud2` |
| Camera image | `/image_raw` | `sensor_msgs::msg::Image` |
| Camera calibration | `/camera_info` | `sensor_msgs::msg::CameraInfo` |
| IMU | `/imu/data` | `sensor_msgs::msg::Imu` |
| Magnetometer | `/imu/mag` | `sensor_msgs::msg::MagneticField` |
| GPS fix | `/fix` | `sensor_msgs::msg::NavSatFix` |
| Range finder | `/range` | `sensor_msgs::msg::Range` |
| Temperature | `/temperature` | `sensor_msgs::msg::Temperature` |
| Fluid pressure | `/fluid_pressure` | `sensor_msgs::msg::FluidPressure` |

Use relative topic names inside reusable nodes (`"scan"`, `"image_raw"`) unless the user asks for absolute graph names; let launch namespaces place them under a robot or sensor namespace.

## QoS Pattern

Use the rclcpp QoS helper directly:

```cpp
auto scan_pub = create_publisher<sensor_msgs::msg::LaserScan>(
  "scan",
  rclcpp::SensorDataQoS{});

auto scan_sub = create_subscription<sensor_msgs::msg::LaserScan>(
  "scan",
  rclcpp::SensorDataQoS{},
  std::bind(&NodeName::scan_callback, this, std::placeholders::_1));
```

Do not replace this with raw `rmw_qos_profile_sensor_data` unless integrating with an API that requires an RMW profile. Do not use reliable/transient-local QoS for live sensor streams unless the user gives a concrete reason.

## Message Rules

- Include only the `sensor_msgs/msg/*.hpp` headers actually used.
- Use message-specific fields instead of packing sensor data into `std_msgs` primitives.
- Fill covariance arrays when known; use documented unknown covariance conventions for messages that define them.
- Keep frame names stable and specific, such as `laser`, `camera_link`, `camera_optical_frame`, `imu_link`, or device-specific names already present in the robot model.
- Preserve device timestamps when they are available and valid; otherwise stamp as close to acquisition as possible.
- Do not rotate, project, filter, or resample sensor data in a driver unless the user requested it or the device API already defines that output.
- Validate units before publishing: ranges in meters, angles in radians, angular velocity in rad/s, linear acceleration in m/s^2, magnetic field in tesla, temperature in Celsius, pressure in pascals.

## Checks

- Sensor data topics use `rclcpp::SensorDataQoS{}` where requested or where the node consumes live sensor data.
- Standard topics and `sensor_msgs` types are used for common sensors.
- Stamped messages set `header.stamp` and `header.frame_id`.
- Sensor frame IDs identify the physical sensor frame, not `base_link`, unless the sensor is physically colocated and documented that way.
- Calibration, covariance, fix/status, and timing fields are not left at misleading defaults when the device provides valid metadata.
- No custom message, topic, parameter, or QoS abstraction is added unless the request requires it.
- Package dependencies include `rclcpp` and `sensor_msgs`; add `image_transport`, `camera_info_manager`, `tf2_ros`, or vendor SDK dependencies only when actually used.
