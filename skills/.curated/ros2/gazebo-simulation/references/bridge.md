# Bridge Type Reference

Each entry in `gazebo_bridge.yaml` has this shape:

```yaml
- ros_topic_name: "/cmd_vel"
  gz_topic_name: "/model/my_robot/cmd_vel"
  ros_type_name: "geometry_msgs/msg/Twist"
  gz_type_name: "gz.msgs.Twist"
  direction: ROS_TO_GZ
```

The tables below list every ROS 2 type and its valid Gazebo type counterpart(s).
Some ROS types map to more than one Gazebo type — either is a valid pairing.

## Topics

### actuator_msgs

| ROS type | Gazebo type |
| --- | --- |
| actuator_msgs/msg/Actuators | gz.msgs.Actuators |

### builtin_interfaces

| ROS type | Gazebo type |
| --- | --- |
| builtin_interfaces/msg/Time | gz.msgs.Time |

### geometry_msgs

| ROS type | Gazebo type |
| --- | --- |
| geometry_msgs/msg/Point | gz.msgs.Vector3d |
| geometry_msgs/msg/Pose | gz.msgs.Pose |
| geometry_msgs/msg/PoseArray | gz.msgs.Pose_V |
| geometry_msgs/msg/PoseStamped | gz.msgs.Pose |
| geometry_msgs/msg/PoseWithCovariance | gz.msgs.PoseWithCovariance |
| geometry_msgs/msg/PoseWithCovarianceStamped | gz.msgs.PoseWithCovariance |
| geometry_msgs/msg/Quaternion | gz.msgs.Quaternion |
| geometry_msgs/msg/Transform | gz.msgs.Pose |
| geometry_msgs/msg/TransformStamped | gz.msgs.Pose |
| geometry_msgs/msg/Twist | gz.msgs.Twist |
| geometry_msgs/msg/TwistStamped | gz.msgs.Twist |
| geometry_msgs/msg/TwistWithCovariance | gz.msgs.TwistWithCovariance |
| geometry_msgs/msg/TwistWithCovarianceStamped | gz.msgs.TwistWithCovariance |
| geometry_msgs/msg/Vector3 | gz.msgs.Vector3d |
| geometry_msgs/msg/Wrench | gz.msgs.Wrench |
| geometry_msgs/msg/WrenchStamped | gz.msgs.Wrench |

### gps_msgs

| ROS type | Gazebo type |
| --- | --- |
| gps_msgs/msg/GPSFix | gz.msgs.NavSat |

### marine_acoustic_msgs

| ROS type | Gazebo type |
| --- | --- |
| marine_acoustic_msgs/msg/Dvl | gz.msgs.DVLVelocityTracking |

### nav_msgs

| ROS type | Gazebo type |
| --- | --- |
| nav_msgs/msg/Odometry | gz.msgs.Odometry |
| nav_msgs/msg/Odometry | gz.msgs.OdometryWithCovariance |

### rcl_interfaces

| ROS type | Gazebo type |
| --- | --- |
| rcl_interfaces/msg/ParameterValue | gz.msgs.Any |

### ros_gz_interfaces

