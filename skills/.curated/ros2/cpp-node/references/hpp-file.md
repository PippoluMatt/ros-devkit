# ROS2 C++ .hpp Node Files

Use a header only when the node class or helper API is reused outside a single executable source file.

## Header Shape

Prefer `#pragma once` and keep includes minimal:

```cpp
#pragma once

#include "rclcpp/rclcpp.hpp"

class ExampleNode : public rclcpp::Node
{
public:
  explicit ExampleNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  void on_timer();

  rclcpp::TimerBase::SharedPtr timer_;
};
```

Define non-trivial behavior in the `.cpp` file.

## Optional NodeInterfaces API

Declare lifecycle-compatible helpers with the interfaces they need:

```cpp
#pragma once

#include "rclcpp/node_interfaces/node_interfaces.hpp"

using NodeInfoInterfaces = rclcpp::node_interfaces::NodeInterfaces<
  rclcpp::node_interfaces::NodeBaseInterface,
  rclcpp::node_interfaces::NodeLoggingInterface>;

void log_node_name(NodeInfoInterfaces interfaces);
```

The `.cpp` file should include logging and implementation headers, then retrieve interfaces with `get_node_*_interface()`.

## Header Rules

- Do not include message headers in the `.hpp` unless the message type appears in a member declaration or public API.
- Prefer forward declarations for project types when possible.
- Keep parameters, topic names, and default values in the `.cpp` unless they are part of a public API.
- Avoid inline ROS graph side effects in headers.
- If the node class is exported from a library, make constructor options explicit and avoid hard-coded process-level behavior.
