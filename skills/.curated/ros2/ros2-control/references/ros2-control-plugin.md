# ROS2 Control Plugin Export

Use pluginlib for `hardware_interface::SystemInterface` implementations.

## Source Export

Use `scripts/add_plugin_export.py` for idempotent insertion. The script owns the exact include and macro formatting.

Review that the source includes `pluginlib/class_list_macros.hpp` and exports `<namespace>::<class_name>` as `hardware_interface::SystemInterface` outside the namespace.

## Plugin XML

Create a plugin description XML at package root by default with `scripts/create_plugin_xml.py`.

The `<library path>` value must match the CMake library target name without the `lib` prefix.
The class entry must use `<package_name>/<class_name>` for `name`, `<namespace>::<class_name>` for `type`, and `hardware_interface::SystemInterface` for `base_class_type`.
