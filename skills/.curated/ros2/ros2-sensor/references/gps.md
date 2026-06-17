# GPS/GNSS

Use this reference for `sensor_msgs::msg::NavSatFix` drivers, consumers, and reviews.

## Contract

- Publish GNSS fixes as `sensor_msgs::msg::NavSatFix` on `fix` unless the package already establishes a different interface.
- Use WGS84 latitude and longitude in degrees. Do not publish radians.
- Use altitude according to the device/reporting datum and make geoid-versus-ellipsoid assumptions explicit when they matter.
- Fill `status.status` and `status.service` from the receiver state. Do not publish invalid or no-fix data as a valid fix.
- Fill `position_covariance` and `position_covariance_type` when the receiver provides accuracy, DOP-derived covariance, or another defensible estimate.
- Stamp fixes with the valid receiver/acquisition timestamp when available; otherwise stamp as close to message acquisition as possible.
- Use an antenna or GNSS receiver frame such as `gps_link`, not `base_link`, unless the physical frame is intentionally colocated and documented.
- Do not project latitude/longitude into local XY, odometry, or map coordinates inside a basic driver unless the user asks for that derived output.

## Review Checks

- Latitude and longitude are degrees in WGS84, not radians or projected coordinates.
- Altitude reference is understood and not silently mixed between ellipsoid, geoid, or local datum.
- Invalid, no-fix, or stale receiver states are not marked as valid fixes.
- Known accuracy metadata is not discarded while covariance remains all zeros or unknown.
- `position_covariance_type` matches how covariance was produced.
- `frame_id` identifies the GNSS antenna/receiver frame, not the robot base frame by convenience.
