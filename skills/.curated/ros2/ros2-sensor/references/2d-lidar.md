# 2D Lidar

Use this reference for `sensor_msgs::msg::LaserScan` drivers, consumers, and reviews.

## Contract

- Publish 2D planar scans as `LaserScan` on `scan` unless the package already establishes a different interface.
- Use meters for ranges and radians for all angles.
- Set `angle_min`, `angle_max`, and `angle_increment` from the actual scan geometry. Do not change these when filtering individual beams.
- Set `time_increment` to the time between adjacent measurements for rotating or time-skewed scanners. Use `0` only when measurements are truly simultaneous or the device cannot provide a defensible value.
- Set `scan_time` to the time between full scans when known.
- Set `range_min` and `range_max` to the valid measurement interval from the device documentation or active configuration.
- Represent invalid, too-close, too-far, or saturated returns using the `LaserScan` conventions expected by downstream consumers; do not clamp them into plausible obstacle ranges.
- Stamp the scan at acquisition time. If the device reports first-ray, mid-scan, or end-of-scan time, preserve that convention and document any conversion.
- Use a stable physical frame such as `laser` or the URDF frame. The scan plane should match the sensor frame and ROS right-handed coordinate conventions.
- Do not publish a synthesized `PointCloud2` instead of `LaserScan` unless the user asks for that output.

## Review Checks

- Angles are radians, not degrees.
- Range values and limits are meters.
- `angle_increment` is consistent with `angle_min`, `angle_max`, and the number of beams using the device's inclusive or exclusive endpoint convention.
- Rotating scanners do not leave `time_increment = 0` without a reason.
- Filtering invalid beams does not resize `ranges` or silently alter scan geometry.
- `intensities` is either filled with aligned per-beam data or left empty.
- `frame_id` is the lidar frame, not `base_link`, unless explicitly documented.