| ROS type | Gazebo type |
| --- | --- |
| ros_gz_interfaces/msg/Altimeter | gz.msgs.Altimeter |
| ros_gz_interfaces/msg/Contact | gz.msgs.Contact |
| ros_gz_interfaces/msg/Contacts | gz.msgs.Contacts |
| ros_gz_interfaces/msg/Dataframe | gz.msgs.Dataframe |
| ros_gz_interfaces/msg/Entity | gz.msgs.Entity |
| ros_gz_interfaces/msg/EntityWrench | gz.msgs.EntityWrench |
| ros_gz_interfaces/msg/Float32Array | gz.msgs.Float_V |
| ros_gz_interfaces/msg/GuiCamera | gz.msgs.GUICamera |
| ros_gz_interfaces/msg/JointWrench | gz.msgs.JointWrench |
| ros_gz_interfaces/msg/Light | gz.msgs.Light |
| ros_gz_interfaces/msg/LogicalCameraImage | gz.msgs.LogicalCameraImage |
| ros_gz_interfaces/msg/LogPlaybackStatistics | gz.msgs.LogPlaybackStatistics |
| ros_gz_interfaces/msg/ParamVec | gz.msgs.Param |
| ros_gz_interfaces/msg/ParamVec | gz.msgs.Param_V |
| ros_gz_interfaces/msg/SensorNoise | gz.msgs.SensorNoise |
| ros_gz_interfaces/msg/StringVec | gz.msgs.StringMsg_V |
| ros_gz_interfaces/msg/TrackVisual | gz.msgs.TrackVisual |
| ros_gz_interfaces/msg/VideoRecord | gz.msgs.VideoRecord |
| ros_gz_interfaces/msg/WorldStatistics | gz.msgs.WorldStatistics |

### rosgraph_msgs

| ROS type | Gazebo type |
| --- | --- |
| rosgraph_msgs/msg/Clock | gz.msgs.Clock |

### sensor_msgs

| ROS type | Gazebo type |
| --- | --- |
| sensor_msgs/msg/BatteryState | gz.msgs.BatteryState |
| sensor_msgs/msg/CameraInfo | gz.msgs.CameraInfo |
| sensor_msgs/msg/FluidPressure | gz.msgs.FluidPressure |
| sensor_msgs/msg/Image | gz.msgs.Image |
| sensor_msgs/msg/Imu | gz.msgs.IMU |
| sensor_msgs/msg/JointState | gz.msgs.Model |
| sensor_msgs/msg/Joy | gz.msgs.Joy |
| sensor_msgs/msg/LaserScan | gz.msgs.LaserScan |
| sensor_msgs/msg/MagneticField | gz.msgs.Magnetometer |
| sensor_msgs/msg/NavSatFix | gz.msgs.NavSat |
| sensor_msgs/msg/PointCloud2 | gz.msgs.PointCloudPacked |
| sensor_msgs/msg/Range | gz.msgs.LaserScan |

### std_msgs

| ROS type | Gazebo type |
| --- | --- |
| std_msgs/msg/Bool | gz.msgs.Boolean |
| std_msgs/msg/ColorRGBA | gz.msgs.Color |
| std_msgs/msg/Empty | gz.msgs.Empty |
| std_msgs/msg/Float32 | gz.msgs.Float |
| std_msgs/msg/Float64 | gz.msgs.Double |
| std_msgs/msg/Header | gz.msgs.Header |
| std_msgs/msg/Int32 | gz.msgs.Int32 |
| std_msgs/msg/String | gz.msgs.StringMsg |
| std_msgs/msg/UInt32 | gz.msgs.UInt32 |

### tf2_msgs

| ROS type | Gazebo type |
| --- | --- |
| tf2_msgs/msg/TFMessage | gz.msgs.Pose_V |

### trajectory_msgs

| ROS type | Gazebo type |
| --- | --- |
| trajectory_msgs/msg/JointTrajectory | gz.msgs.JointTrajectory |

### vision_msgs

| ROS type | Gazebo type |
| --- | --- |
| vision_msgs/msg/Detection2D | gz.msgs.AnnotatedAxisAligned2DBox |
| vision_msgs/msg/Detection2DArray | gz.msgs.AnnotatedAxisAligned2DBox_V |
| vision_msgs/msg/Detection3D | gz.msgs.AnnotatedOriented3DBox |
| vision_msgs/msg/Detection3DArray | gz.msgs.AnnotatedOriented3DBox_V |

## Services

| ROS type | Gazebo request | Gazebo response |
| --- | --- | --- |
| ros_gz_interfaces/srv/ControlWorld | gz.msgs.WorldControl | gz.msgs.Boolean |