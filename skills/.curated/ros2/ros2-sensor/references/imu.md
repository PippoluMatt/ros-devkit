# IMU

Use this reference for `sensor_msgs::msg::Imu` drivers, consumers, and reviews.

## Contract

- Publish IMU data as `sensor_msgs::msg::Imu` on `imu/data` unless the package already establishes a different interface.
- Treat `header.frame_id` as the physical IMU frame. Keep it stable and consistent with URDF/TF.
- Follow right-handed ROS frame semantics. Surface any device NED, NWU, or vendor-specific axis convention before converting it.
- Publish orientation as a normalized quaternion when a fused orientation estimate is available. Use radians per second for angular velocity and meters per second squared for linear acceleration.
- Preserve a valid hardware timestamp when available; otherwise stamp as close to sample acquisition as possible.
- Fill covariance arrays when known. Use message-defined unknown covariance sentinel values where applicable instead of leaving misleading zeros.
- Do not publish fake orientation from gyro-only data. If orientation is unavailable, mark it unknown according to `Imu` message conventions.
- Be explicit about gravity handling. `linear_acceleration` should follow the meaning documented by the device or preprocessing pipeline, and consumers should not have to infer whether gravity was removed.
- Avoid arbitrary frame rotations in the driver unless they are required by the device contract or requested by the user. Document any conversion at the ROS interface boundary.

## Review Checks

- Axes are not swapped or sign-flipped by accident.
- NED/ENU or vendor-frame conversion is explicit and tested.
- Angular velocity is rad/s, not deg/s.
- Linear acceleration is m/s^2, not g.
- Covariance is initialized intentionally; zeros mean known zero variance only when that is true.
- Orientation is not fabricated when the sensor does not provide a fused orientation estimate.
- `frame_id` is consistent across orientation, angular velocity, and linear acceleration samples.
