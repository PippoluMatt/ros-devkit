---
name: ros2-control-pluginize
description: Pluginize existing ROS2 ros2_control controller and hardware interface packages. Use when a package ending `_controllers` or `_hardware` must gain pluginlib XML, PLUGINLIB_EXPORT_CLASS, package.xml dependencies, and CMakeLists.txt wiring for controller_interface or hardware_interface plugins.
---

# ROS2 Control Pluginize

Use this skill to convert an existing ros2_control controller or hardware interface implementation into a loadable pluginlib plugin. Keep the conversion surgical: do not rename the package, move the class, or rewrite build structure unless plugin loading requires it.

## Workflow

1. Classify the package from `package.xml` or the package directory name:
   - `_controllers` means the controller branch.
   - `_hardware` means the hardware branch.
   - Any other suffix is outside this skill; ask before proceeding.

   Complete this step when the branch, package name, C++ namespace, class name, source `.cpp`, library target, and plugin XML path are identified.

2. Add or update the plugin description XML at the package root.

   Complete this step when `<library path="...">` matches the CMake library target exactly and the `<class>` entry uses the same namespace, class, and base type as the source export macro.

3. Add the source export at the end of the implementation `.cpp`.

   Complete this step when `#include "pluginlib/class_list_macros.hpp"` and exactly one `PLUGINLIB_EXPORT_CLASS(...)` for the class exist outside the implementation namespace.

4. Add missing `package.xml` dependencies without duplicating existing tags.

   Complete this step when the branch-specific interface dependency and `pluginlib` are present.

5. Wire `CMakeLists.txt`.

   Complete this step when the interface package and `pluginlib` are found, the plugin library links them, `pluginlib_export_plugin_description_file(...)` points at the XML, the library target is installed, and exported dependencies still match the package dependencies.

6. Validate the conversion.

   Complete this step when XML parses, source/build names agree, `git diff --check` passes, and `colcon build --packages-select <package>` has been run when a ROS2 environment is available.

## Controller Branch

Use this branch only for packages ending `_controllers`.

Plugin XML:

```xml
<library path="<library_target>">
  <class name="<library_target>/<ClassName>"
         type="<namespace>::<ClassName>"
         base_class_type="controller_interface::ChainableControllerInterface">
    <description><ClassName> ros2_control controller.</description>
  </class>
</library>
```

Source export:

```cpp
#include "pluginlib/class_list_macros.hpp"

PLUGINLIB_EXPORT_CLASS(
  <namespace>::<ClassName>,
  controller_interface::ChainableControllerInterface)
```

`package.xml` dependencies:

```xml
<depend>controller_interface</depend>
<depend>pluginlib</depend>
```

If the existing controller inherits `controller_interface::ControllerInterface` instead of `controller_interface::ChainableControllerInterface`, do not silently change the inheritance. Ask whether to export the existing base or convert the controller to chainable.

## Hardware Branch

Use this branch only for packages ending `_hardware`.

Prefer `<name>_hardware_interface` as the library target when no target exists yet, where `<name>` is the package name without the `_hardware` suffix.

Plugin XML:

```xml
<?xml version='1.0' encoding='utf-8'?>
<library path="<name>_hardware_interface">
  <class name="<name>_hardware/<ClassName>"
         type="<name>_hardware::<ClassName>"
         base_class_type="hardware_interface::SystemInterface">
    <description><ClassName> ros2_control hardware interface.</description>
  </class>
</library>
```

Source export:

```cpp
#include "pluginlib/class_list_macros.hpp"

PLUGINLIB_EXPORT_CLASS(
  <name>_hardware::<ClassName>,
  hardware_interface::SystemInterface)
```

`package.xml` dependencies:

```xml
<depend>hardware_interface</depend>
<depend>pluginlib</depend>
```

## CMake Wiring

Preserve the package's existing CMake style. If it uses `THIS_PACKAGE_INCLUDE_DEPENDS`, add the branch-specific dependency and `pluginlib` there so the existing `foreach(Dependency IN ITEMS ...) find_package(...) endforeach()` remains the single dependency source. Otherwise add explicit `find_package(<dependency> REQUIRED)` calls.

For controller plugins, add:

```cmake
pluginlib_export_plugin_description_file(
  controller_interface <plugin_xml>)
```

For hardware plugins, add:

```cmake
pluginlib_export_plugin_description_file(
  hardware_interface <plugin_xml>)
```

Ensure the plugin library target links the matching imported targets:

```cmake
target_link_libraries(<library_target> PUBLIC
  controller_interface::controller_interface
  pluginlib::pluginlib
)
```

or:

```cmake
target_link_libraries(<library_target> PUBLIC
  hardware_interface::hardware_interface
  pluginlib::pluginlib
)
```

If the package already uses `ament_target_dependencies(...)`, add the same dependencies there instead of mixing target-link styles without need.

The plugin library must be installed and exported:

```cmake
install(
  TARGETS <library_target>
  EXPORT export_<library_target>
  RUNTIME DESTINATION bin
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
)

ament_export_targets(export_<library_target> HAS_LIBRARY_TARGET)
ament_export_dependencies(<dependencies>)
```

Use `${THIS_PACKAGE_INCLUDE_DEPENDS}` for `<dependencies>` only when that variable already exists; otherwise list the branch-specific interface package, `pluginlib`, and any other public dependencies explicitly.

If the package has an existing `install(TARGETS ...)` or `ament_export_targets(...)` block, update it in place rather than adding a duplicate.

## Checks

- The package suffix selects exactly one branch.
- Plugin XML `<library path>` equals the CMake library target.
- Plugin XML `type` equals the `PLUGINLIB_EXPORT_CLASS` C++ class.
- Plugin XML `base_class_type` equals the `PLUGINLIB_EXPORT_CLASS` base class.
- `pluginlib_export_plugin_description_file(...)` uses `controller_interface` for controllers and `hardware_interface` for hardware.
- The export macro is outside the namespace block and appears once.
- `package.xml` and `CMakeLists.txt` both include the branch-specific interface dependency and `pluginlib`.
