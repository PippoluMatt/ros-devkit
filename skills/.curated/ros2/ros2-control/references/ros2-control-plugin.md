# ROS2 Control Generated Plugin Files

Use this reference only while generating plugin files for a new `hardware_interface::SystemInterface` hardware package. Use `ros2-control-pluginize` for existing `_controllers` or `_hardware` packages.

## Source

Use `scripts/add_plugin_export.py`; the script owns the include and macro formatting.

Review that the export is outside the namespace and exports `<namespace>::<class_name>` as `hardware_interface::SystemInterface`.

## Plugin XML

Create a plugin description XML at package root by default with `scripts/create_plugin_xml.py`.

Review that `<library path>` matches the CMake target without the `lib` prefix, `name` is `<package_name>/<class_name>`, `type` is `<namespace>::<class_name>`, and `base_class_type` is `hardware_interface::SystemInterface`.
